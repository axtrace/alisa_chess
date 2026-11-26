"""Ленивая конфигурация: сбой YDB никогда не переключает партии на SQLite."""

import os
from functools import lru_cache

from shared_chess.auth import DeviceAuth
from shared_chess.repository import SQLiteRepository
from shared_chess.service import GameService


@lru_cache(maxsize=1)
def services():
    backend = os.environ.get('CHESS_STORAGE', 'ydb')
    if backend == 'sqlite':
        repository = SQLiteRepository(os.environ.get('CHESS_SQLITE_PATH', 'prototype-data/chess.sqlite'))
    elif backend == 'ydb':
        from shared_chess.ydb_repository import YdbRepository

        repository = YdbRepository(
            os.environ['YDB_ENDPOINT'], os.environ['YDB_DATABASE'], os.environ.get('YDB_TABLE_PREFIX', 'chess_')
        )
    else:
        raise ValueError('CHESS_STORAGE must be ydb or sqlite')
    return repository, GameService(repository), DeviceAuth(repository)
