"""Запускается только явно, на отдельном test_chess_* префиксе таблиц."""

import os
import uuid

import pytest


@pytest.mark.skipif(os.environ.get('CHESS_YDB_INTEGRATION') != '1', reason='Нужна явно разрешённая тестовая YDB')
def test_ydb_transactions_and_command_replay():
    import chess

    from shared_chess.service import GameService
    from shared_chess.ydb_repository import YdbRepository

    prefix = os.environ['YDB_TABLE_PREFIX']
    assert prefix.startswith('test_chess_'), 'Только изолированные тестовые таблицы'
    repo = YdbRepository(os.environ['YDB_ENDPOINT'], os.environ['YDB_DATABASE'], prefix)
    try:
        repo.create_schema()
        calls = []

        def engine(board, level):
            calls.append(board.fen())
            return next(iter(board.legal_moves))

        service = GameService(repo, engine=engine)
        owner = 'integration-' + str(uuid.uuid4())
        new = {
            'request_id': str(uuid.uuid4()),
            'game_id': None,
            'expected_revision': None,
            'type': 'new_game',
            'payload': {},
        }
        created = service.execute(owner, 'new', new)['snapshot']
        move = {
            'request_id': str(uuid.uuid4()),
            'game_id': created['game_id'],
            'expected_revision': 1,
            'type': 'move',
            'payload': {'uci': 'e2e4'},
        }
        result = service.execute(owner, 'move', move)
        assert service.execute(owner, 'move', move) == result
        assert result['snapshot']['revision'] == 2
        assert result['snapshot']['fen'] != chess.STARTING_FEN
        assert len(calls) == 1
    finally:
        repo.close()


@pytest.mark.skipif(os.environ.get('CHESS_YDB_INTEGRATION') != '1', reason='Нужна явно разрешённая тестовая YDB')
def test_ydb_native_skill_and_device_share_game(monkeypatch):
    from types import SimpleNamespace

    import shared_alice_serverless
    from shared_chess.api import ChessApi
    from shared_chess.auth import DeviceAuth
    from shared_chess.dialogs_identity import dialogs_owner
    from shared_chess.service import GameService
    from shared_chess.ydb_repository import YdbRepository

    prefix = os.environ['YDB_TABLE_PREFIX']
    assert prefix.startswith('test_chess_')
    repo = YdbRepository(os.environ['YDB_ENDPOINT'], os.environ['YDB_DATABASE'], prefix)
    try:
        service = GameService(repo, engine=lambda board, level: next(iter(board.legal_moves)))
        auth = DeviceAuth(repo)
        monkeypatch.setattr('shared_chess.runtime.services', lambda: (repo, service, auth))
        monkeypatch.setenv('SHARED_GAMES_ENABLED', 'true')
        monkeypatch.setenv('SHARED_ALICE_AUTH', 'dialogs_iam')
        monkeypatch.setenv('SHARED_DIALOGS_FUNCTION_ID', 'private-integration-function')
        monkeypatch.setenv('SHARED_DIALOGS_SKILL_ID', 'integration-skill')
        event = {
            'session': {
                'skill_id': 'integration-skill',
                'session_id': str(uuid.uuid4()),
                'message_id': 0,
                'user': {'user_id': 'synthetic-' + str(uuid.uuid4())},
            },
            'request': {'command': ''},
            'state': {'user': {}, 'session': {}},
        }
        context = SimpleNamespace(function_name='private-integration-function')
        owner = dialogs_owner(event, context)
        monkeypatch.setenv('SHARED_DIALOGS_ALLOWED_OWNER', owner)
        pair = auth.create_pairing(owner)
        event['request']['command'] = 'подключить экран ' + pair['code']
        first = shared_alice_serverless.handler(event, context)
        event['state']['session'] = first['session_state']
        event['session']['message_id'] = 1
        event['request']['command'] = 'да'
        shared_alice_serverless.handler(event, context)
        api = ChessApi(service, auth)
        header = 'Bearer ' + pair['device_token']
        status, created = api.dispatch(
            'POST',
            '/v1/commands',
            {
                'request_id': str(uuid.uuid4()),
                'game_id': None,
                'expected_revision': None,
                'type': 'new_game',
                'payload': {},
            },
            header,
        )
        assert status == 200 and created['snapshot']['revision'] == 1
        event['state']['session'] = {}
        event['session']['message_id'] = 2
        event['request']['command'] = 'e2e4'
        reply = shared_alice_serverless.handler(event, context)
        assert reply['user_state_update']['game_ref']['revision'] == 2
        assert shared_alice_serverless.handler(event, context)['response'] == reply['response']
        status, current = api.dispatch('GET', '/v1/games/current', {}, header)
        assert status == 200 and current['revision'] == 2
        assert current['history_san'][0] == 'e4' and len(current['history_san']) == 2
        assert current['game_id'] == created['snapshot']['game_id']
    finally:
        repo.close()
