import copy
import json
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import chess
import pytest

from shared_chess.alice import SharedAlice
from shared_chess.api import ChessApi
from shared_chess.auth import DeviceAuth
from shared_chess.repository import SQLiteRepository, encode
from shared_chess.service import GameService, ServiceError
from shared_chess.state import SharedGameState


@pytest.mark.parametrize(('body', 'encoded'), [(None, True), ('', True), ('e30=', True), ('', False)])
def test_cloud_gateway_empty_get_body(core, monkeypatch, body, encoded):
    from shared_chess.api import cloud_handler

    repo, service, auth, _ = core
    token = 'test-device-token-' + 'x' * 32
    auth.seed_test_session('owner', token, kind='device')
    monkeypatch.setattr('shared_chess.runtime.services', lambda: (repo, service, auth))
    result = cloud_handler(
        {
            'httpMethod': 'GET',
            'path': '/v1/games/current',
            'headers': {'Authorization': 'Bearer ' + token},
            'body': body,
            'isBase64Encoded': encoded,
        },
        None,
    )
    assert result['statusCode'] == 200
    assert json.loads(result['body'])['game_id'] is None


def test_cloud_gateway_rejects_invalid_base64(core, monkeypatch):
    from shared_chess.api import cloud_handler

    repo, service, auth, _ = core
    monkeypatch.setattr('shared_chess.runtime.services', lambda: (repo, service, auth))
    result = cloud_handler({'httpMethod': 'POST', 'path': '/v1/pairings', 'body': '{}', 'isBase64Encoded': True}, None)
    assert result['statusCode'] == 400


@pytest.fixture
def core(tmp_path):
    repo = SQLiteRepository(tmp_path / 'test.sqlite')
    calls = []

    def engine(board, level):
        calls.append(board.fen())
        return next(iter(board.legal_moves))

    service = GameService(repo, engine=engine)
    return repo, service, DeviceAuth(repo), calls


def command(service, kind, payload=None, snapshot=None, request_id=None):
    snapshot = snapshot or service.current('owner')
    return {
        'request_id': request_id or str(uuid.uuid4()),
        'game_id': snapshot['game_id'],
        'expected_revision': snapshot['revision'],
        'type': kind,
        'payload': payload or {},
    }


def start(service, **payload):
    return service.execute('owner', 'new', command(service, 'new_game', payload))['snapshot']


def test_move_repeat_and_undo_are_one_command(core):
    repo, service, _, calls = core
    before = start(service)
    move = command(service, 'move', {'uci': 'e2e4'}, before)
    result = service.execute('owner', 'move', move)
    assert result['code'] == 'OK'
    assert result['snapshot']['revision'] == 2
    assert service.execute('owner', 'move', move) == result
    assert len(calls) == 1
    undo = command(service, 'undo')
    undone = service.execute('owner', 'undo', undo)
    assert undone['snapshot']['fen'] == chess.STARTING_FEN
    assert service.execute('owner', 'undo', undo) == undone
    with pytest.raises(ServiceError, match='номер запроса'):
        service.execute('owner', 'move', {**move, 'payload': {'uci': 'd2d4'}})


def test_two_clients_and_engine_outside_transaction(core):
    repo, service, _, calls = core
    start(service)
    entered, release = threading.Event(), threading.Event()

    def slow(board, level):
        # A different connection can reserve/read while the engine is running.
        assert service.current('owner')['busy']
        entered.set()
        assert release.wait(3)
        return next(iter(board.legal_moves))

    service.engine = slow
    first = command(service, 'move', {'uci': 'e2e4'})
    second = command(service, 'move', {'uci': 'd2d4'})
    with ThreadPoolExecutor() as pool:
        future = pool.submit(service.execute, 'owner', 'a', first)
        assert entered.wait(3)
        assert service.execute('owner', 'a', first)['code'] == 'IN_PROGRESS'
        assert service.execute('owner', 'b', second)['code'] == 'GAME_BUSY'
        release.set()
        assert future.result()['code'] == 'OK'
    with pytest.raises(ServiceError) as error:
        service.execute('owner', 'b', second)
    assert error.value.code == 'STALE_REVISION'


