from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path


class RateLimiter:
    def __init__(self) -> None:
        self.max_requests_per_minute = int(os.getenv("VNSTOCK_MAX_REQUESTS_PER_MINUTE", "30"))
        self.request_sleep_seconds = float(os.getenv("VNSTOCK_REQUEST_SLEEP_SECONDS", "1.0"))
        self.max_retries = int(os.getenv("VNSTOCK_MAX_RETRIES", "3"))
        self.backoff_seconds = float(os.getenv("VNSTOCK_BACKOFF_SECONDS", "10"))
        self._last_request_at: float | None = None
        self._failure_count = 0
        self._error_log_path = Path(os.getenv("VNSTOCK_INGESTION_ERRORS_PATH", "data/ingestion_errors.jsonl"))

    def wait(self) -> None:
        interval_seconds = self.request_sleep_seconds
        if self.max_requests_per_minute > 0:
            interval_seconds = max(interval_seconds, 60.0 / self.max_requests_per_minute)

        if self._last_request_at is None:
            time.sleep(interval_seconds)
            self._last_request_at = time.monotonic()
            return

        elapsed = time.monotonic() - self._last_request_at
        remaining = interval_seconds - elapsed
        if remaining > 0:
            time.sleep(remaining)
        self._last_request_at = time.monotonic()

    def register_success(self) -> None:
        self._failure_count = 0

    def register_failure(self, error: Exception | str, context: str | None = None) -> bool:
        self._failure_count += 1
        if self._failure_count >= self.max_retries:
            self._write_ingestion_error(error, context=context)
            return False
        return True

    def backoff(self) -> None:
        time.sleep(self.backoff_seconds)

    def _write_ingestion_error(self, error: Exception | str, context: str | None = None) -> None:
        self._error_log_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "context": context,
            "error": str(error),
            "failure_count": self._failure_count,
        }
        with self._error_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=True) + "\n")
