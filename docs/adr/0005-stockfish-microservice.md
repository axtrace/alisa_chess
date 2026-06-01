# ADR-0005: Stockfish как отдельный микросервис с fallback

- **Статус:** Proposed
- **Дата:** 2025-06-01
- **Авторы:** alisa_chess team

## Контекст

Текущая архитектура запускает Stockfish в каждом запросе Cloud Function:
- **Холодный старт:** ~50–150 ms на инициализацию процесса
- **Warm container:** Движок поднимается заново, даже если контейнер переиспользуется
- **Ограничения:** Serverless функция платит за время выполнения, включая инициализацию

Проблема усугубляется при высокой нагрузке: каждый запрос платит за холодный старт Stockfish.

## Решение

Развернуть **Stockfish как отдельный микросервис** (persistent, всегда живой) и использовать его через gRPC/HTTP. Оставить локальный Stockfish в функции как **fallback** на случай недоступности сервиса.

### Архитектура

```
┌─────────────────────────────────────────────────────────┐
│ Yandex Cloud Function (alisa_chess)                     │
│                                                         │
│  alice_serverless.handler()                             │
│    ↓                                                    │
│  AliceChess.handle_request()                            │
│    ↓                                                    │
│  Game.comp_move()                                       │
│    ↓                                                    │
│  EngineClient.best_move(fen, skill_level, time_limit)  │
│    ├─ Попытка 1: gRPC → Stockfish Service (5s timeout) │
│    │   ├─ Успех → вернуть ход                          │
│    │   └─ Ошибка → fallback                            │
│    │                                                   │
│    └─ Fallback: локальный engine.best_move()           │
│       (ленивая инициализация, как сейчас)              │
│                                                         │
└─────────────────────────────────────────────────────────┘
         ↓ (gRPC)
┌─────────────────────────────────────────────────────────┐
│ Stockfish Microservice (persistent)                     │
│ (Yandex Compute Instance или Container)                │
│                                                         │
│  gRPC Server                                            │
│    ├─ BestMove(fen, skill_level, time_limit)           │
│    ├─ Evaluate(fen)                                    │
│    └─ Health()                                         │
│                                                         │
│  Stockfish Engine (инициализирован один раз)           │
│  (переиспользуется для всех запросов)                  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Компоненты

#### 1. Stockfish Microservice (новый проект)

**Язык:** Go или Python (рекомендуется Go для производительности)

**Структура:**
```
stockfish-service/
├── main.go
├── engine/
│   ├── engine.go          # Обёртка UCI
│   └── pool.go            # Пул инстансов (опционально)
├── grpc/
│   ├── service.proto      # gRPC определение
│   └── service.go         # Реализация
├── health/
│   └── health.go          # Health check
├── Dockerfile
├── requirements.txt (если Python)
└── README.md
```

**gRPC API (`service.proto`):**
```protobuf
syntax = "proto3";

package stockfish;

service EngineService {
  rpc BestMove(BestMoveRequest) returns (BestMoveResponse);
  rpc Evaluate(EvaluateRequest) returns (EvaluateResponse);
  rpc Health(HealthRequest) returns (HealthResponse);
}

message BestMoveRequest {
  string fen = 1;
  int32 skill_level = 2;
  float time_limit_seconds = 3;
}

message BestMoveResponse {
  string move = 1;  // UCI notation
  int32 score = 2;  // centipawns
  string pv = 3;    // principal variation
}

message EvaluateRequest {
  string fen = 1;
}

message EvaluateResponse {
  int32 score = 1;  // centipawns
}

message HealthRequest {}

message HealthResponse {
  enum Status {
    UNKNOWN = 0;
    SERVING = 1;
    NOT_SERVING = 2;
  }
  Status status = 1;
}
```

#### 2. EngineClient в Cloud Function

**Новый модуль:** `engine_client.py`

```python
import grpc
import logging
from typing import Optional
from stockfish_pb2 import BestMoveRequest, HealthRequest
from stockfish_pb2_grpc import EngineServiceStub

logger = logging.getLogger(__name__)

