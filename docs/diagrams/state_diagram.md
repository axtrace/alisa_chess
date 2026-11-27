# Состояния голосового диалога

Прод и разрешённый аккаунт тестового навыка используют одни обработчики `SkillState`.
Схема показывает основной сценарий. Специальные интенты обрабатываются до выбора
хендлера текущего состояния. При отказе от подтверждения или смены сложности
восстанавливается `prev_skill_state`.

```mermaid
stateDiagram-v2
    [*] --> INITIATED
    INITIATED --> WAITING_CONFIRM: Приветствие
    WAITING_CONFIRM --> WAITING_COLOR: Да
    WAITING_COLOR --> WAITING_MOVE: Цвет выбран, при чёрных ходит Stockfish
    WAITING_MOVE --> WAITING_NEWGAME_CONFIRM: Новая игра
    GAME_OVER --> WAITING_NEWGAME_CONFIRM: Новая игра
    WAITING_NEWGAME_CONFIRM --> WAITING_COLOR: Да, сброс позиции и цвета
    WAITING_NEWGAME_CONFIRM --> WAITING_MOVE: Нет, возврат к предыдущему состоянию
    WAITING_MOVE --> WAITING_DRAW_CONFIRM: Ничья
    WAITING_DRAW_CONFIRM --> INITIATED: Да
    WAITING_DRAW_CONFIRM --> WAITING_MOVE: Нет
    WAITING_MOVE --> WAITING_RESIGN_CONFIRM: Сдаюсь
    WAITING_RESIGN_CONFIRM --> INITIATED: Да
    WAITING_RESIGN_CONFIRM --> WAITING_MOVE: Нет
    WAITING_MOVE --> WAITING_SKILL_LEVEL: Изменить сложность
    WAITING_SKILL_LEVEL --> WAITING_MOVE: Уровень выбран или изменение отменено
    WAITING_MOVE --> GAME_OVER: Мат, пат или условие ничьей

    note right of WAITING_MOVE
        Ход, помощь, показ позиции и отмена
        обычно сохраняют WAITING_MOVE
    end note
```

| Данные автомата | Прод | Тестовый общий режим |
| --- | --- | --- |
| Текущий и предыдущий этап | `state.user.game_state` | YDB, `players.dialog` |
| Возврат в новой сессии | Снимок из Диалогов | Снимок диалога, согласованный с ревизией партии |
| Подтверждение после изменения позиции | Контекст одного навыка | Проверка `game_ref` и `dialog_revision` |

Превращение пешки разбирается в ходе обработки хода. Реальные значения состояний
перечислены в [skill_state.py](../../skill_state.py).
