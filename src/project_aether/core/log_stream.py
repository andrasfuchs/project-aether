"""In-memory log stream support for live diagnostics in the Streamlit UI."""

from __future__ import annotations

import logging
import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Deque


@dataclass
class LogEntry:
    timestamp: str
    level: str
    levelno: int
    logger_name: str
    message: str
    formatted: str


class InMemoryLogHandler(logging.Handler):
    """Thread-safe ring buffer logging handler for live log tailing."""

    def __init__(self, max_entries: int = 5000, level: int = logging.DEBUG) -> None:
        super().__init__(level=level)
        self._entries: Deque[LogEntry] = deque(maxlen=max_entries)
        self._lock = threading.Lock()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            formatted = self.format(record)
            message = record.getMessage()
            entry = LogEntry(
                timestamp=datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
                level=record.levelname,
                levelno=record.levelno,
                logger_name=record.name,
                message=message,
                formatted=formatted,
            )
            with self._lock:
                self._entries.append(entry)
        except Exception:
            self.handleError(record)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def total_entries(self) -> int:
        with self._lock:
            return len(self._entries)

    def snapshot(
        self,
        *,
        min_level: int = logging.DEBUG,
        logger_filter: str = "",
        text_filter: str = "",
        limit: int = 400,
    ) -> list[LogEntry]:
        logger_filter = (logger_filter or "").strip().lower()
        text_filter = (text_filter or "").strip().lower()

        with self._lock:
            entries = list(self._entries)

        if min_level > logging.NOTSET:
            entries = [entry for entry in entries if entry.levelno >= min_level]

        if logger_filter:
            entries = [entry for entry in entries if logger_filter in entry.logger_name.lower()]

        if text_filter:
            entries = [entry for entry in entries if text_filter in entry.message.lower()]

        if limit > 0 and len(entries) > limit:
            entries = entries[-limit:]

        return entries


_handler: InMemoryLogHandler | None = None
_handler_lock = threading.Lock()


def install_log_stream_handler(
    *,
    max_entries: int = 5000,
    level: int = logging.DEBUG,
) -> InMemoryLogHandler:
    """Attach an in-memory handler to the root logger once and return it."""
    global _handler
    with _handler_lock:
        root_logger = logging.getLogger()

        if _handler is None:
            handler = InMemoryLogHandler(max_entries=max_entries, level=level)
            handler.setFormatter(
                logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            )
            _handler = handler

        if _handler not in root_logger.handlers:
            root_logger.addHandler(_handler)

        return _handler


def get_log_stream_handler() -> InMemoryLogHandler | None:
    return _handler
