"""Length-framed, checksummed, fsynced local material journal."""

from __future__ import annotations

import fcntl
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


class JournalWriterLockError(JournalError):
    """Raised when another live ledger owns this journal directory."""


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
    """Append-only file journal with one exclusive writer per directory."""

    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "material.journal"
        self.lock_path = self.directory / "material.journal.lock"
        self._lock_handle: Any = None

    def acquire_writer(self) -> None:
        if self._lock_handle is not None:
            return
        handle = self.lock_path.open("a+b")
        try:
            fcntl.flock(
                handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB
            )
        except OSError as exc:
            handle.close()
            raise JournalWriterLockError(
                f"journal directory {str(self.directory)!r} already has a "
                "live writer"
            ) from exc
        self._lock_handle = handle

    def release_writer(self) -> None:
        handle = self._lock_handle
        if handle is None:
            return
        self._lock_handle = None
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()

    def __del__(self) -> None:
        try:
            self.release_writer()
        except Exception:
            pass

    def _read_frames(
        self,
    ) -> tuple[list[dict[str, Any]], int, bool]:
        if not self.path.exists():
            return [], 0, False
        data = self.path.read_bytes()
        records: list[dict[str, Any]] = []
        offset = 0
        torn_tail = False
        while offset < len(data):
            remaining = len(data) - offset
            if remaining < _FRAME_HEADER:
                if not records:
                    raise CorruptJournalError("journal has no complete header")
                torn_tail = True
                break
            length = int.from_bytes(
                data[offset : offset + _LENGTH_BYTES], "big"
            )
            frame_length = _FRAME_HEADER + length
            if remaining < frame_length:
                if not records:
                    raise CorruptJournalError("journal header is incomplete")
                torn_tail = True
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
        return records, offset, torn_tail

    def _truncate_tail(self, valid_length: int) -> None:
        with self.path.open("r+b") as handle:
            handle.truncate(valid_length)
            handle.flush()
            os.fsync(handle.fileno())
        directory_fd = os.open(self.directory, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)

    def read_records(self) -> list[dict[str, Any]]:
        records, _, _ = self._read_frames()
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
        records, valid_length, torn_tail = self._read_frames()
        if torn_tail:
            self._truncate_tail(valid_length)
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
