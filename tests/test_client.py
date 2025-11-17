from typing import List

import httpx
import pytest

from wahoo import ValidationAPIClient, ValidationAPIError
from wahoo import PerformanceMetrics, ValidationRecord


def build_mock_client(responses: List[httpx.Response]) -> ValidationAPIClient:
    """Utility to provide a ValidationAPIClient backed by predictable responses."""
    call_count = {"value": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        idx = call_count["value"]
        call_count["value"] += 1
        try:
            return responses[idx]
        except IndexError:
            raise AssertionError("Mock transport received more requests than expected")

    transport = httpx.MockTransport(handler)
    session = httpx.Client(transport=transport)

    client = ValidationAPIClient(
        base_url="https://api.example.com",
        session=session,
        max_retries=3,
        backoff_seconds=0.01,
    )
    client._test_call_count = call_count
    return client


def sample_payload():
    return {
        "status": "success",
        "data": [
            {
                "hotkey": "5G6HBuhKoYUjGvbcoa6X6Tm3q2jNFek1Ry78S8gKyY5HgiDj",
                "signature": "88ba...",
                "message": "nonce-msg",
                "performance": {
                    "total_volume_usd": "14.15954",
                    "realized_profit_usd": "4.27772",
                    "unrealized_profit_usd": 0,
                    "trade_count": 3,
                    "open_positions_count": 1,
                },
            },
            {"hotkey": "fakeadresstotest"},
        ],
    }


def test_fetch_validation_data_success():
    payload = sample_payload()
    responses = [httpx.Response(200, json=payload)]
    client = build_mock_client(responses)

    records = client.fetch_validation_data(
        hotkeys=["5G6HBuhKoYUjGvbcoa6X6Tm3q2jNFek1Ry78S8gKyY5HgiDj", "fakeadresstotest"]
    )

    assert len(records) == 2
    first = records[0]
    assert isinstance(first, ValidationRecord)
    assert first.hotkey == "5G6HBuhKoYUjGvbcoa6X6Tm3q2jNFek1Ry78S8gKyY5HgiDj"
    assert isinstance(first.performance, PerformanceMetrics)
    assert first.performance.total_volume_usd == pytest.approx(14.15954)
    assert first.performance.realized_profit_usd == pytest.approx(4.27772)
    assert first.performance.unrealized_profit_usd == 0.0
    assert first.performance.trade_count == 3
    assert first.performance.open_positions_count == 1


def test_fetch_validation_data_retries_on_server_error():
    payload = sample_payload()
    responses = [
        httpx.Response(500, json={"error": "temporary"}),
        httpx.Response(200, json=payload),
    ]
    client = build_mock_client(responses)

    records = client.fetch_validation_data(
        hotkeys=["5G6HBuhKoYUjGvbcoa6X6Tm3q2jNFek1Ry78S8gKyY5HgiDj"]
    )

    assert len(records) == 2
    assert client._test_call_count["value"] == 2


def test_fetch_validation_data_validates_start_end_order():
    client = build_mock_client([httpx.Response(200, json=sample_payload())])

    with pytest.raises(ValueError):
        client.fetch_validation_data(
            hotkeys=["hk1"],
            start_date="2025-12-01T00:00:00Z",
            end_date="2025-11-01T00:00:00Z",
        )


def test_fetch_validation_data_surfaces_client_error():
    responses = [
        httpx.Response(403, json={"status": "error", "message": "forbidden"}),
    ]
    client = build_mock_client(responses)

    with pytest.raises(ValidationAPIError):
        client.fetch_validation_data(hotkeys=["hk1"])


def test_fetch_validation_data_invalid_payload_raises():
    responses = [
        httpx.Response(200, json={"status": "success", "data": [{"hotkey": ""}]}),
    ]
    client = build_mock_client(responses)

    with pytest.raises(ValidationAPIError):
        client.fetch_validation_data(hotkeys=["hk1"])
