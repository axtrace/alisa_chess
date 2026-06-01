# Roadmap: Оптимизация производительности

## Обзор

Два крупных проекта для улучшения производительности `alisa_chess`:

1. **Кэш позиций в Redis** (ADR-0004) — ускорение повторных позиций в 50–100x раз
2. **Stockfish микросервис** (ADR-0005) — исключение холодного старта, persistent engine

Оба проекта независимы и могут реализовываться параллельно.

---

## Проект 1: Кэш позиций в Redis

### Цель
Ускорить вычисление ходов для повторяющихся позиций через кэширование в Redis.

### Статус
- **Статус:** Proposed (ADR-0004)
- **Приоритет:** Высокий (максимальный ROI)
- **Сложность:** Средняя
- **Сроки:** 2–3 дня

### Задачи

#### Phase 1: Реализация (1–2 дня)
- [ ] Создать модуль `position_cache.py` с классом `PositionCache`
  - [ ] Методы: `get_move()`, `set_move()`, `_make_key()`
  - [ ] Поддержка Redis URL из переменной окружения
  - [ ] Graceful degradation при недоступности Redis
- [ ] Интегрировать `PositionCache` в `Game.comp_move()`
  - [ ] Проверка кэша перед вычислением
  - [ ] Сохранение результата в кэш
- [ ] Добавить инициализацию в `alice_serverless.handler`
- [ ] Добавить метрики: `skill.cache.hit`, `skill.cache.miss`
- [ ] Обновить `requirements.txt`: добавить `redis>=4.5.0`

#### Phase 2: Тестирование (0.5 дня)
- [ ] Написать unit-тесты для `PositionCache` (с mock Redis)
- [ ] Написать интеграционные тесты с реальным Redis (в Docker)
- [ ] Проверить, что все существующие тесты остаются зелёными
- [ ] Профилировать эффективность кэша (hit rate, latency)

#### Phase 3: Развёртывание (0.5 дня)
- [ ] Развернуть Redis инстанс в Yandex Cloud
- [ ] Настроить переменные окружения в Cloud Function
- [ ] Развернуть в staging и профилировать
- [ ] Настроить мониторинг: размер Redis, hit rate, latency
- [ ] Развернуть в production

### Зависимости
- Redis инстанс (Yandex Cloud или self-hosted)
- Библиотека `redis` в Python

### Риски
- Redis недоступен → функция работает без кэша (graceful degradation)
- Кэш содержит устаревшие ходы при обновлении Stockfish → решение: инвалидация через TTL или явный flush

### Метрики успеха
- Hit rate кэша > 30% в production
- Ускорение повторных позиций в 50x+ раз
- Нулевое влияние на latency при miss (fallback на engine)

---

## Проект 2: Stockfish микросервис

### Цель
Развернуть Stockfish как отдельный persistent сервис, исключить холодный старт, оставить локальный engine как fallback.

### Статус
- **Статус:** Proposed (ADR-0005)
- **Приоритет:** Средний (реализовать после кэша)
- **Сложность:** Высокая
- **Сроки:** 1–2 недели

### Задачи

#### Phase 1: Проектирование (1 день)
- [ ] Выбрать язык для микросервиса (Go рекомендуется)
- [ ] Спроектировать gRPC API (`service.proto`)
  - [ ] `BestMove(fen, skill_level, time_limit)`
  - [ ] `Evaluate(fen)`
  - [ ] `Health()`
- [ ] Спроектировать архитектуру микросервиса
  - [ ] Инициализация Stockfish один раз
  - [ ] Обработка параллельных запросов
  - [ ] Graceful shutdown

#### Phase 2: Реализация микросервиса (3–5 дней)
- [ ] Создать репозиторий `stockfish-service`
- [ ] Реализовать gRPC сервис
  - [ ] Обёртка UCI для Stockfish
  - [ ] Обработчик `BestMove`
  - [ ] Обработчик `Health`
- [ ] Написать Dockerfile
- [ ] Написать unit-тесты
- [ ] Написать интеграционные тесты

