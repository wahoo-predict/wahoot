import pandas as pd
import pytest

from wahoo.models import PerformanceMetrics, ValidationRecord
from wahoo.dataframe import records_to_dataframe, ensure_required_columns


def test_records_to_dataframe_basic():
    records = [
        ValidationRecord(
            hotkey="hk1",
            signature="sig",
            message="msg",
            performance=PerformanceMetrics(
                total_volume_usd=10,
                realized_profit_usd=5,
                unrealized_profit_usd=1,
                trade_count=2,
            ),
        ),
        ValidationRecord(
            hotkey="hk2",
            performance=PerformanceMetrics(
                total_volume_usd="14.15954",
                realized_profit_usd="4.27772",
                unrealized_profit_usd=0,
                trade_count=3,
            ),
        ),
    ]

    df = records_to_dataframe(records)

    assert list(df["hotkey"]) == ["hk1", "hk2"]
    assert df.loc[df["hotkey"] == "hk1", "total_volume_usd"].iloc[0] == 10.0
    assert df.loc[df["hotkey"] == "hk2", "total_volume_usd"].iloc[0] == pytest.approx(
        14.15954
    )
    assert df.loc[df["hotkey"] == "hk2", "trade_count"].iloc[0] == 3


def test_records_to_dataframe_fill_missing():
    records = [
        ValidationRecord(
            hotkey="hk3",
            performance=PerformanceMetrics(),
        )
    ]
    df = records_to_dataframe(records)
    assert df.loc[0, "total_volume_usd"] == 0.0
    assert df.loc[0, "trade_count"] == 0
    assert df.loc[0, "signature"] == ""


def test_records_to_dataframe_drop_duplicates():
    records = [
        ValidationRecord(
            hotkey="hk1", performance=PerformanceMetrics(total_volume_usd=1)
        ),
        ValidationRecord(
            hotkey="hk1", performance=PerformanceMetrics(total_volume_usd=5)
        ),
    ]
    df = records_to_dataframe(records)
    assert len(df) == 1
    assert df.loc[0, "total_volume_usd"] == 5.0


def test_ensure_required_columns_raises():
    df = pd.DataFrame({"hotkey": ["hk1"]})
    with pytest.raises(ValueError):
        ensure_required_columns(df)
