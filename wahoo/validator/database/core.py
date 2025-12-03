import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from ..api.client import ValidatorDBInterface
from .validator_db import get_or_create_database

logger = logging.getLogger(__name__)


class ValidatorDB(ValidatorDBInterface):
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path
        get_or_create_database(self.db_path)

    def _get_conn(self) -> sqlite3.Connection:
        return get_or_create_database(self.db_path)

    def cache_validation_data(self, hotkey: str, data_dict: Dict[str, Any]) -> None:
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            perf = data_dict.get("performance", {})

            timestamp = datetime.utcnow().isoformat() + "Z"

            cursor.execute(
                """
                INSERT INTO performance_snapshots (
                    hotkey, timestamp,
                    total_volume_usd, trade_count, realized_profit_usd,
                    unrealized_profit_usd, win_rate, total_fees_paid_usd,
                    open_positions_count, referral_count, referral_volume
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    hotkey,
                    timestamp,
                    perf.get("total_volume_usd"),
                    perf.get("trade_count"),
                    perf.get("realized_profit_usd"),
                    perf.get("unrealized_profit_usd"),
                    perf.get("win_rate"),
                    perf.get("total_fees_paid_usd"),
                    perf.get("open_positions_count"),
                    perf.get("referral_count"),
                    perf.get("referral_volume_usd"),
                ),
            )

            cursor.execute(
                """
                INSERT INTO miners (hotkey, last_seen_ts)
                VALUES (?, ?)
                ON CONFLICT(hotkey) DO UPDATE SET last_seen_ts = excluded.last_seen_ts
                """,
                (hotkey, timestamp),
            )

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to cache validation data for {hotkey}: {e}")

    def get_cached_validation_data(
        self, hotkeys: Sequence[str], max_age_days: int = 7
    ) -> List[Dict[str, Any]]:
        if not hotkeys:
            return []

        try:
            conn = self._get_conn()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cutoff_date = (datetime.utcnow() - timedelta(days=max_age_days)).isoformat()

            placeholders = ",".join("?" for _ in hotkeys)
            query = f"""
                SELECT * FROM performance_snapshots
                WHERE hotkey IN ({placeholders})
                AND timestamp > ?
                ORDER BY timestamp DESC
            """

            query = f"""
                SELECT * FROM (
                    SELECT *,
                           ROW_NUMBER() OVER (PARTITION BY hotkey ORDER BY timestamp DESC) as rn
                    FROM performance_snapshots
                    WHERE hotkey IN ({placeholders})
                    AND timestamp > ?
                ) WHERE rn = 1
            """

            params = list(hotkeys) + [cutoff_date]
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            results = []
            for row in rows:
                data = dict(row)
                perf = {
                    "total_volume_usd": data["total_volume_usd"],
                    "trade_count": data["trade_count"],
                    "realized_profit_usd": data["realized_profit_usd"],
                    "unrealized_profit_usd": data["unrealized_profit_usd"],
                    "win_rate": data["win_rate"],
                    "total_fees_paid_usd": data["total_fees_paid_usd"],
                    "open_positions_count": data["open_positions_count"],
                    "referral_count": data["referral_count"],
                    "referral_volume_usd": data["referral_volume"],
                }

                record = {
                    "hotkey": data["hotkey"],
                    "performance": perf,
                }
                results.append(record)

            return results

        except Exception as e:
            logger.error(f"Failed to retrieve cached data: {e}")
            return []

    def delete_cached_validation_data(self, hotkeys: Sequence[str]) -> None:
        if not hotkeys:
            return

        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            placeholders = ",".join("?" for _ in hotkeys)
            cursor.execute(
                f"DELETE FROM performance_snapshots WHERE hotkey IN ({placeholders})",
                list(hotkeys),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to delete cached data: {e}")

    def cleanup_old_cache(self, max_age_days: int = 7) -> int:
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            cutoff_date = (datetime.utcnow() - timedelta(days=max_age_days)).isoformat()

            cursor.execute(
                "DELETE FROM performance_snapshots WHERE timestamp < ?",
                (cutoff_date,),
            )
            deleted = cursor.rowcount
            conn.commit()
            conn.execute("VACUUM")
            conn.close()

            return deleted
        except Exception as e:
            logger.error(f"Failed to cleanup cache: {e}")
            return 0

    def add_scoring_run(
        self, scores: Dict[str, float], reason: str = "ema_update"
    ) -> None:
        if not scores:
            return

        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            timestamp = datetime.utcnow().isoformat() + "Z"

            data = [
                (timestamp, hotkey, score, reason) for hotkey, score in scores.items()
            ]

            cursor.executemany(
                "INSERT INTO scoring_runs (ts, hotkey, score, reason) VALUES (?, ?, ?, ?)",
                data,
            )

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to save scoring run: {e}")

    def get_latest_scores(self) -> Dict[str, float]:
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            query = """
                SELECT hotkey, score
                FROM (
                    SELECT hotkey, score,
                           ROW_NUMBER() OVER (PARTITION BY hotkey ORDER BY ts DESC) as rn
                    FROM scoring_runs
                )
                WHERE rn = 1
            """

            cursor.execute(query)
            rows = cursor.fetchall()
            conn.close()

            return {row[0]: row[1] for row in rows}
        except Exception as e:
            logger.error(f"Failed to retrieve latest scores: {e}")
            return {}