#### Phase 3: Интеграция в Cloud Function (2–3 дня)
- [ ] Создать модуль `engine_client.py` с классом `EngineClient`
  - [ ] Подключение к gRPC сервису
  - [ ] Fallback на локальный engine
  - [ ] Timeout обработка
  - [ ] Метрики: `skill.engine.remote`, `skill.engine.local_fallback`
- [ ] Интегрировать `EngineClient` в `Game.comp_move()`
- [ ] Обновить `alice_serverless.handler` для инициализации клиента
- [ ] Обновить `requirements.txt`: добавить `grpcio>=1.50.0`

#### Phase 4: Тестирование (2 дня)
- [ ] Написать unit-тесты для `EngineClient` (с mock gRPC)
- [ ] Написать интеграционные тесты (микросервис + функция)
- [ ] Проверить fallback логику (отключить сервис, проверить работу)
- [ ] Профилировать latency (сетевая задержка, timeout)
- [ ] Проверить, что все существующие тесты остаются зелёными

#### Phase 5: Развёртывание (2–3 дня)
- [ ] Развернуть микросервис в staging (Compute Instance или K8s)
- [ ] Настроить переменные окружения в Cloud Function
- [ ] Профилировать в staging (задержка, надёжность, fallback rate)
- [ ] Настроить мониторинг микросервиса
  - [ ] Health check
  - [ ] Latency
  - [ ] Error rate
  - [ ] Memory usage
- [ ] Развернуть в production с постепенным rollout (10% → 50% → 100%)

### Зависимости
- Отдельный микросервис (Go/Python)
- Compute Instance или Kubernetes в Yandex Cloud
- gRPC библиотеки в Python

### Риски
- Микросервис упадёт → fallback на локальный engine (graceful degradation)
- Сетевая задержка > timeout → fallback на локальный engine
- Несинхронизированные версии Stockfish → решение: версионирование в gRPC API

### Метрики успеха
- Исключение холодного старта Stockfish (~50–150 ms экономия)
- Fallback rate < 1% в production (надёжность сервиса)
- Сетевая задержка < 100 ms (приемлемо)
- Ускорение на 2–3x в warm container

---

## График реализации

```
Неделя 1:
  ├─ Пн–Вт: Кэш Redis (Phase 1–2)
  ├─ Ср–Пт: Кэш Redis (Phase 3) + Stockfish микросервис (Phase 1)

Неделя 2:
  ├─ Пн–Ср: Stockfish микросервис (Phase 2)
  ├─ Чт–Пт: Stockfish микросервис (Phase 3)

Неделя 3:
  ├─ Пн–Ср: Stockfish микросервис (Phase 4–5)
  ├─ Чт–Пт: Профилирование, мониторинг, production rollout
```

---

## Параллельная реализация

Оба проекта можно реализовывать параллельно:

- **Разработчик 1:** Кэш Redis (Phase 1–3)
- **Разработчик 2:** Stockfish микросервис (Phase 1–5)

Интеграция в `Game` и `alice_serverless` может быть скоординирована на Phase 3.

---

## Критерии приёмки

### Кэш Redis
- [ ] Все тесты зелёные (49/49 passed)
- [ ] Hit rate > 30% в staging
- [ ] Нулевое влияние на latency при miss
- [ ] Graceful degradation при недоступности Redis
- [ ] Метрики `skill.cache.hit` / `skill.cache.miss` работают

### Stockfish микросервис
- [ ] Все тесты зелёные (49/49 passed)
- [ ] Fallback rate < 1% в staging
- [ ] Сетевая задержка < 100 ms
- [ ] Graceful degradation при недоступности сервиса
- [ ] Метрики `skill.engine.remote` / `skill.engine.local_fallback` работают
- [ ] Мониторинг микросервиса настроен (health, latency, memory)

---

## Документация

- [ADR-0004: Кэш позиций в Redis](adr/0004-position-cache-redis.md)
- [ADR-0005: Stockfish микросервис](adr/0005-stockfish-microservice.md)

---

## Контакты и вопросы

При возникновении вопросов или блокеров:
1. Обновить соответствующий ADR с новой информацией
2. Создать issue в репозитории
3. Обсудить в команде
