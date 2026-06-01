# ADR-0004: Кэш позиций в Redis

- **Статус:** Proposed
- **Дата:** 2025-06-01
- **Авторы:** alisa_chess team

## Контекст

Каждый запрос с ходом пользователя требует вычисления хода компьютера через Stockfish. Даже в одной сессии позиции могут повторяться (ошибка пользователя, отмена хода, анализ вариантов). Между разными пользователями повторяемость позиций ещё выше.

Текущее решение:
- Каждый запрос → `Game.comp_move()` → `engine.best_move()` → вычисление с нуля
- Время вычисления: 50–500 ms в зависимости от `skill_level` и позиции

**Проблема:** Ресурсы тратятся впустую на пересчёт одних и тех же позиций.

## Решение

Добавить слой кэширования позиций в Redis:

```
Запрос с ходом пользователя
    ↓
Game.comp_move()
    ↓
PositionCache.get_move(fen, skill_level)
    ├─ Если в Redis → вернуть кэшированный ход (instant)
    └─ Если нет → вычислить через engine.best_move()
                  → сохранить в Redis (TTL 24h)
                  → вернуть ход
```

### Архитектура

**Новый модуль:** `position_cache.py`

```python
class PositionCache:
    """Кэш ходов компьютера по позиции (FEN) и уровню сложности."""

    def __init__(self, redis_url: str = 'redis://localhost:6379/0'):
        self.redis = redis.from_url(redis_url)
        self.ttl = 86400  # 24 часа

    def get_move(self, fen: str, skill_level: int) -> str | None:
        """Получить кэшированный ход или None."""
        key = self._make_key(fen, skill_level)
        return self.redis.get(key)

    def set_move(self, fen: str, skill_level: int, move: str) -> None:
        """Сохранить ход в кэш."""
        key = self._make_key(fen, skill_level)
        self.redis.setex(key, self.ttl, move)

    def _make_key(self, fen: str, skill_level: int) -> str:
        """Генерировать ключ Redis."""
        return f"chess:move:{skill_level}:{hashlib.sha256(fen.encode()).hexdigest()}"
```

**Интеграция в `Game`:**

```python
class Game:
    def __init__(self, skill_level: int = 1, ..., cache: PositionCache | None = None):
        self.cache = cache
        ...

    def comp_move(self) -> str:
        """Ход компьютера с кэшированием."""
        if self.cache:
            cached = self.cache.get_move(self.board.fen(), self.skill_level)
            if cached:
                logger.info(f'Cache hit: {cached}')
                emit_counter('skill.cache.hit', tags={'skill_level': str(self.skill_level)})
                return cached

        # Вычисляем ход
        move = self.engine.best_move(...)

        # Сохраняем в кэш
        if self.cache:
            self.cache.set_move(self.board.fen(), self.skill_level, str(move))
            emit_counter('skill.cache.miss', tags={'skill_level': str(self.skill_level)})

        return str(move)
```

**Инициализация в `alice_serverless`:**

```python
from position_cache import PositionCache

cache = PositionCache(redis_url=os.getenv('REDIS_URL', 'redis://localhost:6379/0'))

def handler(event, context):
    ...
    with AliceChess(cache=cache) as alice:
        response = alice.handle_request(event)
    ...
```

### Конфигурация

**Переменные окружения:**
- `REDIS_URL` — URL подключения к Redis (по умолчанию `redis://localhost:6379/0`)
- `CACHE_TTL` — время жизни записи в секундах (по умолчанию 86400 = 24h)
- `CACHE_ENABLED` — включить/отключить кэш (по умолчанию `true`)

**Зависимости:**
- Добавить в `requirements.txt`: `redis>=4.5.0`

### Инвалидация кэша

Кэш автоматически инвалидируется через TTL (24 часа). Ручная инвалидация:

```python
# При изменении версии Stockfish
cache.redis.flushdb()

# При изменении параметров движка
cache.redis.delete(f"chess:move:{skill_level}:*")
```

## Последствия

**Плюсы:**
- Ускорение повторных позиций в 50–100x раз
- Работает между сессиями разных пользователей
- Не требует изменения жизненного цикла Stockfish
- Graceful degradation: если Redis недоступен, функция работает без кэша
- Метрики: `skill.cache.hit` / `skill.cache.miss` для мониторинга эффективности

**Минусы:**
- Добавляет зависимость Redis (требует инстанса в Yandex Cloud)
- Сетевая задержка на обращение к Redis (~5–10 ms)
- Требует обработки ошибок подключения
- Кэш может содержать устаревшие ходы при обновлении Stockfish

**Компромиссы:**
- Кэш не учитывает историю партии (только текущую позицию). Это допустимо, так как ход компьютера зависит только от позиции и `skill_level`.
- TTL 24 часа — компромисс между свежестью и экономией памяти Redis.

## Инварианты, которые нельзя нарушать

- Кэш — опциональный слой. Функция должна работать без Redis.
- Ключ кэша должен включать `skill_level` (разные уровни → разные ходы).
- При ошибке Redis не должна падать функция — логировать и продолжить без кэша.
- Тесты должны работать с mock Redis или без кэша вообще.

## Связанные документы

- [ADR-0002: Жизненный цикл Stockfish](0002-stockfish-lifecycle.md)
- [`AGENTS.md`](../../AGENTS.md) — инварианты для агентов
- [`metrics.py`](../../metrics.py) — система метрик

## Следующие шаги

1. Реализовать `PositionCache` с mock Redis для тестов
2. Интегрировать в `Game.comp_move()`
3. Добавить метрики `skill.cache.hit` / `skill.cache.miss`
4. Профилировать эффективность кэша в staging
5. Развернуть Redis инстанс в Yandex Cloud
6. Мониторить размер Redis и настроить eviction policy
