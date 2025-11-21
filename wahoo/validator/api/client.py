from __future__ import annotations

import os
import time
from datetime import datetime
from types import TracebackType
from typing import Any, Dict, List, NoReturn, Optional, Sequence, Set, Type

import bittensor as bt
import httpx
from dotenv import load_dotenv
from pydantic import ValidationError

from ..models import ValidationRecord
from .fallback import filter_usable_records

load_dotenv()

DEFAULT_VALIDATION_ENDPOINT = (
    "https://api.wahoopredict.com/api/v2/event/bittensor/statistics"
)

RETRY_STATUS_CODES = {429}
RETRY_STATUS_CODES.update(range(500, 600))

WAHOO_API_MAX_RETRIES = 2
WAHOO_API_BACKOFF_SECONDS = 1.0

EVENT_ID_MAX_RETRIES = 0

SET_WEIGHTS_MAX_RETRIES = 1


class ValidationAPIError(RuntimeError):
    pass


def _parse_iso8601(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"Invalid ISO 8601 datetime: {value}") from exc


class ValidationAPIClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        *,
        timeout: float = 30.0,
        max_retries: int = WAHOO_API_MAX_RETRIES,
        backoff_seconds: float = WAHOO_API_BACKOFF_SECONDS,
        session: Optional[httpx.Client] = None,
    ):
        resolved_url = base_url or os.getenv(
            "WAHOO_VALIDATION_ENDPOINT", DEFAULT_VALIDATION_ENDPOINT
        )
        self.base_url = resolved_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self._session = session or httpx.Client(timeout=self.timeout)
        self._owns_session = session is None

    def __enter__(self) -> "ValidationAPIClient":
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_session:
            self._session.close()

    def fetch_validation_data(
        self,
        *,
        hotkeys: Sequence[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[ValidationRecord]:
        valid_hotkeys = self._normalize_hotkeys(hotkeys)
        params: Dict[str, str] = {"hotkeys": ",".join(valid_hotkeys)}

        start_dt: Optional[datetime] = None
        end_dt: Optional[datetime] = None
        if start_date:
            start_dt = _parse_iso8601(start_date)
            params["start_date"] = start_date
        if end_date:
            end_dt = _parse_iso8601(end_date)
            params["end_date"] = end_date
        if start_dt and end_dt and start_dt >= end_dt:
            raise ValueError("start_date must be earlier than end_date")

        response = self._request_with_retries(params)
        payload = self._extract_payload(response)
        records: List[ValidationRecord] = []
        for item in payload:
            try:
                record = ValidationRecord.model_validate(item)
            except ValidationError as exc:
                raise ValidationAPIError(f"Invalid validation record: {exc}") from exc
            records.append(record)
        return records

    def _normalize_hotkeys(self, hotkeys: Sequence[str]) -> List[str]:
        if not hotkeys:
            raise ValueError("hotkeys list cannot be empty")
        deduped: List[str] = []
        seen: Set[str] = set()
        for hotkey in hotkeys:
            hk = (hotkey or "").strip()
            if not hk:
                continue
            if hk not in seen:
                seen.add(hk)
                deduped.append(hk)
        if not deduped:
            raise ValueError("hotkeys list cannot be empty")
        return deduped

    def _request_with_retries(self, params: Dict[str, str]) -> httpx.Response:
        url = self.base_url
        attempt = 0
        max_attempts = self.max_retries + 1

        while attempt < max_attempts:
            attempt += 1

            if attempt > 1:
                bt.logging.info(
                    f"ValidationAPI retry attempt {attempt}/{max_attempts} "
                    f"(max_retries={self.max_retries})"
                )

            try:
                response = self._session.get(url, params=params)
            except httpx.TimeoutException as exc:
                bt.logging.error(
                    f"ValidationAPI request timed out after {self.timeout}s "
                    f"(attempt {attempt}/{max_attempts}): {exc}"
                )
                raise ValidationAPIError(
                    f"Validation API request timed out after {self.timeout}s"
                ) from exc
            except httpx.HTTPError as exc:
                bt.logging.warning(
                    f"ValidationAPI request failed (attempt {attempt}/{max_attempts}): {exc}"
                )
                if attempt >= max_attempts:
                    bt.logging.error(
                        f"ValidationAPI exhausted all {max_attempts} attempts"
                    )
                    raise ValidationAPIError(
                        "Failed to reach validation endpoint after all retries"
                    ) from exc
                self._sleep_backoff(attempt)
                continue

            if response.status_code == 200:
                if attempt > 1:
                    bt.logging.info(
                        f"ValidationAPI request succeeded on attempt {attempt}/{max_attempts}"
                    )
                return response

            if response.status_code in RETRY_STATUS_CODES and attempt < max_attempts:
                bt.logging.warning(
                    f"ValidationAPI transient error (status={response.status_code}, "
                    f"attempt {attempt}/{max_attempts}), retrying..."
                )
                self._sleep_backoff(attempt)
                continue

            self._log_and_raise(response)
        raise ValidationAPIError("Exhausted retries for validation endpoint")

    def _sleep_backoff(self, attempt: int) -> None:
        delay = min(30.0, self.backoff_seconds * (2 ** (attempt - 1)))
        time.sleep(delay)

    @staticmethod
    def _extract_payload(response: httpx.Response) -> List[Dict[str, Any]]:
        try:
            data = response.json()
        except ValueError as exc:
            raise ValidationAPIError(
                "Validation endpoint returned invalid JSON"
            ) from exc

        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            if "data" in data and isinstance(data["data"], list):
                return list(data["data"])
            return []
        raise ValidationAPIError("Unexpected response format from validation endpoint")

    def _log_and_raise(self, response: httpx.Response) -> NoReturn:
        try:
            payload = response.json()
        except ValueError:
            payload = response.text
        bt.logging.error(
            f"ValidationAPI request failed with status {response.status_code}: {payload}"
        )
        raise ValidationAPIError(
            f"Validation API request failed with status {response.status_code}"
        )


def get_active_event_id(
    api_base_url: Optional[str] = None,
    *,
    timeout: float = 10.0,
    default_event_id: str = "wahoo_test_event",
) -> str:
    if api_base_url:
        base_url = api_base_url.rstrip("/")
    else:
        base_url = os.getenv("WAHOO_API_URL", "https://api.wahoopredict.com").rstrip(
            "/"
        )

    events_url = f"{base_url}/events"

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(events_url)
            response.raise_for_status()

            data = response.json()
            if isinstance(data, dict):
                event_id = (
                    data.get("active_event_id")
                    or data.get("event_id")
                    or data.get("id")
                    or data.get("event")
                )
                if event_id:
                    bt.logging.info(f"Retrieved active event_id: {event_id}")
                    return str(event_id)

            bt.logging.warning(
                f"Could not extract event_id from response: {data}. "
                f"Using default: {default_event_id}"
            )
            return default_event_id

    except httpx.TimeoutException as exc:
        bt.logging.warning(
            f"Events API request timed out after {timeout}s: {exc}. "
            f"Falling back to default event_id: {default_event_id}"
        )
        return default_event_id
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        bt.logging.warning(
            f"Failed to get active event_id from API: {exc}. "
            f"Falling back to default event_id: {default_event_id}"
        )
        return default_event_id


class ValidatorDBInterface:
    def cache_validation_data(self, hotkey: str, data_dict: Dict[str, Any]) -> None:
        raise NotImplementedError

    def get_cached_validation_data(
        self, hotkeys: Sequence[str], max_age_days: int = 7
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError


def get_wahoo_validation_data(
    hotkeys: Sequence[str],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    *,
    max_per_batch: int = 256,
    batch_timeout: float = 30.0,
    api_base_url: Optional[str] = None,
    validator_db: Optional[ValidatorDBInterface] = None,
    client: Optional[ValidationAPIClient] = None,
) -> List[ValidationRecord]:
    if not hotkeys:
        return []

    valid_hotkeys = list(dict.fromkeys(str(hk).strip() for hk in hotkeys if hk))
    if not valid_hotkeys:
        return []

    endpoint = (
        api_base_url.rstrip("/")
        if api_base_url
        else os.getenv("WAHOO_VALIDATION_ENDPOINT", DEFAULT_VALIDATION_ENDPOINT)
    )

    if client is None:
        client = ValidationAPIClient(base_url=endpoint, timeout=batch_timeout)
    else:
        client.base_url = endpoint
        client.timeout = batch_timeout

    batches = [
        valid_hotkeys[i : i + max_per_batch]
        for i in range(0, len(valid_hotkeys), max_per_batch)
    ]

    bt.logging.info(
        f"Processing {len(valid_hotkeys)} hotkeys in {len(batches)} batches "
        f"(max {max_per_batch} per batch, {batch_timeout}s timeout)"
    )

    all_records: List[ValidationRecord] = []
    successful_batches = 0
    failed_batches = 0

    for batch_num, batch in enumerate(batches, 1):
        try:
            records = client.fetch_validation_data(
                hotkeys=batch,
                start_date=start_date,
                end_date=end_date,
            )

            if validator_db is not None:
                try:
                    for record in records:
                        validator_db.cache_validation_data(
                            hotkey=record.hotkey, data_dict=record.model_dump()
                        )
                except Exception as e:
                    bt.logging.warning(f"Failed to cache batch {batch_num}: {e}")

            all_records.extend(records)
            successful_batches += 1
            bt.logging.debug(
                f"Batch {batch_num}/{len(batches)}: {len(records)} records"
            )

        except ValidationAPIError as e:
            bt.logging.warning(
                f"Batch {batch_num}/{len(batches)} failed: {e}. "
                "Attempting cache fallback..."
            )

            if validator_db is not None:
                try:
                    cached_data = validator_db.get_cached_validation_data(
                        hotkeys=batch, max_age_days=7
                    )
                    if cached_data:
                        cached_records = []
                        for data_dict in cached_data:
                            try:
                                record = ValidationRecord.model_validate(data_dict)
                                cached_records.append(record)
                            except Exception:
                                continue

                        if cached_records:
                            bt.logging.info(
                                f"Cache fallback successful for batch {batch_num}: "
                                f"{len(cached_records)} records"
                            )
                            all_records.extend(cached_records)
                            successful_batches += 1
                            continue
                except Exception as cache_error:
                    bt.logging.warning(
                        f"Cache fallback failed for batch {batch_num}: {cache_error}"
                    )

            bt.logging.warning(
                f"Batch {batch_num}/{len(batches)} skipped (no cache available)"
            )
            failed_batches += 1

        except Exception as e:
            bt.logging.error(f"Batch {batch_num}/{len(batches)} error: {e}")
            failed_batches += 1

    bt.logging.info(
        f"Batching complete: {successful_batches} successful, "
        f"{failed_batches} failed, {len(all_records)} total records"
    )

    usable_records = filter_usable_records(all_records)
    if len(usable_records) < len(all_records):
        excluded = len(all_records) - len(usable_records)
        bt.logging.info(
            f"Filtered {excluded} record(s) with empty metrics. "
            f"Returning {len(usable_records)} usable records."
        )

    return usable_records