class EngineClient:
    """Клиент для подключения к Stockfish микросервису с fallback на локальный движок."""

    def __init__(self, service_url: str, local_engine=None, timeout_seconds: float = 5.0):
        """
        Args:
            service_url: gRPC адрес сервиса (e.g., 'stockfish-service:50051')
            local_engine: Локальный engine для fallback (Game.engine)
            timeout_seconds: Timeout для gRPC запроса
        """
        self.service_url = service_url
        self.local_engine = local_engine
        self.timeout_seconds = timeout_seconds
        self.channel = None
        self.stub = None

    def _connect(self) -> bool:
        """Подключиться к сервису. Возвращает True если успешно."""
        try:
            self.channel = grpc.aio.secure_channel(
                self.service_url,
                grpc.ssl_channel_credentials()
            )
            self.stub = EngineServiceStub(self.channel)

            # Проверить здоровье сервиса
            response = self.stub.Health(HealthRequest(), timeout=self.timeout_seconds)
            if response.status == HealthResponse.Status.SERVING:
                logger.info(f'Connected to Stockfish service at {self.service_url}')
                return True
        except Exception as e:
            logger.warning(f'Failed to connect to Stockfish service: {e}')
            self.channel = None
            self.stub = None
        return False

    def best_move(self, fen: str, skill_level: int, time_limit: float) -> str:
        """
        Получить лучший ход.

        Стратегия:
        1. Попытаться получить ход из микросервиса (с timeout)
        2. Если ошибка → fallback на локальный engine
        3. Если локального нет → исключение
        """
        # Попытка 1: микросервис
        if self.stub:
            try:
                request = BestMoveRequest(
                    fen=fen,
                    skill_level=skill_level,
                    time_limit_seconds=time_limit
                )
                response = self.stub.BestMove(request, timeout=self.timeout_seconds)
                logger.info(f'Got move from service: {response.move}')
                emit_counter('skill.engine.remote', tags={'skill_level': str(skill_level)})
                return response.move
            except grpc.RpcError as e:
                logger.warning(f'Stockfish service error: {e.code()} {e.details()}')
                emit_counter('skill.engine.remote_error', tags={'code': str(e.code())})

        # Fallback: локальный engine
        if self.local_engine:
            logger.info('Falling back to local engine')
            emit_counter('skill.engine.local_fallback')
            return str(self.local_engine.best_move(fen, skill_level, time_limit))

        # Ошибка: нет ни сервиса, ни локального движка
        raise RuntimeError('No engine available (service down and no local fallback)')

    async def close(self):
        """Закрыть подключение."""
        if self.channel:
            await self.channel.close()
```

#### 3. Интеграция в Game

**Изменение в `game.py`:**

```python
class Game:
    def __init__(self, skill_level: int = 1, ..., engine_client: EngineClient | None = None):
        self._engine = None  # Локальный engine (fallback)
        self.engine_client = engine_client
        ...

    def comp_move(self) -> str:
        """Ход компьютера с использованием микросервиса и fallback."""
        if self.engine_client:
            return self.engine_client.best_move(
                fen=self.board.fen(),
                skill_level=self.skill_level,
                time_limit=self.time_level
            )
        else:
            # Fallback на локальный engine (текущее поведение)
            return str(self.engine.best_move(self.board, chess.engine.Limit(time=self.time_level)))
```

#### 4. Инициализация в alice_serverless

```python
import os
from engine_client import EngineClient

def handler(event, context):
    global _COLD_START_PENDING

    # Инициализировать клиент микросервиса
    service_url = os.getenv('STOCKFISH_SERVICE_URL', None)
    engine_client = None
    if service_url:
        engine_client = EngineClient(
            service_url=service_url,
            timeout_seconds=float(os.getenv('STOCKFISH_TIMEOUT', '5.0'))
        )

    try:
        with measure_duration('skill.handler.duration_ms'):
            with AliceChess(engine_client=engine_client) as alice:
                response = alice.handle_request(event)
                ...
    finally:
        if engine_client:
            asyncio.run(engine_client.close())
