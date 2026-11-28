# Обработка голосового запроса

## Прод

```mermaid
sequenceDiagram
    participant D as Яндекс Диалоги
    participant F as alice_serverless.handler
    participant A as AliceChess
    participant G as Game
    participant E as Stockfish 14.1
    D->>F: Запрос, state.user / state.application и state.session
    Note over F,A: Аккаунт — user; аноним — application
    F->>A: handle_request(event)
    alt Дубликат message_id
        A-->>F: previous_response из session_state
    else Новый запрос
        A->>G: Восстановить GameState V1/V2
        A->>A: Специальный интент или обработчик SkillState
        alt YANDEX.REPEAT
            A-->>F: previous_response из session_state
        else Обычная команда
            opt Нужен ответный ход
                A->>G: comp_move()
                G->>E: Ленивый запуск UCI и расчёт
                E-->>G: Ход
            end
            A-->>F: Ответ и обновлённые состояния
        end
    end
    F->>G: Game.quit() при выходе из with AliceChess
    Note over G,E: Созданный процесс Stockfish закрывается
    F-->>D: response, user_state_update / application_state, session_state
    D->>D: Сохранить позицию и контекст сессии
```

## Тестовый навык

Схема показывает обычную команду разрешённого аккаунта. Входной адаптер также
может вернуть короткую сохранённую реплику из сессии или передать аккаунт вне
пилота без `game_ref` продовому обработчику.

```mermaid
sequenceDiagram
    participant D as Яндекс Диалоги
    participant F as shared_alice_serverless.handler
    participant A as SharedAlice
    participant S as GameService
    participant DB as YDB
    participant C as AliceChess и VoiceGame
    participant E as Stockfish 19
    D->>F: Закрытый IAM-вызов с запросом и state
    F->>F: Проверить функцию, навык, аккаунт / приложение и его allowlist
    F->>A: handle(event, owner)
    A->>DB: Найти команду или сохранённый ответ
    alt Команда уже завершена или запрошен повтор
        DB-->>A: Сохранённый результат или полная реплика
    else Новая команда
        A->>S: execute() с ID команды и ревизиями
        S->>DB: Транзакция резервирования
        DB-->>S: Снимок партии, диалог и lease
        S->>C: play_dialog() со штатными обработчиками
        opt Нужен ответный ход
            C->>E: Локальный UCI-расчёт вне транзакции YDB
            E-->>C: Ход
            Note over C,E: Процесс Stockfish закрывается
        end
        C-->>S: Позиция, этап диалога и ответ
        S->>DB: Проверить lease и ревизию, сохранить всё одной транзакцией
        DB-->>S: Записанный результат команды
        S-->>A: Результат и ссылка на ответ
    end
    A-->>F: Ответ, совместимый снимок и game_ref
    F-->>D: response, user_state_update / application_state, session_state
```

Ходы приложения проходят через Gateway и `ChessApi` в собственный экземпляр
того же `GameService`. Конфликтующие операции проверяются по общей ревизии в YDB.
Резервирование и завершение команды описаны в [архитектуре тестового контура](../architecture.md#тест).
