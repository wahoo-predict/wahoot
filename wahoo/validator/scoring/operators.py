from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Sequence

import numpy as np
import pandas as pd

from ..dataframe import ensure_required_columns


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


class VolumeProfitOperator(Operator):
    name = "volume_profit"
    required_columns = ("hotkey", "total_volume_usd", "realized_profit_usd")

    def run(self, df: pd.DataFrame) -> OperatorResult:
        df = self.preprocess(df)
        eligible = df["realized_profit_usd"] > 0
        signals = np.where(
            eligible,
            df["realized_profit_usd"].to_numpy(dtype=float)
            * np.maximum(df["total_volume_usd"].to_numpy(dtype=float), 0.0),
            0.0,
        )
        total = float(signals.sum())
        if total <= 0:
            weights = np.zeros(df.shape[0], dtype=float)
            meta = {"reason": "no_positive_profit", "eligible": int(eligible.sum())}
            return OperatorResult(weights=weights, meta=meta)
        weights = signals / total
        meta = {"eligible": int(eligible.sum())}
        return OperatorResult(weights=weights, meta=meta)


__all__ = [
    "Operator",
    "OperatorResult",
    "VolumeProfitOperator",
]
