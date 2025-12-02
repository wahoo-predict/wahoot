import numpy as np

from wahoo import ValidationRecord, PerformanceMetrics
from wahoo import EMAVolumeScorer
from wahoo import OperatorPipeline


def make_records():
    return [
        ValidationRecord(
            hotkey="hk1",
            performance=PerformanceMetrics(
                total_volume_usd=100,
                realized_profit_usd=10,
                unrealized_profit_usd=0,
            ),
        ),
        ValidationRecord(
            hotkey="hk2",
            performance=PerformanceMetrics(
                total_volume_usd=50, realized_profit_usd=5, unrealized_profit_usd=0
            ),
        ),
        ValidationRecord(
            hotkey="hk3",
            performance=PerformanceMetrics(
                total_volume_usd=30, realized_profit_usd=-1, unrealized_profit_usd=0
            ),
        ),
    ]


def test_ema_volume_scorer_basic():
    operator = EMAVolumeScorer()
    pipeline = OperatorPipeline([operator], target_length=3)
    records = make_records()
    result = pipeline.run("ema_volume", records)

    assert np.isclose(result.weights.sum(), 1.0)
    assert result.meta["total_miners"] == 3
    assert result.meta["active_miners"] >= 0
    assert "smoothed_scores" in result.meta


def test_pipeline_pads_weights():
    operator = EMAVolumeScorer()
    pipeline = OperatorPipeline([operator], target_length=5)
    result = pipeline.run("ema_volume", make_records())
    assert result.weights.shape[0] == 5
    assert np.isclose(result.weights[:3].sum(), 1.0)
    assert np.all(result.weights[3:] == 0.0)
