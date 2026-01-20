from __future__ import annotations
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional, Sequence

import numpy as np
import pandas as pd

from .dataframe import ensure_required_columns

logger = logging.getLogger(__name__)

HALF_LIFE_SECONDS = 12 * 3600
EPOCH_INTERVAL_SECONDS = 360 * 12
HALF_LIFE_EPOCHS = int(HALF_LIFE_SECONDS / EPOCH_INTERVAL_SECONDS)
EMA_ALPHA = 1 - (0.5 ** (1 / HALF_LIFE_EPOCHS))
VOLUME_EXPONENT = 0.7
MIN_VOLUME_THRESHOLD = 1.0

# Cliff detection: if raw score drops below this fraction of stored EMA, reset
# This prevents miners from account swapping and abusing ema score i
CLIFF_RESET_THRESHOLD = 0.5  # raw score must be at least 50% of previous EMA

# Anomaly detection: flag new miners with suspiciously high raw scores
# This helps detect potential data manipulation or API issues
NEW_MINER_HIGH_SCORE_THRESHOLD = 10000  # Raw score above this for new miners is suspicious
HIGH_VOLUME_THRESHOLD = 100000  # $100K volume threshold for logging context


@dataclass(frozen=True)
class OperatorResult:
    weights: np.ndarray
    meta: Dict[str, Any]


class Operator(ABC):
    name: str = "base"
    required_columns: Sequence[str] = (
        "hotkey",
        "total_volume_usd",
        "realized_profit_usd",
        "unrealized_profit_usd",
    )

    def preprocess(self, df: pd.DataFrame) -> pd.DataFrame:
        ensure_required_columns(df, self.required_columns)
        return df

    @abstractmethod
    def run(self, df: pd.DataFrame) -> OperatorResult:
        raise NotImplementedError


class EMAVolumeScorer(Operator):
    name = "ema_volume"
    required_columns = (
        "hotkey",
        "total_volume_usd",
        "realized_profit_usd",
        "unrealized_profit_usd",
    )

    def __init__(self, alpha: float = EMA_ALPHA, volume_exp: float = VOLUME_EXPONENT):
        self.alpha = alpha
        self.volume_exp = volume_exp

    def run(
        self,
        df: pd.DataFrame,
        previous_scores: Optional[Dict[str, float]] = None,
    ) -> OperatorResult:
        df = self.preprocess(df)

        if previous_scores is None:
            previous_scores = {}

        hotkeys = df["hotkey"].to_numpy()
        volume = np.maximum(df["total_volume_usd"].fillna(0).to_numpy(dtype=float), 0.0)
        realized_pnl = df["realized_profit_usd"].fillna(0).to_numpy(dtype=float)
        unrealized_pnl = df["unrealized_profit_usd"].fillna(0).to_numpy(dtype=float)

        total_pnl = realized_pnl + unrealized_pnl

        volume_component = np.power(volume, self.volume_exp)
        safe_volume = np.maximum(volume, MIN_VOLUME_THRESHOLD)
        pnl_ratio = total_pnl / safe_volume
        pnl_multiplier = np.maximum(0.0, 1.0 + pnl_ratio)

        raw_scores = volume_component * pnl_multiplier
        smoothed_scores = np.zeros_like(raw_scores)
        new_miner_count = 0
        cliff_reset_count = 0

        for i, hotkey in enumerate(hotkeys):
            prev_score = previous_scores.get(hotkey, 0.0)
            raw = raw_scores[i]
            vol = volume[i]
            
            if prev_score == 0.0:
                # New miner detected
                smoothed_scores[i] = raw
                new_miner_count += 1
                
                # Flag new miners with suspiciously high raw scores
                if raw > NEW_MINER_HIGH_SCORE_THRESHOLD:
                    logger.warning(
                        f"ANOMALY: New miner {hotkey[:16]}... has unusually high raw score: "
                        f"raw_score={raw:.2f}, volume=${vol:.2f}, "
                        f"realized_pnl=${realized_pnl[i]:.2f}, unrealized_pnl=${unrealized_pnl[i]:.2f}"
                    )
                elif vol > HIGH_VOLUME_THRESHOLD:
                    # Log high volume new miners for tracking (info level)
                    logger.info(
                        f"New high-volume miner {hotkey[:16]}...: "
                        f"raw_score={raw:.2f}, volume=${vol:.2f}"
                    )
            elif prev_score > 0 and raw < CLIFF_RESET_THRESHOLD * prev_score:
                # CLIFF DETECTION: Raw score dropped below threshold of previous EMA
                # This indicates the miner stopped trading or had a massive activity drop
                # Or switched their hotkeys to a different account
                # Reset to raw score to prevent coasting on historical scores
                smoothed_scores[i] = raw
                cliff_reset_count += 1
                logger.warning(
                    f"EMA cliff reset for {hotkey[:16]}...: "
                    f"prev_ema={prev_score:.2f}, raw={raw:.4f}, "
                    f"ratio={raw/prev_score:.6f} < {CLIFF_RESET_THRESHOLD}, "
                    f"volume=${vol:.2f}, realized_pnl=${realized_pnl[i]:.2f}"
                )
            else:
                # Normal EMA update
                smoothed_scores[i] = (
                    1 - self.alpha
                ) * prev_score + self.alpha * raw
                
                # ANOMALY DETECTION: Log significant score drops that don't trigger cliff reset
                # This helps track API data changes for investigation
                if prev_score > 0 and raw < 0.1 * prev_score:
                    logger.info(
                        f"Significant score drop for {hotkey[:16]}...: "
                        f"prev_ema={prev_score:.2f}, raw={raw:.2f}, "
                        f"ratio={raw/prev_score:.4f}, volume=${vol:.2f}"
                    )

        if cliff_reset_count > 0:
            logger.info(
                f"EMA cliff detection: Reset {cliff_reset_count} miners with "
                f"raw_score < {CLIFF_RESET_THRESHOLD*100:.1f}% of stored EMA"
            )

        total = smoothed_scores.sum()
        if total > 0:
            weights = smoothed_scores / total
        else:
            weights = np.zeros_like(smoothed_scores)

        meta = {
            "total_miners": len(hotkeys),
            "new_miners": new_miner_count,
            "cliff_resets": cliff_reset_count,
            "active_miners": int(np.sum(weights > 0)),
            "total_raw_score": float(raw_scores.sum()),
            "total_smoothed_score": float(total),
            "alpha": self.alpha,
            "volume_exponent": self.volume_exp,
            "cliff_threshold": CLIFF_RESET_THRESHOLD,
            "max_weight": float(weights.max()) if len(weights) > 0 else 0.0,
            "mean_weight": float(weights.mean()) if len(weights) > 0 else 0.0,
            "smoothed_scores": {
                str(hotkey): float(smoothed_scores[i])
                for i, hotkey in enumerate(hotkeys)
            },
        }

        return OperatorResult(weights=weights, meta=meta)


__all__ = [
    "Operator",
    "OperatorResult",
    "EMAVolumeScorer",
    "EMA_ALPHA",
    "HALF_LIFE_EPOCHS",
    "VOLUME_EXPONENT",
    "CLIFF_RESET_THRESHOLD",
]
