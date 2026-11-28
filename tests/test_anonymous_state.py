"""Переносим только те области состояния, которые доступны выбранному игроку."""

from copy import deepcopy
from unittest.mock import patch

import pytest
from test_golden_games import make_event
from test_voice_dialog_parity import old_game

import alice_serverless
import shared_alice_serverless
from game import Game


@pytest.mark.parametrize('fallback', [False, True], ids=['legacy', 'pilot-fallback'])
def test_anonymous_setup_and_resume_use_only_application(monkeypatch, fallback):
    handler = shared_alice_serverless.handler if fallback else alice_serverless.handler
    monkeypatch.setenv('SHARED_GAMES_ENABLED', 'false')
    monkeypatch.setattr('shared_chess.runtime.services', lambda: pytest.fail('Must not open YDB'))
    event = make_event('', new=True)
    event['session'].pop('user')
    # Даже если в запросе осталось user-состояние, аноним не должен его наследовать.
    event['state']['user'] = old_game()
    for command, stage in [('', 'WAITING_CONFIRM'), ('да', 'WAITING_COLOR'), ('белые', 'WAITING_MOVE')]:
        event['request']['command'] = command
        reply = handler(event, None)
        assert 'user_state_update' not in reply
        assert reply['application_state']['game_state']['skill_state'] == stage
        event['state']['application'] = reply['application_state']
        event['state']['session'] = reply['session_state']
        event['session']['message_id'] += 1
        event['session']['new'] = False

    # В новой сессии previous_response и message_id прежней сессии не передаются.
    event['session'].update(session_id='next-session', message_id=0, new=True)
    event['state']['session'] = {}
    event['request']['command'] = ''
    resumed = handler(event, None)
    assert resumed['application_state'] == reply['application_state']
    assert 'Продолжим нашу игру' in resumed['response']['text']


@pytest.mark.parametrize('anonymous', [False, True])
@pytest.mark.parametrize('failure', ['construct', 'restore', 'dispatch'])
def test_fatal_error_preserves_selected_input_state(anonymous, failure):
    event = make_event('')
    if anonymous:
        event['session'].pop('user')
    scope, output = ('application', 'application_state') if anonymous else ('user', 'user_state_update')
    saved = {'game_state': Game(game_state=old_game()['game_state']).serialize_state()}
    event['state'][scope] = deepcopy(saved)
    target = {
        'construct': 'alice_serverless.AliceChess',
        'restore': 'alice_chess.Game',
        'dispatch': 'alice_chess.SpecialIntentHandler',
    }[failure]
    if failure == 'restore':
        # Первый Game создаётся пустым в __init__, второй восстанавливает партию.
        effect = [Game(), RuntimeError('restore failed')]
    else:
        effect = RuntimeError('request failed')
    with patch(target, side_effect=effect):
        reply = alice_serverless.handler(event, None)
    assert reply[output] == saved
    assert ('user_state_update' if anonymous else 'application_state') not in reply
    assert reply['response']['end_session']


def test_sign_in_and_sign_out_do_not_merge_games():
    event = make_event('', new=True)
    event['state']['application'] = old_game()
    reply = alice_serverless.handler(event, None)
    # У аккаунта нет игры: нельзя подхватить анонимную партию приложения.
    assert reply['user_state_update']['game_state']['skill_state'] == 'WAITING_CONFIRM'
    assert 'application_state' not in reply

    event['state']['user'] = reply['user_state_update']
    event['session'].pop('user')
    signed_out = alice_serverless.handler(event, None)
    assert signed_out['application_state']['game_state']['board_state'] == old_game()['game_state']['board_state']
    assert signed_out['application_state']['game_state']['skill_state'] == 'WAITING_MOVE'
    assert 'user_state_update' not in signed_out
