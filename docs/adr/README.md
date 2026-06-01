# Architecture Decision Records

ADR — короткие документы, фиксирующие важные архитектурные решения проекта. Формат: контекст → варианты → решение → последствия.

| № | Решение | Статус |
|---|---|---|
| [0001](0001-state-machine.md) | Конечный автомат состояний навыка через `SkillState` | Accepted |
| [0002](0002-stockfish-lifecycle.md) | Жизненный цикл Stockfish в serverless | Accepted |
| [0003](0003-game-state-serialization.md) | Сериализация GameState (Pydantic + версионирование + миграции) | Accepted |
| [0004](0004-position-cache-redis.md) | Кэш позиций в Redis для ускорения повторных ходов | Proposed |
| [0005](0005-stockfish-microservice.md) | Stockfish как отдельный микросервис с fallback на локальный engine | Proposed |

## Правила

- Один ADR — одно решение.
- Файл не удаляется, даже если решение отменено: добавляется новый ADR со статусом `Supersedes ADR-NNNN`, а у старого статус меняется на `Superseded by ADR-NNNN`.
- Номер ADR — sequential, без переиспользования.
- Шаблон: см. структуру [`0001-state-machine.md`](0001-state-machine.md).
