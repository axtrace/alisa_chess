"""HTTP API для API Gateway и локального сервера. Никогда не логирует bearer/body."""

import json
import logging
import uuid

from pydantic import ValidationError

from shared_chess.alice import SharedAlice
from shared_chess.service import ServiceError

logger = logging.getLogger(__name__)


class ChessApi:
    def __init__(self, service, auth):
        self.service, self.auth = service, auth

    def dispatch(self, method, path, body, authorization='', client_key='unknown'):
        try:
            if not isinstance(body, dict):
                raise ServiceError('INVALID_REQUEST', 'Ожидается JSON-объект.', 400)
            token = authorization[7:] if authorization.startswith('Bearer ') else ''
            if method == 'POST' and path == '/v1/pairings':
                return 201, self.auth.create_pairing(client_key)
            if method == 'POST' and path == '/v1/pairings/status':
                return 200, self.auth.pairing_status(body['pairing_id'], body['poll_secret'])
            if method == 'POST' and path == '/v1/skill':
                session = self.auth.authenticate(token, 'skill')
                return 200, SharedAlice(self.service, self.auth).handle(body, session['owner'])
            session = self.auth.authenticate(token)
            owner, device = session['owner'], session['device_id']
            if method == 'GET' and path == '/v1/games/current':
                return 200, self.service.current(owner)
            if method == 'POST' and path == '/v1/device-session/revoke':
                self.auth.revoke(token)
                return 200, {'status': 'REVOKED'}
            if method == 'POST' and path == '/v1/commands':
                request_id = str(uuid.UUID(body['request_id']))
                result = self.service.execute(owner, f'{device}:{request_id}', body)
                return (202 if result['status'] == 'RUNNING' else 200), result
            if method == 'GET' and path.startswith('/v1/commands/'):
                request_id = str(uuid.UUID(path.rsplit('/', 1)[1]))
                result = self.service.result(owner, f'{device}:{request_id}')
                status = 404 if result['status'] == 'NOT_FOUND' else 202 if result['status'] == 'RUNNING' else 200
                return status, result
            return 404, {'code': 'NOT_FOUND', 'message': 'Маршрут не найден.'}
        except ServiceError as error:
            return error.status, {'code': error.code, 'message': error.message}
        except (ValidationError, KeyError, ValueError, TypeError):
            return 400, {'code': 'INVALID_REQUEST', 'message': 'Проверьте параметры запроса.'}
        except Exception as error:
            logger.error('Storage/API failure: %s', type(error).__name__)
            return 503, {
                'code': 'STORAGE_UNAVAILABLE',
                'message': 'Сервис временно недоступен. Повторите тот же запрос.',
            }


def cloud_handler(event, context):
    import base64

    from shared_chess.runtime import services

    try:
        _, service, auth = services()
        headers = {k.lower(): v for k, v in event.get('headers', {}).items()}
        raw = event.get('body') or ''
        if event.get('isBase64Encoded'):
            raw = base64.b64decode(raw, validate=True).decode()
        if len(raw.encode()) > 16384:
            raise ValueError('body too large')
        status, data = ChessApi(service, auth).dispatch(
            event.get('httpMethod', ''),
            event.get('path', ''),
            json.loads(raw or '{}'),
            headers.get('authorization', ''),
            event.get('requestContext', {}).get('identity', {}).get('sourceIp', 'gateway'),
        )
    except (ValueError, TypeError):
        status, data = 400, {'code': 'INVALID_REQUEST', 'message': 'Некорректный запрос.'}
    except Exception:
        status, data = 503, {'code': 'STORAGE_UNAVAILABLE', 'message': 'Сервис временно недоступен.'}
    return {
        'statusCode': status,
        'headers': {'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store'},
        'body': json.dumps(data, ensure_ascii=False),
        'isBase64Encoded': False,
    }
