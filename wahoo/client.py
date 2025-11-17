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

from .models import ValidationRecord

load_dotenv()

DEFAULT_VALIDATION_ENDPOINT = (
    "https://api.wahoopredict.com/api/v2/event/bittensor/statistics"
)

RETRY_STATUS_CODES = {429}
RETRY_STATUS_CODES.update(range(500, 600))


class ValidationAPIError(RuntimeError):
    """Raised when the validation endpoint cannot be queried successfully."""


def _parse_iso8601(value: str) -> datetime:
    """Parse ISO-8601 strings"""
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
        max_retries: int = 3,
        backoff_seconds: float = 1.0,
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
        url = f"{self.base_url}/api/v2/users/validation"
        attempt = 0
        while attempt < self.max_retries:
            attempt += 1
            try:
                response = self._session.get(url, params=params)
            except httpx.HTTPError as exc:
                bt.logging.warning(f"ValidationAPI request failed: {exc}")
                if attempt >= self.max_retries:
                    raise ValidationAPIError(
                        "Failed to reach validation endpoint"
                    ) from exc
                self._sleep_backoff(attempt)
                continue

            if response.status_code == 200:
                return response

            if (
                response.status_code in RETRY_STATUS_CODES
                and attempt < self.max_retries
            ):
                bt.logging.warning(
                    f"ValidationAPI transient error (status={response.status_code}), retrying..."
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
