from __future__ import annotations

import json
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import IntEnum
from typing import Any, Dict, Optional


class LogLevel(IntEnum):
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40


@dataclass(slots=True, frozen=True)
class LogRecord:
    timestamp: str
    level: str
    event: str
    message: str
    fields: Dict[str, Any]


class BotLogger:
    """
    Легковесный structured logger для stderr.

    Цели:
    - единый формат логов по всему проекту;
    - минимальный overhead;
    - удобство дебага боёв;
    - отсутствие зависимости от внешних библиотек.
    """

    def __init__(
        self,
        *,
        level: LogLevel = LogLevel.INFO,
        emit_json: bool = False,
    ) -> None:
        self._level = level
        self._emit_json = emit_json

    def debug(self, event: str, message: str, **fields: Any) -> None:
        self._log(LogLevel.DEBUG, event, message, fields)

    def info(self, event: str, message: str, **fields: Any) -> None:
        self._log(LogLevel.INFO, event, message, fields)

    def warning(self, event: str, message: str, **fields: Any) -> None:
        self._log(LogLevel.WARNING, event, message, fields)

    def error(self, event: str, message: str, **fields: Any) -> None:
        self._log(LogLevel.ERROR, event, message, fields)

    def exception(self, event: str, message: str, **fields: Any) -> None:
        fields = dict(fields)
        fields["traceback"] = traceback.format_exc()
        self._log(LogLevel.ERROR, event, message, fields)

    def _log(
        self,
        level: LogLevel,
        event: str,
        message: str,
        fields: Optional[Dict[str, Any]] = None,
    ) -> None:
        if level < self._level:
            return

        record = LogRecord(
            timestamp=self._utc_now_iso(),
            level=level.name,
            event=event,
            message=message,
            fields=fields or {},
        )

        rendered = self._render(record)
        print(rendered, file=sys.stderr, flush=False)

    def _render(self, record: LogRecord) -> str:
        if self._emit_json:
            payload = {
                "ts": record.timestamp,
                "level": record.level,
                "event": record.event,
                "message": record.message,
                "fields": self._sanitize_fields(record.fields),
            }
            return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

        fields_str = self._render_kv(record.fields)
        if fields_str:
            return (
                f"[{record.timestamp}] "
                f"[{record.level}] "
                f"[{record.event}] "
                f"{record.message} | {fields_str}"
            )

        return f"[{record.timestamp}] [{record.level}] [{record.event}] {record.message}"

    def _render_kv(self, fields: Dict[str, Any]) -> str:
        safe = self._sanitize_fields(fields)
        parts = [f"{key}={value}" for key, value in safe.items()]
        return " ".join(parts)

    def _sanitize_fields(self, fields: Dict[str, Any]) -> Dict[str, Any]:
        sanitized: Dict[str, Any] = {}
        for key, value in fields.items():
            sanitized[str(key)] = self._sanitize_value(value)
        return sanitized

    def _sanitize_value(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, dict):
            return {str(k): self._sanitize_value(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._sanitize_value(v) for v in value]
        return repr(value)

    @staticmethod
    def _utc_now_iso() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="milliseconds")
