"""Транзакционный контракт; SQLite — только локальная проверка, YDB — облако."""

import json
import sqlite3
import threading
from pathlib import Path

TABLES = ('players', 'games', 'commands', 'replies', 'device_sessions', 'pairings')


def encode(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), sort_keys=True)


class SQLiteRepository:
    """Изолированная БД для разработки, не автоматический fallback после сбоя YDB."""

    def __init__(self, filename):
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        self.filename = str(filename)
        self._local = threading.local()
        with sqlite3.connect(self.filename) as db:
            db.execute('PRAGMA journal_mode=WAL')
            for table in TABLES:
                db.execute(
                    f'CREATE TABLE IF NOT EXISTS {table} '
                    '(owner_id TEXT, record_id TEXT, payload TEXT NOT NULL, '
                    'PRIMARY KEY(owner_id, record_id))'
                )

    def atomic(self, operation):
        with sqlite3.connect(self.filename, timeout=5) as db:
            db.execute('BEGIN IMMEDIATE')
            return operation(SQLiteTransaction(db))


class SQLiteTransaction:
    def __init__(self, db):
        self.db = db

    def get(self, table, owner, key=''):
        assert table in TABLES
        row = self.db.execute(f'SELECT payload FROM {table} WHERE owner_id=? AND record_id=?', (owner, key)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, table, owner, key, value):
        assert table in TABLES
        self.db.execute(
            f'INSERT INTO {table} VALUES (?, ?, ?) '
            'ON CONFLICT(owner_id, record_id) DO UPDATE SET payload=excluded.payload',
            (owner, key, encode(value)),
        )