```

### Конфигурация

**Переменные окружения:**
- `STOCKFISH_SERVICE_URL` — адрес gRPC сервиса (e.g., `stockfish-service:50051`). Если не задана → используется локальный engine.
- `STOCKFISH_TIMEOUT` — timeout для gRPC запроса в секундах (по умолчанию 5.0)
- `STOCKFISH_FALLBACK_ENABLED` — включить fallback на локальный engine (по умолчанию `true`)

**Зависимости:**
- Добавить в `requirements.txt`: `grpcio>=1.50.0`, `grpcio-tools>=1.50.0`

### Развёртывание микросервиса

**Вариант 1: Yandex Compute Instance**
```bash
# На инстансе
git clone <stockfish-service-repo>
cd stockfish-service
docker build -t stockfish-service .
docker run -d -p 50051:50051 stockfish-service
```

**Вариант 2: Yandex Container Registry + Kubernetes**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: stockfish-service
spec:
  replicas: 1
  selector:
    matchLabels:
      app: stockfish-service
  template:
    metadata:
      labels:
        app: stockfish-service
    spec:
      containers:
      - name: stockfish
        image: cr.yandex/my-registry/stockfish-service:latest
        ports:
        - containerPort: 50051
        resources:
          requests:
            memory: "512Mi"
            cpu: "1000m"
          limits:
            memory: "1Gi"
            cpu: "2000m"
---
apiVersion: v1
kind: Service
metadata:
  name: stockfish-service
spec:
  selector:
    app: stockfish-service
  ports:
  - protocol: TCP
    port: 50051
    targetPort: 50051
  type: ClusterIP
```

## Последствия

**Плюсы:**
- Исключение холодного старта Stockfish (~50–150 ms экономия на каждый запрос)
- Переиспользование одного инстанса движка между всеми запросами
- Масштабируемость: можно добавить несколько реплик микросервиса
- Возможность использовать более мощный Stockfish (16+, многопоточный)
- Graceful degradation: если сервис недоступен → fallback на локальный engine
- Метрики: `skill.engine.remote` / `skill.engine.local_fallback` / `skill.engine.remote_error`

**Минусы:**
- Усложнение архитектуры (новый микросервис, gRPC, сетевые ошибки)
- Сетевая задержка (~10–50 ms в зависимости от расстояния)
- Требует управления отдельным сервисом (мониторинг, логирование, обновления)
- Потенциальная точка отказа (если сервис упадёт, функция работает медленнее)
- Требует SSL/TLS для gRPC в production

**Компромиссы:**
- Timeout 5 секунд — компромисс между надёжностью и задержкой. Если сервис не ответит за 5 сек → fallback.
- Fallback на локальный engine гарантирует, что функция никогда не упадёт из-за недоступности сервиса.
- Один инстанс микросервиса может обслуживать ~100–1000 запросов в секунду (зависит от сложности позиций).

## Инварианты, которые нельзя нарушать

- **Fallback обязателен.** Функция должна работать без микросервиса.
- **Timeout на gRPC запрос.** Не должна зависать на недоступном сервисе.
- **Локальный engine остаётся в коде.** Не удалять, даже если микросервис работает.
- **Метрики для мониторинга.** Отслеживать `skill.engine.remote` vs `skill.engine.local_fallback` для понимания надёжности сервиса.
- **Тесты должны работать без микросервиса.** Mock gRPC или отключить сервис в тестах.

## Связанные документы

- [ADR-0002: Жизненный цикл Stockfish](0002-stockfish-lifecycle.md)
- [ADR-0004: Кэш позиций в Redis](0004-position-cache-redis.md)
- [`AGENTS.md`](../../AGENTS.md) — инварианты для агентов
- [`metrics.py`](../../metrics.py) — система метрик

## Следующие шаги

1. Создать отдельный репозиторий `stockfish-service`
2. Реализовать gRPC сервис на Go/Python
3. Написать `EngineClient` с fallback логикой
4. Интегрировать в `Game.comp_move()`
5. Добавить метрики `skill.engine.remote` / `skill.engine.local_fallback`
6. Развернуть микросервис в staging
7. Профилировать задержку и надёжность
8. Настроить мониторинг и алерты для микросервиса
9. Развернуть в production с постепенным rollout (10% → 50% → 100%)

## Риски и смягчение

| Риск | Вероятность | Влияние | Смягчение |
|------|-------------|--------|----------|
| Микросервис упадёт | Средняя | Высокое (медленнее) | Fallback на локальный engine |
| Сетевая задержка | Высокая | Низкое (10–50 ms) | Timeout 5 сек, кэш позиций |
| Несинхронизированные версии Stockfish | Низкая | Среднее (разные ходы) | Версионирование в gRPC API |
| Утечка памяти в микросервисе | Низкая | Высокое (crash) | Мониторинг памяти, graceful restart |
