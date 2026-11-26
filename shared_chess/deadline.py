"""Один бюджет на весь запрос, включая повторы транзакций."""

import time
from contextlib import contextmanager
from contextvars import ContextVar

_deadline = ContextVar('chess_deadline', default=None)


def remaining(default=3.0):
    end = _deadline.get()
    seconds = default if end is None else min(default, end - time.monotonic())
    if seconds <= 0.02:
        raise TimeoutError('Request deadline reached')
    return seconds


@contextmanager
def budget(seconds):
    token = _deadline.set(time.monotonic() + seconds)
    try:
        yield
    finally:
        _deadline.reset(token)
