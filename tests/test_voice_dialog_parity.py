"""Один эталон голосового диалога для обычной и общей партии.

CHESS_YDB_INTEGRATION=1 запускает общую ветку на тестовой YDB вместо временной SQLite.
"""

import json
import os
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import chess
import pytest
from test_golden_games import make_event

import alice_serverless
import shared_alice_serverless
from shared_chess.auth import DeviceAuth
from shared_chess.dialogs_identity import dialogs_owner
from shared_chess.repository import SQLiteRepository, encode
from shared_chess.service import GameService

DATA = Path(__file__).parent / 'fixtures' / 'voice_dialog'
SCENARIOS = {
    'black': [('', {}), ('да', {}), ('черные', {'BLACK_WORD': {}})],
    'resume_undo': [
        ('', {}),
        (
            'конь f3',
            {
                'CHESS_MOVE': {
                    'slots': {
                        'piece': {'value': 'конь'},
                        'file_to': {'value': 'f'},
                        'rank_to': {'value': '3'},
                    }
                }
            },
        ),
        ('отмени ход', {'UNDO': {}}),
    ],
    'repeat': [('где мои кони?', {}), ('повтори', {'YANDEX.REPEAT': {}})],
    'new_game': [
        ('', {}),
        ('новая игра', {'NEW_GAME': {}}),
        ('нет', {}),
        ('новая игра', {'NEW_GAME': {}}),
        ('да', {}),
        ('белые', {'WHITE_WORD': {}}),
    ],
    'resign': [
        ('', {}),
        ('сдаюсь', {'RESIGN': {}}),
        ('повтори', {'YANDEX.REPEAT': {}}),
        ('нет', {}),
        ('сдаюсь', {'RESIGN': {}}),
        ('да', {}),
    ],
    'draw': [
        ('', {}),
        ('ничья', {'OFFER_DRAW': {}}),
        ('нет', {}),
        ('ничья', {'OFFER_DRAW': {}}),
        ('да', {}),
    ],
    'level': [
        ('', {}),
        ('уровень сложности', {'SET_SKILL_LEVEL': {}}),
        ('12', {}),
        ('покажи доску', {'SHOW_BOARD': {}}),
        ('помощь', {'YANDEX.HELP': {}}),
    ],
}


@pytest.fixture
def repository(tmp_path):
    if os.environ.get('CHESS_YDB_INTEGRATION') != '1':
        yield SQLiteRepository(tmp_path / 'games.sqlite')
        return

    from shared_chess.ydb_repository import YdbRepository

    prefix = os.environ['YDB_TABLE_PREFIX']
    assert prefix.startswith('test_chess_')
    repo = YdbRepository(os.environ['YDB_ENDPOINT'], os.environ['YDB_DATABASE'], prefix)
    try:
        yield repo
    finally:
        repo.close()


def old_game():
    board = chess.Board()
    board.push_san('e4')
    board.push_san('e5')
    # Версия без _version реально читается навыком как V1.
    return {
        'game_state': {
            'board_state': board.fen(),
            'prev_board_state': chess.STARTING_FEN,
            'last_move': 'e5',
            'skill_state': 'WAITING_MOVE',
            'user_color': 'WHITE',
            'skill_level': 8,
        }
    }


def play(scenario, handler, context, account, engine, current=None, *, anonymous=False):
    user = {} if scenario == 'black' else old_game()
    session = {}
    turns = []
    previous_snapshot = None
    for index, (command, intents) in enumerate(SCENARIOS[scenario]):
        event = make_event(command, intents, message_id=index, new=index == 0)
        event['session']['user']['user_id'] = account
        if anonymous:
            event['session'].pop('user')
            event['session']['application']['application_id'] = account
        scope, output = ('application', 'application_state') if anonymous else ('user', 'user_state_update')
        event['state'].update({scope: deepcopy(user), 'session': deepcopy(session)})
        calls = engine.play.call_count
        reply = handler(event, context)
        user, session = reply[output], reply['session_state']
        assert ('user_state_update' if anonymous else 'application_state') not in reply
        game = user.get('game_state', {})
        turn = {
            'response': reply['response'],
            'fen': game.get('board_state'),
            'stage': game.get('skill_state'),
            'color': game.get('user_color'),
            'level': game.get('skill_level'),
            'engine_calls': engine.play.call_count - calls,
        }
        if current:
            assert len(encode(session).encode()) <= 1024
            assert len(encode(user).encode()) <= 1024
            snapshot = current()
            if game.get('user_color'):
                assert snapshot['fen'] == turn['fen']
                assert snapshot['revision'] == user['game_ref']['revision']
                assert snapshot['skill_level'] == turn['level']
        if scenario == 'repeat' and index == 1:
            assert turn == turns[-1]
            if current:
                assert snapshot == previous_snapshot
        if scenario == 'resume_undo' and index == 1:
            # Повторная доставка с тем же message_id и уже принятым состоянием Диалогов.
            calls_after_move = engine.play.call_count
            if current:
                # Первый ответ потерян: Диалоги ещё не получили новые state и game_ref.
                replay = handler(deepcopy(event), context)
                assert replay == reply
            event['state'].update({scope: deepcopy(user), 'session': deepcopy(session)})
            duplicate = handler(event, context)
            assert duplicate == reply
            assert engine.play.call_count == calls_after_move
            if current:
                assert current() == snapshot
        if current:
            previous_snapshot = snapshot
        turns.append(turn)
    return turns


@pytest.mark.parametrize('scenario', SCENARIOS)
@pytest.mark.parametrize('anonymous', [False, True], ids=['account', 'anonymous'])
def test_dialog_parity(scenario, anonymous, repository, monkeypatch, _stub_stockfish_engine):
    context = SimpleNamespace(function_name='parity-function')
    account = 'parity-' + str(uuid4())
    monkeypatch.setenv('SHARED_GAMES_ENABLED', 'true')
    monkeypatch.setenv('SHARED_ALICE_AUTH', 'dialogs_iam')
    monkeypatch.setenv('SHARED_DIALOGS_FUNCTION_ID', context.function_name)
    event = make_event('')
    monkeypatch.setenv('SHARED_DIALOGS_SKILL_ID', event['session']['skill_id'])
    event['session']['user']['user_id'] = account
    if anonymous:
        event['session'].pop('user')
        event['session']['application']['application_id'] = account
    owner = dialogs_owner(event, context)
    setting = 'SHARED_DIALOGS_ALLOWED_APPLICATION_OWNER' if anonymous else 'SHARED_DIALOGS_ALLOWED_OWNER'
    monkeypatch.setenv(setting, owner)
    service = GameService(repository)
    monkeypatch.setattr('shared_chess.runtime.services', lambda: (repository, service, DeviceAuth(repository)))

    engine = Mock()
    engine.play.return_value.move = chess.Move.from_uci('e2e4' if scenario == 'black' else 'b8c6')
    _stub_stockfish_engine.side_effect = None
    _stub_stockfish_engine.return_value = engine
    legacy = play(scenario, alice_serverless.handler, context, account, engine, anonymous=anonymous)
    pilot = play(
        scenario,
        shared_alice_serverless.handler,
        context,
        account,
        engine,
        lambda: service.current(owner),
        anonymous=anonymous,
    )
    # Сравниваем весь response, включая кнопки, если они появились.
    if (DATA / f'{scenario}.json').exists():
        expected = json.loads((DATA / f'{scenario}.json').read_text())
        assert legacy == expected['legacy']
    assert pilot == legacy
