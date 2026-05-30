"""Единая конфигурация логирования для навыка.

Главные принципы:
- настройка корневого логгера выполняется один раз — в точке входа
  ([`alice_serverless.handler`](alice_serverless.py:1));
- модули **не** должны вызывать `logger.setLevel(...)` — уровень определяется
  переменной окружения `LOG_LEVEL` (по умолчанию `INFO`);
- формат вывода — JSON (одна строка на запись), удобен для Yandex Monitoring;
- контекст запроса (session_id, message_id, user_id) хранится в `ContextVar`
  и автоматически попадает в каждую запись через `extra`.
"""

from __future__ import annotations

import json
import logging
import os
from contextvars import ContextVar
from typing import Any, Dict, Optional

# Контекст текущего запроса. Заполняется в начале обработки в
# `bind_request_context()` и автоматически подмешивается в каждую запись.
_request_context: ContextVar[Dict[str, Any]] = ContextVar('alisa_chess_request_context', default={})

# Поля LogRecord, которые не нужно дублировать в "extra".
_RESERVED_LOG_RECORD_FIELDS = {
    'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename',
    'module', 'exc_info', 'exc_text', 'stack_info', 'lineno', 'funcName',
    'created', 'msecs', 'relativeCreated', 'thread', 'threadName',
    'processName', 'process', 'message', 'asctime', 'taskName',
}


class JsonFormatter(logging.Formatter):
    """Форматтер логов в JSON.

    Подмешивает текущий request-контекст (если есть) и поля, переданные
    через `extra=...` в вызовы логгера.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            'ts': self.formatTime(record, '%Y-%m-%dT%H:%M:%S'),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        if record.exc_info:
            payload['exc_info'] = self.formatException(record.exc_info)

        # Контекст запроса.
        ctx = _request_context.get()
        if ctx:
            payload['ctx'] = ctx

        # Поля из extra=...
        for key, value in record.__dict__.items():
            if key in _RESERVED_LOG_RECORD_FIELDS:
                continue
            if key.startswith('_'):
                continue
            payload[key] = value

        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logging(level: Optional[str] = None) -> None:
    """Инициализирует корневой логгер один раз за процесс.

    Параметры:
        level: имя уровня (`DEBUG`/`INFO`/...). Если `None`, читается
            переменная окружения `LOG_LEVEL`, по умолчанию `INFO`.

    Безопасно вызывать многократно — повторных хендлеров не плодит.
    """
    resolved_level = (level or os.environ.get('LOG_LEVEL') or 'INFO').upper()

    root = logging.getLogger()
    root.setLevel(resolved_level)

    # Если уже инициализирован нашим хендлером — не дублируем.
    for handler in root.handlers:
        if getattr(handler, '_alisa_chess_json', False):
            return

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    handler._alisa_chess_json = True  # type: ignore[attr-defined]
    root.addHandler(handler)


def bind_request_context(**fields: Any) -> None:
    """Связывает поля с текущим request-контекстом.

    Вызов:
        bind_request_context(session_id="...", message_id="...", user_id="...")

    Поля попадут в каждую последующую запись логов до сброса/перезаписи.
    """
    current = dict(_request_context.get())
    current.update({k: v for k, v in fields.items() if v is not None})
    _request_context.set(current)


def clear_request_context() -> None:
    """Очищает request-контекст (вызывать в конце обработки запроса)."""
    _request_context.set({})


def get_request_context() -> Dict[str, Any]:
    """Возвращает копию текущего request-контекста (для диагностики)."""
    return dict(_request_context.get())
