"""Административный smoke test. Используется только закрытой IAM-версией функции."""

import platform
import time
import uuid

from shared_chess.replies import resolve_reply
from shared_chess.runtime import services
from shared_chess.service import ServiceError


def handler(event, context):
    started = time.perf_counter()
    repository, service, auth = services()
    initialized = time.perf_counter()
    owner = 'cloud-check-' + str(uuid.uuid4())
    new = {
        'request_id': str(uuid.uuid4()),
        'game_id': None,
        'expected_revision': None,
        'type': 'new_game',
        'payload': {'user_color': 'WHITE', 'skill_level': 1},
    }
    created = service.execute(owner, 'new', new)
    snapshot = created['snapshot']
    assert len(snapshot['legal_moves']) == 20
    move = {
        'request_id': str(uuid.uuid4()),
        'game_id': snapshot['game_id'],
        'expected_revision': 1,
        'type': 'move',
        'payload': {'uci': 'e2e4'},
    }
    reply_context = {'skill_id': 'cloud-check', 'session_id': owner, 'message_id': 0}
    before_move = time.perf_counter()
    result = service.execute(owner, 'move', move, reply_context)
    after_move = time.perf_counter()
    assert result['code'] == 'OK', result['code']
    assert result['snapshot']['revision'] == 2
    assert len(result['snapshot']['history_san']) == 2
    assert service.execute(owner, 'move', move, reply_context) == result
    replay = resolve_reply(repository, owner, reply_context, result['alice_reply']['reference'])
    assert replay == result['alice_reply']['response']
    assert service.current(owner + '-other')['game_id'] is None
    stale = {**move, 'request_id': str(uuid.uuid4()), 'payload': {'uci': 'd2d4'}}
    try:
        service.execute(owner, 'stale', stale)
    except ServiceError as error:
        assert error.code == 'STALE_REVISION'
    else:
        raise AssertionError('Stale revision was accepted')
    undo = {**move, 'request_id': str(uuid.uuid4()), 'expected_revision': 2, 'type': 'undo', 'payload': {}}
    restored = service.execute(owner, 'undo', undo)
    assert restored['snapshot']['fen'] == snapshot['fen']
    pair = auth.create_pairing(owner)
    auth.confirm_pairing(owner, pair['code'])
    assert auth.authenticate(pair['device_token'])['owner'] == owner
    auth.revoke(pair['device_token'])
    try:
        auth.authenticate(pair['device_token'])
    except ServiceError as error:
        assert error.code == 'UNAUTHORIZED'
    else:
        raise AssertionError('Revoked token was accepted')
    return {
        'ok': True,
        'python': platform.python_version(),
        'function_id': getattr(context, 'function_name', None),
        'checks': [
            'initial_legal_moves',
            'stockfish_reply',
            'idempotency',
            'exact_reply',
            'owner_isolation',
            'stale_revision',
            'undo',
            'pairing_and_revoke',
        ],
        'storage': 'YDB',
        'history_san': result['snapshot']['history_san'],
        'driver_init_ms': round((initialized - started) * 1000, 1),
        'move_engine_and_storage_ms': round((after_move - before_move) * 1000, 1),
        'total_ms': round((time.perf_counter() - started) * 1000, 1),
    }
