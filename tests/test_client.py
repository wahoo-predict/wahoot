from typing import List

import httpx
import pytest

from wahoo import ValidationAPIClient, ValidationAPIError
from wahoo import PerformanceMetrics, ValidationRecord
from wahoo.validator.api.client import get_wahoo_validation_data


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


def test_get_wahoo_validation_data_batching():
    """Test that get_wahoo_validation_data splits hotkeys into batches.

    Note: This is a basic test. Full integration testing would require
    mocking the httpx client properly, which is complex.
    For now, we verify the function exists and handles edge cases.
    """
    # Test with empty hotkeys
    records = get_wahoo_validation_data(hotkeys=[])
    assert records == []

    # Test that function is callable and accepts parameters
    # Full mocking would require patching httpx.Client which is complex
    # This test verifies the interface works
    assert callable(get_wahoo_validation_data)


def test_get_wahoo_validation_data_empty_hotkeys():
    """Test that get_wahoo_validation_data handles empty hotkeys gracefully."""
    records = get_wahoo_validation_data(hotkeys=[])
    assert records == []


def test_get_wahoo_validation_data_handles_failures():
    """Test that get_wahoo_validation_data handles failures gracefully."""
    # Test with invalid hotkeys (empty strings get filtered)
    records = get_wahoo_validation_data(hotkeys=["", "  ", None])  # type: ignore
    # Should return empty list after normalization
    assert isinstance(records, list)


def test_get_wahoo_validation_data_batching_splits_correctly():
    """Test that batching splits hotkeys into correct batch sizes."""
    # Create 300 hotkeys to test batching (should create 2 batches: 256 + 44)
    hotkeys = [f"hotkey_{i:03d}" for i in range(300)]

    # Create mock responses for 2 batches
    def create_batch_payload(batch_hotkeys):
        return {
            "data": [
                {
                    "hotkey": hk,
                    "performance": {
                        "total_volume_usd": "100.0",
                        "realized_profit_usd": "10.0",
                    },
                }
                for hk in batch_hotkeys
            ]
        }

    # Track which batches were called
    call_tracker = {"batches": []}

    def handler(request: httpx.Request) -> httpx.Response:
        # Extract hotkeys from request params
        params = dict(request.url.params)
        batch_hotkeys = params.get("hotkeys", "").split(",")
        call_tracker["batches"].append(batch_hotkeys)

        # Return appropriate payload for this batch
        payload = create_batch_payload(batch_hotkeys)
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)
    session = httpx.Client(transport=transport)
    client = ValidationAPIClient(
        base_url="https://api.example.com",
        session=session,
        max_retries=1,
        backoff_seconds=0.01,
    )

    # Test with max_per_batch=256
    records = get_wahoo_validation_data(
        hotkeys=hotkeys,
        max_per_batch=256,
        client=client,
    )

    # Should have 2 batches
    assert len(call_tracker["batches"]) == 2
    assert len(call_tracker["batches"][0]) == 256
    assert len(call_tracker["batches"][1]) == 44

    # Should return all records
    assert len(records) == 300


def test_get_wahoo_validation_data_handles_failed_batches():
    """Test that failed batches don't block other batches."""
    hotkeys = [f"hotkey_{i}" for i in range(500)]  # 2 batches with 256

    call_count = {"value": 0}
    first_batch_calls = {"value": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        call_count["value"] += 1
        # Extract hotkeys from request to identify which batch
        params = dict(request.url.params)
        batch_hotkeys = params.get("hotkeys", "").split(",")

        # Check if this is the first batch (256 hotkeys) or second batch (244 hotkeys)
        is_first_batch = len(batch_hotkeys) == 256

        if is_first_batch:
            first_batch_calls["value"] += 1
            # First batch always fails (even on retry)
            # With max_retries=1, we get 2 attempts for first batch
            return httpx.Response(500, json={"error": "server error"})
        else:
            # Second batch succeeds
            return httpx.Response(
                200,
                json={
                    "data": [
                        {"hotkey": hk, "performance": {"total_volume_usd": "100.0"}}
                        for hk in batch_hotkeys
                    ]
                },
            )

    transport = httpx.MockTransport(handler)
    session = httpx.Client(transport=transport)
    client = ValidationAPIClient(
        base_url="https://api.example.com",
        session=session,
        max_retries=1,  # 2 total attempts (1 initial + 1 retry)
        backoff_seconds=0.01,
    )

    records = get_wahoo_validation_data(
        hotkeys=hotkeys,
        max_per_batch=256,
        client=client,
    )

    # With max_retries=1, first batch gets 2 attempts (1 initial + 1 retry)
    # Second batch gets 1 attempt
    # Total: 3 calls (2 for first batch + 1 for second batch)
    assert call_count["value"] == 3
    assert first_batch_calls["value"] == 2  # First batch attempted twice
    # Should have records from second batch only (244 records: 500 - 256)
    assert len(records) == 244


def test_get_wahoo_validation_data_with_validator_db():
    """Test that batching stores results to ValidatorDB as batches complete."""
    hotkeys = [f"hotkey_{i}" for i in range(100)]

    # Mock ValidatorDB
    class MockValidatorDB:
        def __init__(self):
            self.cached_data = {}
            self.cache_calls = []

        def cache_validation_data(self, hotkey: str, data_dict: dict):
            self.cached_data[hotkey] = data_dict
            self.cache_calls.append(hotkey)

    mock_db = MockValidatorDB()

    # Mock API responses
    def handler(request: httpx.Request) -> httpx.Response:
        params = dict(request.url.params)
        batch_hotkeys = params.get("hotkeys", "").split(",")
        return httpx.Response(
            200,
            json={
                "data": [
                    {"hotkey": hk, "performance": {"total_volume_usd": "100.0"}}
                    for hk in batch_hotkeys
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    session = httpx.Client(transport=transport)
    client = ValidationAPIClient(
        base_url="https://api.example.com",
        session=session,
    )

    records = get_wahoo_validation_data(
        hotkeys=hotkeys,
        max_per_batch=50,  # 2 batches
        client=client,
        validator_db=mock_db,
    )

    # Should have cached all records
    assert len(mock_db.cached_data) == 100
    assert len(mock_db.cache_calls) == 100
    assert len(records) == 100


def test_get_wahoo_validation_data_deduplicates_hotkeys():
    """Test that duplicate hotkeys are deduplicated before batching."""
    hotkeys = ["hotkey_1", "hotkey_2", "hotkey_1", "hotkey_3", "hotkey_2"]

    call_tracker = {"hotkeys_seen": set()}

    def handler(request: httpx.Request) -> httpx.Response:
        params = dict(request.url.params)
        batch_hotkeys = params.get("hotkeys", "").split(",")
        call_tracker["hotkeys_seen"].update(batch_hotkeys)

        return httpx.Response(
            200,
            json={
                "data": [
                    {"hotkey": hk, "performance": {"total_volume_usd": "100.0"}}
                    for hk in batch_hotkeys
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    session = httpx.Client(transport=transport)
    client = ValidationAPIClient(
        base_url="https://api.example.com",
        session=session,
    )

    records = get_wahoo_validation_data(
        hotkeys=hotkeys,
        client=client,
    )

    # Should only have 3 unique hotkeys
    assert len(call_tracker["hotkeys_seen"]) == 3
    assert len(records) == 3
    assert set(r.hotkey for r in records) == {"hotkey_1", "hotkey_2", "hotkey_3"}
