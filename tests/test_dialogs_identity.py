import copy
from types import SimpleNamespace

import pytest

import shared_alice_serverless
from shared_chess.auth import DeviceAuth
from shared_chess.dialogs_identity import dialogs_owner
from shared_chess.repository import SQLiteRepository
from shared_chess.service import GameService


@pytest.fixture
def native(monkeypatch, tmp_path):
    monkeypatch.setenv('SHARED_GAMES_ENABLED', 'true')
    monkeypatch.setenv('SHARED_ALICE_AUTH', 'dialogs_iam')
    monkeypatch.setenv('SHARED_DIALOGS_FUNCTION_ID', 'private-test-function')
    monkeypatch.setenv('SHARED_DIALOGS_SKILL_ID', 'test-skill')
    event = {
        'version': '1.0',
        'session': {
            'skill_id': 'test-skill',
            'session_id': 'session',
            'message_id': 0,
            'user': {'user_id': 'test-account'},
        },
        'request': {'command': 'покажи доску'},
        'state': {'user': {}, 'session': {}},
    }
    context = SimpleNamespace(function_name='private-test-function')
    owner = dialogs_owner(event, context)
    monkeypatch.setenv('SHARED_DIALOGS_ALLOWED_OWNER', owner)
    repo = SQLiteRepository(tmp_path / 'native.sqlite')
    service = GameService(repo, engine=lambda board, level: next(iter(board.legal_moves)))
    auth = DeviceAuth(repo)
    monkeypatch.setattr('shared_chess.runtime.services', lambda: (repo, service, auth))
    return event, context, owner, service, auth


def test_native_account_is_stable_across_apps_and_namespaced(native, monkeypatch):
    event, context, owner, _, _ = native
    other = copy.deepcopy(event)
    other['session']['user_id'] = 'forged-legacy-device-id'
    other['session']['application'] = {'application_id': 'another-device'}
    assert dialogs_owner(other, context) == owner
    other['session']['user']['user_id'] = 'different-account'
    assert dialogs_owner(other, context) != owner
    monkeypatch.setenv('SHARED_DIALOGS_SKILL_ID', 'other-skill')
    other['session']['skill_id'] = 'other-skill'
    other['session']['user']['user_id'] = 'test-account'
    assert dialogs_owner(other, context) != owner


@pytest.mark.parametrize('change', ['function', 'skill', 'http', 'missing-config'])
def test_native_rejects_untrusted_transport(native, monkeypatch, change):
    event, context, _, _, _ = native
    if change == 'function':
        context.function_name = 'public-device-api'
    elif change == 'skill':
        event['session']['skill_id'] = 'other-skill'
    elif change == 'http':
        event['httpMethod'] = 'POST'
    else:
        monkeypatch.delenv('SHARED_DIALOGS_FUNCTION_ID')
    monkeypatch.setattr('shared_chess.runtime.services', lambda: pytest.fail('Must not open YDB'))
    reply = shared_alice_serverless.handler(event, context)
    assert reply['user_state_update'] == event['state']['user']
    assert 'недоступна' in reply['response']['text']
    assert not reply['response']['end_session']


@pytest.mark.parametrize('anonymous', [False, True])
def test_native_non_tester_keeps_legacy_without_ydb(native, monkeypatch, anonymous):
    event, context, _, _, _ = native
    if anonymous:
        event['session'].pop('user')
    else:
        event['session']['user']['user_id'] = 'not-allowlisted'
    monkeypatch.setattr('shared_chess.runtime.services', lambda: pytest.fail('Must not open YDB'))
    monkeypatch.setattr('alice_serverless.handler', lambda event, context: {'legacy': True})
    assert shared_alice_serverless.handler(event, context) == {'legacy': True}


def test_native_removed_tester_with_game_ref_fails_closed(native, monkeypatch):
    event, context, _, _, _ = native
    event['state']['user'] = {'game_ref': {'game_id': 'existing', 'revision': 2}}
    monkeypatch.setenv('SHARED_DIALOGS_ALLOWED_OWNER', 'another-tester')
    monkeypatch.setattr('alice_serverless.handler', lambda *_: pytest.fail('Must not fall back'))
    reply = shared_alice_serverless.handler(event, context)
    assert reply['user_state_update'] == event['state']['user']
    assert not reply['response']['end_session']


def test_native_tester_code_does_not_enroll_or_read_storage(native, monkeypatch):
    event, context, owner, _, _ = native
    monkeypatch.delenv('SHARED_DIALOGS_ALLOWED_OWNER')
    monkeypatch.setattr('shared_chess.runtime.services', lambda: pytest.fail('Must not open YDB'))
    event['request']['command'] = 'код тестера'
    reply = shared_alice_serverless.handler(event, context)
    assert owner in reply['response']['text']
    assert 'test-account' not in reply['response']['text']
    assert reply['user_state_update'] == {}


def test_native_alice_pairs_device_and_replays_exactly(native):
    event, context, owner, service, auth = native
    pair = auth.create_pairing('test-ip')
    event['request']['command'] = 'подключить экран ' + pair['code']
    confirmation = shared_alice_serverless.handler(event, context)
    event['state']['session'] = confirmation['session_state']
    event['session']['message_id'] = 1
    event['request']['command'] = 'да'
    shared_alice_serverless.handler(event, context)
    assert auth.authenticate(pair['device_token'])['owner'] == owner
    service.execute(
        owner,
        'new',
        {
            'request_id': '00000000-0000-0000-0000-000000000001',
            'game_id': None,
            'expected_revision': None,
            'type': 'new_game',
            'payload': {},
        },
    )
    event['session']['message_id'] = 2
    event['state']['session'] = {}
    event['request']['command'] = 'e2e4'
    reply = shared_alice_serverless.handler(event, context)
    assert service.current(owner)['revision'] == 2
    assert reply['user_state_update']['game_ref']['revision'] == 2
    assert shared_alice_serverless.handler(event, context)['response'] == reply['response']
    event['session']['message_id'] = 3
    event['request']['command'] = 'повтори'
    event['state']['user'] = reply['user_state_update']
    event['state']['session'] = reply['session_state']
    assert shared_alice_serverless.handler(event, context)['response'] == reply['response']


def test_native_position_queries_preserve_revision_and_exact_replay(native):
    event, context, owner, service, _ = native
    event['state']['user'] = {
        'game_state': {
            'board_state': '3nk3/8/8/8/8/8/8/1N2K3 b - - 0 1',
            'user_color': 'BLACK',
            'skill_state': 'WAITING_MOVE',
        }
    }
    event['request']['command'] = 'назови позицию'
    reply = shared_alice_serverless.handler(event, context)
    assert 'конь d8' in reply['response']['text']
    assert 'конь дэ 8' in reply['response']['tts']
    ref = reply['user_state_update']['game_ref']
    event['state'] = {'user': reply['user_state_update'], 'session': reply['session_state']}
    event['session']['message_id'] += 1
    event['request']['command'] = 'повтори'
    assert shared_alice_serverless.handler(event, context)['response'] == reply['response']
    event['session']['message_id'] += 1
    event['request']['command'] = 'где мои кони?'
    knights = shared_alice_serverless.handler(event, context)
    assert knights['response']['text'] == 'Ваш конь на d8.'
    assert knights['user_state_update']['game_ref'] == ref
    assert service.current(owner)['revision'] == ref['revision']
