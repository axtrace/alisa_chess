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
@pytest.mark.parametrize('anonymous', [False, True])
def test_native_rejects_untrusted_transport(native, monkeypatch, change, anonymous):
    event, context, _, _, _ = native
    if anonymous:
        event['session'].pop('user')
        event['session']['application'] = {'application_id': 'test-app'}
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
    field = 'application_state' if anonymous else 'user_state_update'
    assert reply[field] == {}
    assert 'недоступна' in reply['response']['text']
    assert not reply['response']['end_session']


@pytest.mark.parametrize('anonymous', [False, True])
def test_native_non_tester_keeps_legacy_without_ydb(native, monkeypatch, anonymous):
    event, context, _, _, _ = native
    if anonymous:
        event['session'].pop('user')
        event['session']['application'] = {'application_id': 'test-account'}
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


@pytest.mark.parametrize('anonymous', [False, True])
def test_native_alice_pairs_device_and_replays_exactly(native, monkeypatch, anonymous):
    event, context, owner, service, auth = native
    if anonymous:
        event['session'].pop('user')
        event['session']['application'] = {'application_id': 'test-app'}
        owner = dialogs_owner(event, context)
        monkeypatch.setenv('SHARED_DIALOGS_ALLOWED_APPLICATION_OWNER', owner)
    scope, output = ('application', 'application_state') if anonymous else ('user', 'user_state_update')
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
    assert reply[output]['game_ref']['revision'] == 2
    assert shared_alice_serverless.handler(event, context)['response'] == reply['response']
    event['session']['message_id'] = 3
    event['request']['command'] = 'повтори'
    event['state'][scope] = reply[output]
    event['state']['session'] = reply['session_state']
    assert shared_alice_serverless.handler(event, context)['response'] == reply['response']
    event['session'].update(session_id='new-session', message_id=0, new=True)
    event['state'] = {}
    event['request']['command'] = ''
    resumed = shared_alice_serverless.handler(event, context)
    assert resumed[output]['game_ref'] == reply[output]['game_ref']
    assert resumed[output]['game_state']['board_state'] == service.current(owner)['fen']


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


def test_anonymous_identity_and_game_are_isolated(native, monkeypatch):
    event, context, account_owner, service, _ = native
    event['session'].pop('user')
    event['session']['application'] = {'application_id': 'test-account'}
    event['session']['user_id'] = 'forged-legacy-id'
    owner = dialogs_owner(event, context)
    assert owner.startswith('dialogs-application:') and owner != account_owner
    monkeypatch.setenv('SHARED_DIALOGS_ALLOWED_APPLICATION_OWNER', owner)
    event['request']['command'] = ''
    reply = shared_alice_serverless.handler(event, context)
    assert reply['application_state']['game_state']['skill_state'] == 'WAITING_CONFIRM'
    assert 'user_state_update' not in reply
    event['request']['command'] = 'да'
    event['session']['message_id'] = 1
    event['state'] = {'application': reply['application_state'], 'session': reply['session_state']}
    reply = shared_alice_serverless.handler(event, context)
    assert reply['application_state']['game_state']['skill_state'] == 'WAITING_COLOR'

    # YDB восстанавливает разговор того же приложения даже без контекста Диалогов.
    event['session'].update(session_id='another-session', message_id=0, new=True)
    event['state'] = {}
    event['request']['command'] = ''
    restored = shared_alice_serverless.handler(event, context)
    assert restored['application_state'] == reply['application_state']
    assert service.voice_snapshot(account_owner)['game_state'] == {}

    event['session']['application']['application_id'] = 'another-app'
    other = dialogs_owner(event, context)
    assert other != owner
    monkeypatch.setenv('SHARED_DIALOGS_ALLOWED_APPLICATION_OWNER', other)
    separate = shared_alice_serverless.handler(event, context)
    assert separate['application_state']['game_state']['skill_state'] == 'WAITING_CONFIRM'
    monkeypatch.setenv('SHARED_DIALOGS_SKILL_ID', 'other-skill')
    event['session']['skill_id'] = 'other-skill'
    assert dialogs_owner(event, context) not in (owner, other, account_owner)


def test_anonymous_migrated_game_fails_closed_and_repeats_outage(native, monkeypatch):
    event, context, _, _, _ = native
    event['session'].pop('user')
    event['session']['application'] = {'application_id': 'test-app'}
    owner = dialogs_owner(event, context)
    event['state']['application'] = {'game_ref': {'game_id': 'existing', 'revision': 2}}
    monkeypatch.setattr('alice_serverless.handler', lambda *_: pytest.fail('Must not fall back'))
    monkeypatch.setattr('shared_chess.runtime.services', lambda: (_ for _ in ()).throw(OSError('offline')))
    # Нет допуска — отказ. С допуском, но без YDB — тот же безопасный ответ.
    denied = shared_alice_serverless.handler(event, context)
    monkeypatch.setenv('SHARED_DIALOGS_ALLOWED_APPLICATION_OWNER', owner)
    failed = shared_alice_serverless.handler(event, context)
    assert failed == denied
    assert failed['application_state'] == event['state']['application']
    assert 'user_state_update' not in failed
    assert not failed['response']['end_session']
    event['state']['session'] = failed['session_state']
    event['session']['message_id'] += 1
    event['request']['command'] = 'повтори'
    assert shared_alice_serverless.handler(event, context)['response'] == failed['response']


@pytest.mark.parametrize('identity', ['', 42, 'a' * 129])
def test_anonymous_rejects_invalid_application_identity(native, identity):
    event, context, _, _, _ = native
    event['session'].pop('user')
    event['session']['application'] = {'application_id': identity}
    with pytest.raises(ValueError, match='application identity'):
        dialogs_owner(event, context)


def test_legacy_user_id_does_not_identify_an_account_or_application(native):
    event, context, _, _, _ = native
    event['session'].pop('user')
    event['session']['user_id'] = 'test-account'
    assert dialogs_owner(event, context) is None