def test_engine_error_preserves_board_and_is_replayed(core):
    _, service, _, _ = core
    before = start(service)

    def fail(*_):
        raise OSError('engine down')

    service.engine = fail
    cmd = command(service, 'move', {'uci': 'e2e4'})
    result = service.execute('owner', 'move', cmd)
    assert result['code'] == 'ENGINE_ERROR'
    assert service.current('owner')['fen'] == before['fen']
    assert service.current('owner')['revision'] == before['revision']
    assert service.execute('owner', 'move', cmd) == result


def test_new_game_and_late_old_result_keep_current_generation(core):
    _, service, _, _ = core
    start(service)
    old_cmd = command(service, 'move', {'uci': 'e2e4'})
    old_result = service.execute('owner', 'old', old_cmd)
    new = service.execute('owner', 'newer', command(service, 'new_game', {'user_color': 'BLACK'}))
    assert new['snapshot']['active_generation'] == 2
    assert new['snapshot']['user_color'] == 'BLACK'
    assert not new['snapshot']['can_undo']
    assert service.execute('owner', 'old', old_cmd) == old_result
    assert service.current('owner')['game_id'] == new['snapshot']['game_id']


def test_import_once_and_undo_rebases_history(core):
    _, service, _, _ = core
    board = chess.Board()
    board.push_san('e4')
    board.push_san('e5')
    old = {
        'board_state': board.fen(),
        'prev_board_state': chess.STARTING_FEN,
        'user_color': 'WHITE',
        'skill_state': 'WAITING_MOVE',
        'last_move': 'e5',
    }
    imported = service.import_legacy('owner', old)
    assert not imported['history_complete']
    assert service.import_legacy('owner', {**old, 'board_state': chess.STARTING_FEN}) == imported
    undone = service.execute('owner', 'undo', command(service, 'undo'))
    assert undone['snapshot']['fen'] == chess.STARTING_FEN
    assert not undone['snapshot']['can_undo']
    assert service.execute('owner', 'undo2', command(service, 'undo'))['code'] == 'UNDO_UNAVAILABLE'
    again = service.execute('owner', 'move', command(service, 'move', {'uci': 'd2d4'}))
    assert again['code'] == 'OK'


def test_late_worker_cannot_commit_after_lease_is_taken(core):
    repo, service, _, _ = core
    start(service)
    now = [100.0]
    service.clock = lambda: now[0]
    entered, release = threading.Event(), threading.Event()
    calls = [0]

    def engine(board, level):
        calls[0] += 1
        if calls[0] == 1:
            entered.set()
            assert release.wait(3)
            return chess.Move.from_uci('e7e5')
        return chess.Move.from_uci('c7c5')

    service.engine = engine
    cmd = command(service, 'move', {'uci': 'e2e4'})
    with ThreadPoolExecutor() as pool:
        future = pool.submit(service.execute, 'owner', 'move', cmd)
        assert entered.wait(3)
        now[0] += 11
        recovered = service.execute('owner', 'move', cmd)
        release.set()
        assert future.result() == recovered
    assert recovered['snapshot']['history_san'] == ['e4', 'c5']
    assert service.current('owner')['revision'] == 2


def test_auth_pairing_owner_isolation_expiry_and_revoke(core):
    repo, service, auth, _ = core
    pairing = auth.create_pairing('client')
    with pytest.raises(ServiceError):
        auth.authenticate(pairing['device_token'])
    with pytest.raises(ServiceError):
        auth.pairing_status(pairing['pairing_id'], 'wrong')
    auth.confirm_pairing('owner', pairing['code'])
    assert auth.pairing_status(pairing['pairing_id'], pairing['poll_secret'])['status'] == 'CONFIRMED'
    assert auth.authenticate(pairing['device_token'])['owner'] == 'owner'
    with pytest.raises(ServiceError):
        auth.confirm_pairing('attacker', pairing['code'])
    auth.revoke(pairing['device_token'])
    with pytest.raises(ServiceError):
        auth.authenticate(pairing['device_token'])


