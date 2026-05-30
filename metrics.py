"""Минимальный слой метрик навыка.

Yandex Cloud Functions автоматически отдаёт в Yandex Monitoring базовые
метрики (количество вызовов, длительность, ошибки runtime). Для прикладных
метрик (cold start, ход компьютера, неоднозначные/невалидные ходы, тип ошибки)
используется лог-based подход: модуль пишет структурированную JSON-строку
в общий `logging`, а в Yandex Monitoring настраиваются log-метрики
по полю `event` / `metric`.

Использование:

    from metrics import emit_counter, measure_duration

    emit_counter('skill.cold_start')

    with measure_duration('skill.handler'):
        ...

    emit_counter('skill.move.invalid', tags={'reason': 'bad_san'})

Все события автоматически получают request-контекст из `logging_config`
(session_id / message_id / user_id), который пробрасывается через extra-поля.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Mapping
from contextlib import contextmanager

logger = logging.getLogger('alisa_chess.metrics')


def emit_counter(name: str, value: int = 1, tags: Mapping[str, str] | None = None) -> None:
    """Эмитит счётчик метрики в лог в виде структурированной записи."""
    logger.info(
        'metric',
        extra={
            'metric': name,
            'metric_kind': 'counter',
            'metric_value': value,
            'metric_tags': dict(tags) if tags else {},
        },
    )


def emit_gauge(name: str, value: float, tags: Mapping[str, str] | None = None) -> None:
    """Эмитит мгновенное значение (gauge) в лог."""
    logger.info(
        'metric',
        extra={
            'metric': name,
            'metric_kind': 'gauge',
            'metric_value': value,
            'metric_tags': dict(tags) if tags else {},
        },
    )


def emit_histogram(name: str, value: float, tags: Mapping[str, str] | None = None) -> None:
    """Эмитит наблюдение для гистограммы (длительности, размеры payload)."""
    logger.info(
        'metric',
        extra={
            'metric': name,
            'metric_kind': 'histogram',
            'metric_value': value,
            'metric_tags': dict(tags) if tags else {},
        },
    )


@contextmanager
def measure_duration(name: str, tags: Mapping[str, str] | None = None):
    """Контекстный менеджер: измеряет длительность блока и эмитит гистограмму (мс)."""
    started = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        emit_histogram(name, elapsed_ms, tags=tags)
