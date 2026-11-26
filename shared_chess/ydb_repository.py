"""YDB Query API: только короткие Serializable RW транзакции, без движка."""

import json
import re

from shared_chess.deadline import remaining
from shared_chess.repository import TABLES, encode


class YdbRepository:
    def __init__(self, endpoint, database, prefix='chess_', driver=None):
        import ydb

        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', prefix):
            raise ValueError('Некорректный префикс таблиц')
        self.prefix = prefix
        self.ydb = ydb
        self.driver = driver or ydb.Driver(
            endpoint=endpoint, database=database, credentials=ydb.credentials_from_env_variables()
        )
        try:
            self.driver.wait(timeout=remaining(1.0), fail_fast=True)
        except Exception:
            self.driver.stop()
            raise
        self.pool = ydb.QuerySessionPool(self.driver, size=4)

    def create_schema(self):
        """Вызывается явно при настройке, никогда не из обработчика запросов."""
        for table in TABLES:
            self.pool.execute_with_retries(
                f'CREATE TABLE IF NOT EXISTS `{self.prefix}{table}` '
                '(owner_id Utf8 NOT NULL, record_id Utf8 NOT NULL, payload Utf8 NOT NULL, '
                'PRIMARY KEY(owner_id, record_id))'
            )

    def atomic(self, operation):
        def run(session):
            remaining()
            with session.transaction(self.ydb.QuerySerializableReadWrite()) as tx:
                transaction = YdbTransaction(tx, self.prefix, self.ydb)
                result = operation(transaction)
                transaction.commit()
                return result

        return self.pool.retry_operation_sync(
            run,
            retry_settings=self.ydb.RetrySettings(
                max_retries=2,
                max_session_acquire_timeout=remaining(1.0),
                get_session_client_timeout=remaining(1.0),
                fast_backoff_settings=self.ydb.BackoffSettings(ceiling=2, slot_duration=0.01),
                slow_backoff_settings=self.ydb.BackoffSettings(ceiling=2, slot_duration=0.02),
            ),
        )

    def close(self):
        self.pool.stop()
        self.driver.stop()


class YdbTransaction:
    def __init__(self, tx, prefix, ydb):
        self.tx, self.prefix, self.ydb = tx, prefix, ydb
        self.cache = {}
        self.writes = {}

    def _parameters(self, **values):
        return {f'${name}': self.ydb.TypedValue(value, self.ydb.PrimitiveType.Utf8) for name, value in values.items()}

    def get(self, table, owner, key=''):
        assert table in TABLES
        identity = (table, owner, key)
        if identity in self.cache:
            value = self.cache[identity]
            return json.loads(value) if value is not None else None
        query = (
            f'DECLARE $owner AS Utf8; DECLARE $key AS Utf8; '
            f'SELECT payload FROM `{self.prefix}{table}` WHERE owner_id=$owner AND record_id=$key;'
        )
        with self.tx.execute(
            query,
            self._parameters(owner=owner, key=key),
            settings=self.ydb.BaseRequestSettings().with_timeout(remaining()),
        ) as stream:
            rows = [row for result in stream for row in result.rows]
        value = rows[0].payload if rows else None
        self.cache[identity] = value
        return json.loads(value) if value is not None else None

    def put(self, table, owner, key, value):
        assert table in TABLES
        identity = (table, owner, key)
        self.cache[identity] = encode(value)
        self.writes[identity] = self.cache[identity]

    def commit(self):
        # One write RPC per transaction; reads after put use the local transaction view.
        # This also avoids premature read-after-write flushes in YDB.
        declarations, statements, parameters = [], [], {}
        for index, ((table, owner, key), payload) in enumerate(self.writes.items()):
            values = {f'owner_{index}': owner, f'key_{index}': key, f'payload_{index}': payload}
            declarations.extend(f'DECLARE ${name} AS Utf8;' for name in values)
            parameters.update(self._parameters(**values))
            statements.append(
                f'UPSERT INTO `{self.prefix}{table}` (owner_id,record_id,payload) '
                f'VALUES ($owner_{index},$key_{index},$payload_{index});'
            )
        query = ' '.join(declarations + statements) or 'SELECT 1;'
        with self.tx.execute(
            query, parameters, commit_tx=True, settings=self.ydb.BaseRequestSettings().with_timeout(remaining())
        ) as stream:
            list(stream)
