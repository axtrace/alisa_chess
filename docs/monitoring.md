# Мониторинг и алерты

Документ описывает метрики, которые эмитит навык `alisa_chess`, и рекомендации по их визуализации и алертингу в Yandex Monitoring.

## Подход

Навык работает в Yandex Cloud Function, где недоступен прямой push-клиент Monitoring без дополнительной инфраструктуры. Поэтому метрики эмитятся как структурированные log-записи через [`logging_config.JsonFormatter`](../logging_config.py:1) и [`metrics`](../metrics.py:1). Yandex Monitoring подключается к Cloud Logging как источник log-based метрик: фильтр строится по полю `metric`, агрегация — по `metric_value` и `metric_tags`.

Каждая запись метрики имеет вид:

```json
{
  "message": "metric",
  "metric": "skill.request",
  "metric_kind": "counter",
  "metric_value": 1,
  "metric_tags": {"kind": "..."},
  "session_id": "...",
  "message_id": "...",
  "user_id": "..."
}
```

Поля `session_id`/`message_id`/`user_id` подмешиваются автоматически через [`ContextVar`](../logging_config.py:1) (см. ADR-0001 и задачу №18).

## Каталог метрик

| Метрика | Тип | Где эмитится | Назначение |
|---|---|---|---|
| `skill.cold_start` | counter | [`alice_serverless.handler()`](../alice_serverless.py:37) при первом запросе после старта контейнера | Доля холодных стартов |
| `skill.request` | counter | [`alice_serverless.handler()`](../alice_serverless.py:37) на каждый входящий запрос | Базовый RPS |
| `skill.handler.duration_ms` | histogram | [`measure_duration`](../metrics.py:1) внутри [`handler()`](../alice_serverless.py:37) | Latency обработки запроса |
| `skill.error` | counter, tag `kind=<ExceptionType>` | catch-all в [`handler()`](../alice_serverless.py:37) | Частота катастрофических ошибок |
| `skill.move.ok` | counter | [`WaitingMoveHandler._handle_user_move()`](../handlers/waiting_move_handler.py:59) после успешного хода | Доля корректных ходов |
| `skill.move.not_defined` | counter | [`_reason_handler()`](../handlers/waiting_move_handler.py:138) | Ход не распознан в команде |
| `skill.move.invalid` | counter | [`_reason_handler()`](../handlers/waiting_move_handler.py:138) | Нелегальный ход на доске |
| `skill.move.ambiguous` | counter | [`_reason_handler()`](../handlers/waiting_move_handler.py:138) | Команда соответствует нескольким ходам |

## Настройка log-based метрик в Yandex Monitoring

1. В Cloud Logging выбрать лог-группу функции навыка.
2. Создать кастомную метрику, фильтр:
   ```
   json_payload.message = "metric" AND json_payload.metric = "<имя метрики>"
   ```
3. Для counter — агрегация `SUM(json_payload.metric_value)`.
4. Для histogram (`skill.handler.duration_ms`) — `PERCENTILE(json_payload.metric_value, 0.95)` и `PERCENTILE(..., 0.99)`.
5. Опционально сгруппировать по `json_payload.metric_tags.kind`.

## Рекомендованные алерты

| Алерт | Условие | Цель |
|---|---|---|
| Error rate | `SUM(skill.error) / SUM(skill.request)` > 1% за 5 мин | Поймать массовые сбои |
| Latency p95 | `PERCENTILE(skill.handler.duration_ms, 0.95)` > 2000 ms за 5 мин | Деградация Stockfish или сетевые задержки |
| Latency p99 | `PERCENTILE(skill.handler.duration_ms, 0.99)` > 4000 ms за 5 мин | Хвостовые таймауты |
| Invalid move spike | `SUM(skill.move.invalid + skill.move.not_defined) / SUM(skill.move.*)` > 30% за 10 мин | Сломан парсер или NLU |
| Ambiguous move spike | `SUM(skill.move.ambiguous) / SUM(skill.move.*)` > 15% за 10 мин | Проблема дизамбигуации |
| Cold start rate | `SUM(skill.cold_start) / SUM(skill.request)` > 20% за 15 мин (информационно) | Сигнал низкого трафика / мелкого пула воркеров |

Пороги — стартовые рекомендации, подгонять под реальный профиль после двух-трёх недель наблюдения.

## Связанные документы

- [`docs/architecture.md`](architecture.md)
- [`docs/adr/0001-state-machine.md`](adr/0001-state-machine.md)
- [`logging_config.py`](../logging_config.py:1)
- [`metrics.py`](../metrics.py:1)
