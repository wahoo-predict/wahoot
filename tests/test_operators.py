import numpy as np

from wahoo.models import ValidationRecord, PerformanceMetrics
from wahoo.operators import VolumeProfitOperator
from wahoo.pipeline import OperatorPipeline


def make_records():
    return [
        ValidationRecord(
            hotkey="hk1",
            performance=PerformanceMetrics(
                total_volume_usd=100, realized_profit_usd=10
            ),
        ),
        ValidationRecord(
            hotkey="hk2",
            performance=PerformanceMetrics(total_volume_usd=50, realized_profit_usd=5),
        ),
        ValidationRecord(
            hotkey="hk3",
            performance=PerformanceMetrics(total_volume_usd=30, realized_profit_usd=-1),
        ),
    ]


def test_volume_profit_ansatz_basic():
    operator = VolumeProfitOperator()
    pipeline = OperatorPipeline([operator], target_length=3)
    records = make_records()
    result = pipeline.run("volume_profit", records)

    assert np.isclose(result.weights.sum(), 1.0)
    assert result.weights[2] == 0.0
    assert result.meta["eligible"] == 2


def test_pipeline_pads_weights():
    operator = VolumeProfitOperator()
    pipeline = OperatorPipeline([operator], target_length=5)
    result = pipeline.run("volume_profit", make_records())
    assert result.weights.shape[0] == 5
    assert np.isclose(result.weights[:3].sum(), 1.0)
    assert np.all(result.weights[3:] == 0.0)
