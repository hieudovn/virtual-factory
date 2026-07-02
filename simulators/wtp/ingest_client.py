"""Ingest Client — HTTP POST measurements to PlantOS with retry + buffer."""

from __future__ import annotations

import json
import time
from collections import deque
from typing import Any

import httpx

from .models import Measurement


class IngestClient:
    """HTTP client for PlantOS measurement ingestion.

    Features:
    - POST to {base_url}/api/v1/measurements/ingest
    - Retry with exponential backoff + jitter
    - Local ring buffer (up to max_buffer frames)
    - Auto-replay buffered frames when connection restores
    """

    def __init__(
        self,
        ingest_url: str,
        source: str = "wtp-sim-01",
        api_key: str = "",
        max_retries: int = 5,
        base_delay_s: float = 1.0,
        max_delay_s: float = 30.0,
        backoff_multiplier: float = 2.0,
        max_buffer: int = 3600,
    ) -> None:
        self.ingest_url = ingest_url
        self.source = source
        self.api_key = api_key
        self.max_retries = max_retries
        self.base_delay_s = base_delay_s
        self.max_delay_s = max_delay_s
        self.backoff_multiplier = backoff_multiplier
        self.max_buffer = max_buffer

        self.buffer: deque[list[Measurement]] = deque(maxlen=max_buffer)
        self.consecutive_errors: int = 0
        self.total_ingested: int = 0
        self.total_errors: int = 0
        self.last_error_time: float = 0.0
        self._client: httpx.Client | None = None

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=10.0)
        return self._client

    @property
    def status(self) -> str:
        if self.consecutive_errors == 0:
            return "connected"
        if self.consecutive_errors < self.max_retries:
            return "retrying"
        if len(self.buffer) > 0:
            return "buffering"
        return "failed"

    def post_measurements(self, measurements: list[Measurement]) -> bool:
        """Post a frame of measurements. Returns True if successful."""
        payload = {
            "measurements": [m.to_dict() for m in measurements]
        }

        for attempt in range(self.max_retries + 1):
            try:
                headers = {"Content-Type": "application/json"}
                if self.api_key:
                    headers["X-API-Key"] = self.api_key
                response = self.client.post(
                    self.ingest_url,
                    json=payload,
                    headers=headers,
                )
                if response.status_code < 500:
                    self.consecutive_errors = 0
                    self.total_ingested += len(measurements)
                    # Try to flush buffer
                    self._flush_buffer()
                    return True

            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError) as e:
                if attempt == self.max_retries:
                    self.consecutive_errors += 1
                    self.total_errors += 1
                    self.last_error_time = time.time()
                    self._buffer_frame(measurements)
                    return False

                # Exponential backoff with jitter
                delay = min(
                    self.base_delay_s * (self.backoff_multiplier ** attempt),
                    self.max_delay_s,
                )
                import random as rng
                delay *= 1.0 + rng.uniform(-0.2, 0.2)
                time.sleep(delay)

        self.consecutive_errors += 1
        self.total_errors += 1
        self._buffer_frame(measurements)
        return False

    def _buffer_frame(self, frame: list[Measurement]) -> None:
        """Buffer a frame locally when PlantOS is down."""
        self.buffer.append(frame)

    def _flush_buffer(self) -> int:
        """Replay buffered frames. Returns number of frames flushed."""
        if not self.buffer:
            return 0

        flushed = 0
        while self.buffer:
            frame = self.buffer[0]
            payload = {"measurements": [m.to_dict() for m in frame]}
            try:
                response = self.client.post(self.ingest_url, json=payload)
                if response.status_code < 500:
                    self.buffer.popleft()
                    self.total_ingested += len(frame)
                    flushed += 1
                else:
                    break
            except Exception:
                break

        return flushed

    def get_status(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "buffered_frames": len(self.buffer),
            "total_ingested": self.total_ingested,
            "total_errors": self.total_errors,
            "consecutive_errors": self.consecutive_errors,
            "last_error_time": self.last_error_time,
        }

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