def test_pairing_rate_limits_and_expiry(core):
    repo, _, _, _ = core
    now = [0.0]
    auth = DeviceAuth(repo, clock=lambda: now[0])
    pairing = auth.create_pairing('ip')
    for _ in range(4):
        auth.create_pairing('ip')
    with pytest.raises(ServiceError) as error:
        auth.create_pairing('ip')
    assert error.value.status == 429
    now[0] = 301
    assert auth.pairing_status(pairing['pairing_id'], pairing['poll_secret'])['status'] == 'EXPIRED'
    with pytest.raises(ServiceError):
        auth.confirm_pairing('owner', pairing['code'])


def test_http_rejects_forged_owner_and_recovers_response(core):
    _, service, auth, _ = core
    auth.seed_test_session('owner', 'a' * 43, kind='device')
    auth.seed_test_session('stranger', 'b' * 43, kind='device')
    api = ChessApi(service, auth)
    assert api.dispatch('GET', '/v1/games/current', {}, '')[0] == 401
    cmd = command(service, 'new_game')
    status, result = api.dispatch('POST', '/v1/commands', cmd, 'Bearer ' + 'a' * 43)
    assert status == 200
    assert api.dispatch('GET', '/v1/commands/' + cmd['request_id'], {}, 'Bearer ' + 'a' * 43)[1] == result
    assert api.dispatch('GET', '/v1/games/current', {}, 'Bearer ' + 'b' * 43)[1]['game_id'] is None
    assert api.dispatch('POST', '/v1/commands', {**cmd, 'owner': 'owner'}, 'Bearer ' + 'b' * 43)[0] == 400


def alice_event(message, text, user=None, state=None):
    return {
        'session': {'skill_id': 'skill', 'session_id': 'dialog', 'message_id': message},
        'request': {'command': text, 'nlu': {'intents': {}}},
        'state': {'user': user or {}, 'session': state or {}},
    }


def test_alice_zero_id_exact_repeat_and_reply_budget(core):
    _, service, auth, calls = core
    start(service)
    alice = SharedAlice(service, auth)
    event = alice_event(0, 'пешка с е два на е четыре')
    response = alice.handle(event, 'owner')
    assert len(calls) == 1
    repeated_event = alice_event(
        0, 'пешка с е два на е четыре', response['user_state_update'], response['session_state']
    )
    assert alice.handle(repeated_event, 'owner')['response'] == response['response']
    repeat = alice.handle(alice_event(1, 'повтори', response['user_state_update'], response['session_state']), 'owner')
    assert repeat['response'] == response['response']
    assert len(calls) == 1
    assert len(encode(response['session_state']).encode()) <= 1024
    assert len(encode(response['user_state_update']).encode()) <= 1024


def test_repeat_of_storage_error_is_inline_and_does_not_need_database(core):
    repo, service, auth, _ = core
    alice = SharedAlice(service, auth)

    def unavailable(_):
        raise OSError('offline')

    repo.atomic = unavailable
    failed = alice.handle(alice_event(0, 'e2e4'), 'owner')
    repeated = alice.handle(alice_event(1, 'повтори', failed['user_state_update'], failed['session_state']), 'owner')
    assert repeated['response'] == failed['response']
    assert not repeated['response']['end_session']


def test_negated_multi_move_and_ambiguous_promotion_rejected(core):
    _, service, _, _ = core
    start(service)
    for number, text in enumerate(['не ходи е2 е4', 'е2 е4 и е7 е5']):
        result = service.execute('owner', str(number), command(service, 'move_text', {'text': text}))
        assert result['code'] != 'OK'
        assert service.current('owner')['revision'] == 1


def test_state_rejects_inconsistent_history():
    with pytest.raises(ValueError):
        SharedGameState(moves_uci=['e2e5'])
    with pytest.raises(ValueError):
        SharedGameState(turn_starts=[1])


def test_alice_lost_state_replays_original_after_new_game(core):
    _, service, auth, calls = core
    start(service)
    alice = SharedAlice(service, auth)
    event = alice_event(0, 'e2e4')
    first = alice.handle(event, 'owner')
    assert alice.handle(event, 'owner')['response'] == first['response']
    assert len(calls) == 1
    service.execute('owner', 'next-game', command(service, 'new_game'))
    replay = alice.handle(event, 'owner')
    assert replay['response'] == first['response']
    assert replay['user_state_update']['game_ref']['game_id'] == service.current('owner')['game_id']
    changed = alice.handle(alice_event(0, 'd2d4'), 'owner')
    assert 'Номер сообщения' in changed['response']['text']


