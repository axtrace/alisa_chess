"""Глобальные фикстуры pytest для тестов alisa_chess.

Главная цель — гарантировать, что ни один unit-тест не запустит реальный
бинарь Stockfish. Любой случайный путь, который дотянется до
`chess.engine.SimpleEngine.popen_uci`, получит заглушку, возвращающую
тихий ход e2e4. Тесты, которым нужен другой ответ движка, могут
переопределить патч локально (через `@patch('chess.engine.SimpleEngine.popen_uci')`).
"""

from unittest.mock import MagicMock, patch

import chess
import pytest


def _build_fake_engine():
    """Создаёт MagicMock, имитирующий минимальный API SimpleEngine."""
    fake_engine = MagicMock(name='FakeStockfishEngine')
    fake_result = MagicMock(name='FakeEngineResult')
    fake_result.move = chess.Move.from_uci('e2e4')
    fake_engine.play.return_value = fake_result
    fake_engine.configure.return_value = None
    fake_engine.quit.return_value = None
    fake_engine.id = {'name': 'FakeStockfish'}
    return fake_engine


@pytest.fixture(autouse=True)
def _stub_stockfish_engine():
    """Глобально подменяет `popen_uci`, чтобы исключить запуск реального Stockfish."""
    with patch(
        'chess.engine.SimpleEngine.popen_uci',
        side_effect=lambda *args, **kwargs: _build_fake_engine(),
    ) as mocked:
        yield mocked
