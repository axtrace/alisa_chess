"""Одноразовая привязка и отзыв сессии; в БД находятся только хеши секретов."""

import hashlib
import secrets
import time

from shared_chess.service import ServiceError


def secret_hash(value):
    return hashlib.sha256(value.encode()).hexdigest()


class DeviceAuth:
    def __init__(self, repository, clock=time.time):
        self.repository, self.clock = repository, clock

    def authenticate(self, token, kind='device'):
        if not token or len(token) > 512:
            raise ServiceError('UNAUTHORIZED', 'Подключите приложение к партии.', 401)
        saved = self.repository.atomic(lambda tx: tx.get('device_sessions', 'auth', secret_hash(token)))
        if not saved or saved.get('revoked') or saved['expires'] <= self.clock() or saved['kind'] != kind:
            raise ServiceError('UNAUTHORIZED', 'Привязка истекла или отозвана. Подключите приложение снова.', 401)
        return saved

    def seed_test_session(self, owner, token, kind='skill'):
        """Только явная локальная/административная настройка, не публичный маршрут."""
        if len(token) < 32:
            raise ValueError('Нужен случайный токен длиной не менее 32 символов')
        self.repository.atomic(
            lambda tx: tx.put(
                'device_sessions',
                'auth',
                secret_hash(token),
                {
                    'owner': owner,
                    'device_id': secret_hash(token)[:24],
                    'kind': kind,
                    'expires': self.clock() + 30 * 86400,
                    'revoked': False,
                },
            )
        )

    def create_pairing(self, client_key):
        code = f'{secrets.randbelow(1000000):06d}'
        token, poll_secret = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        pairing_id = secrets.token_urlsafe(24)

        def create(tx):
            now = self.clock()
            # Client key comes from the transport, never from the JSON body.
            rate_key = 'rate:' + secret_hash(client_key)
            rate = tx.get('pairings', 'auth', rate_key) or {'start': now, 'count': 0}
            if now - rate['start'] >= 300:
                rate = {'start': now, 'count': 0}
            if rate['count'] >= 5:
                raise ServiceError('RATE_LIMITED', 'Слишком много попыток. Подождите пять минут.', 429)
            existing = tx.get('pairings', 'codes', secret_hash(code))
            if existing and existing['expires'] > now:
                raise ServiceError('CODE_COLLISION', 'Повторите создание кода.', 409)
            rate['count'] += 1
            tx.put('pairings', 'auth', rate_key, rate)
            item = {
                'id': pairing_id,
                'code_hash': secret_hash(code),
                'poll_hash': secret_hash(poll_secret),
                'token_hash': secret_hash(token),
                'expires': now + 300,
                'owner': None,
            }
            tx.put('pairings', 'auth', pairing_id, item)
            tx.put('pairings', 'codes', secret_hash(code), {'id': pairing_id, 'expires': item['expires']})

        self.repository.atomic(create)
        return {
            'pairing_id': pairing_id,
            'code': code,
            'poll_secret': poll_secret,
            'device_token': token,
            'expires_in': 300,
        }

    def pairing_status(self, pairing_id, poll_secret):
        item = self.repository.atomic(lambda tx: tx.get('pairings', 'auth', pairing_id))
        if not item or not secrets.compare_digest(item['poll_hash'], secret_hash(poll_secret)):
            raise ServiceError('UNAUTHORIZED', 'Не удалось проверить привязку.', 401)
        if item['owner']:
            return {'status': 'CONFIRMED'}
        return {'status': 'EXPIRED' if item['expires'] <= self.clock() else 'WAITING'}

    def confirm_pairing(self, owner, code):
        def confirm(tx):
            now = self.clock()
            rate = tx.get('pairings', owner, 'attempts') or {'start': now, 'count': 0}
            if now - rate['start'] >= 300:
                rate = {'start': now, 'count': 0}
            if rate['count'] >= 5:
                return 'RATE_LIMITED'
            entry = tx.get('pairings', 'codes', secret_hash(code))
            item = tx.get('pairings', 'auth', entry['id']) if entry else None
            if not item or item['expires'] <= now:
                rate['count'] += 1
                tx.put('pairings', owner, 'attempts', rate)
                return 'INVALID_CODE'
            if item['owner'] and item['owner'] != owner:
                return 'INVALID_CODE'
            if not item['owner']:
                item['owner'] = owner
                tx.put('pairings', 'auth', item['id'], item)
                tx.put(
                    'device_sessions',
                    'auth',
                    item['token_hash'],
                    {
                        'owner': owner,
                        'device_id': item['id'],
                        'kind': 'device',
                        'expires': now + 30 * 86400,
                        'revoked': False,
                    },
                )
            return 'OK'

        result = self.repository.atomic(confirm)
        if result != 'OK':
            raise ServiceError(
                result,
                'Код не принят. Проверьте код или подождите пять минут.',
                429 if result == 'RATE_LIMITED' else 400,
            )

    def revoke(self, token):
        def revoke(tx):
            item = tx.get('device_sessions', 'auth', secret_hash(token))
            if item:
                item['revoked'] = True
                tx.put('device_sessions', 'auth', secret_hash(token), item)

        self.repository.atomic(revoke)