def test_alice_stale_confirmation_cannot_resign_new_position(core):
    _, service, auth, _ = core
    start(service)
    alice = SharedAlice(service, auth)
    confirm = alice.handle(alice_event(0, 'сдаюсь'), 'owner')
    service.execute('owner', 'touch', command(service, 'move', {'uci': 'e2e4'}))
    response = alice.handle(alice_event(1, 'да', confirm['user_state_update'], confirm['session_state']), 'owner')
    assert 'Позиция изменилась' in response['response']['text']
    assert service.current('owner')['status'] == 'playing'


def test_lost_commit_response_is_recovered_without_second_engine(core):
    repo, service, _, calls = core
    start(service)
    atomic = repo.atomic
    count = [0]

    def lost_commit(operation):
        result = atomic(operation)
        count[0] += 1
        if count[0] == 2:
            raise OSError('commit response lost')
        return result

    cmd = command(service, 'move', {'uci': 'e2e4'})
    repo.atomic = lost_commit
    with pytest.raises(OSError):
        service.execute('owner', 'lost-response', cmd)
    repo.atomic = atomic
    recovered = service.execute('owner', 'lost-response', cmd)
    assert recovered['code'] == 'OK'
    assert recovered['snapshot']['revision'] == 2
    assert len(calls) == 1


def test_black_mate_has_no_extra_engine_and_undo_uses_turn_boundaries(core):
    _, service, _, _ = core
    replies = iter(['f2f3', 'g2g4'])
    service.engine = lambda board, level: chess.Move.from_uci(next(replies))
    opening = start(service, user_color='BLACK')
    assert opening['history_san'] == ['f3'] and not opening['can_undo']
    service.execute('owner', 'e5', command(service, 'move', {'uci': 'e7e5'}))
    mate = service.execute('owner', 'mate', command(service, 'move', {'uci': 'd8h4'}))
    assert mate['snapshot']['result'] == '0-1'
    assert mate['snapshot']['status'] == 'finished'
    first = service.execute('owner', 'undo-mate', command(service, 'undo'))
    assert first['snapshot']['history_san'] == ['f3', 'e5', 'g4']
    assert first['snapshot']['status'] == 'playing'
    second = service.execute('owner', 'undo-e5', command(service, 'undo'))
    assert second['snapshot']['history_san'] == ['f3']
    assert not second['snapshot']['can_undo']


def test_promotion_and_castling_are_legal_server_moves(core):
    _, service, _, _ = core
    service.import_legacy(
        'owner', {'board_state': '7k/P7/8/8/8/8/8/7K w - - 0 1', 'user_color': 'WHITE', 'skill_state': 'WAITING_MOVE'}
    )
    assert {m for m in service.current('owner')['legal_moves'] if m.startswith('a7a8')} == {
        'a7a8q',
        'a7a8r',
        'a7a8b',
        'a7a8n',
    }
    result = service.execute('owner', 'promote', command(service, 'move', {'uci': 'a7a8n'}))
    assert result['snapshot']['pieces']['a8'] == 'N'


def test_migrated_game_does_not_fall_back_to_context_without_auth(monkeypatch):
    import shared_alice_serverless

    monkeypatch.setenv('SHARED_GAMES_ENABLED', 'false')
    user = {'game_ref': {'game_id': 'existing', 'revision': 2}, 'game_state': {'board_state': chess.STARTING_FEN}}
    event = alice_event(0, 'e2e4', user)
    monkeypatch.setattr('shared_chess.runtime.services', lambda: (_ for _ in ()).throw(OSError('offline')))
    reply = shared_alice_serverless.handler(event, None)
    assert reply['user_state_update'] == user
    assert not reply['response']['end_session']
    assert reply['session_state']['previous_response']['kind'] == 'inline'
    repeated = shared_alice_serverless.handler(alice_event(1, 'повтори', user, reply['session_state']), None)
    assert repeated['response'] == reply['response']
