"""Length-framed, checksummed, fsynced local material journal."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any


class JournalError(ValueError):
    """Base error for local journal failures."""


class CorruptJournalError(JournalError):
    """Raised when a complete journal record cannot be trusted."""


class JournalHeaderError(JournalError):
    """Raised when an existing journal is bound to a different run."""


def canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise JournalError(f"value is not canonical JSON: {exc}") from exc


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


_LENGTH_BYTES = 8
_DIGEST_BYTES = 32
_FRAME_HEADER = _LENGTH_BYTES + _DIGEST_BYTES


class Journal:
    """Append-only file journal with a durable frame per record."""

    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "material.journal"

    def read_records(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        data = self.path.read_bytes()
        records: list[dict[str, Any]] = []
        offset = 0
        while offset < len(data):
            remaining = len(data) - offset
            if remaining < _FRAME_HEADER:
                if not records:
                    raise CorruptJournalError("journal has no complete header")
                break
            length = int.from_bytes(
                data[offset : offset + _LENGTH_BYTES], "big"
            )
            frame_length = _FRAME_HEADER + length
            if remaining < frame_length:
                if not records:
                    raise CorruptJournalError("journal header is incomplete")
                break
            digest = data[
                offset + _LENGTH_BYTES : offset + _FRAME_HEADER
            ]
            payload = data[
                offset + _FRAME_HEADER : offset + frame_length
            ]
            if hashlib.sha256(payload).digest() != digest:
                raise CorruptJournalError(
                    f"checksum failure at journal record {len(records)}"
                )
            try:
                record = json.loads(payload.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise CorruptJournalError(
                    f"malformed journal record {len(records)}: {exc}"
                ) from exc
            if not isinstance(record, dict):
                raise CorruptJournalError("journal record must be an object")
            records.append(record)
            offset += frame_length
        return records

    def append(self, record: Mapping[str, Any]) -> None:
        payload = canonical_json(record).encode("utf-8")
        frame = (
            len(payload).to_bytes(_LENGTH_BYTES, "big")
            + hashlib.sha256(payload).digest()
            + payload
        )
        is_new = not self.path.exists()
        with self.path.open("ab") as handle:
            handle.write(frame)
            handle.flush()
            os.fsync(handle.fileno())
        if is_new:
            directory_fd = os.open(self.directory, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)

    def initialize(self, header: Mapping[str, Any]) -> list[dict[str, Any]]:
        records = self.read_records()
        if not records:
            if self.path.exists() and self.path.stat().st_size:
                raise CorruptJournalError("journal has no complete header")
            self.append(header)
            return []
        if records[0] != dict(header):
            raise JournalHeaderError(
                "journal run/config identity does not match this ledger"
            )
        return records[1:]
