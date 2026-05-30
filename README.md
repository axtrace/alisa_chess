# alisa_chess

Голосовой шахматный навык для Яндекс.Алисы: игра в шахматы вслепую с озвучиванием ходов.

## Возможности

- Голосовая игра в шахматы через Яндекс.Алису
- Шахматный движок Stockfish (локальный бинарь, запускается по UCI через [`python-chess`](https://github.com/niklasf/python-chess))
- Распознавание ходов в нескольких форматах: SAN, длинная нотация (`e2e4`), русскоязычные команды («пешка е4», «конь на эф 3»)
- Превращение пешки (с явным указанием фигуры или ферзём по умолчанию)
- Специальные команды и интенты: помощь, новая игра, сдача, ничья, отмена хода, показать доску, выбор уровня сложности
- Восстановление состояния игры между запросами через `user_state_update`
- Идемпотентность повторных запросов по `message_id`
- Поддержка `YANDEX.REPEAT` через `session_state`
- Версионируемая схема состояния игры (Pydantic V2) с graceful fallback при ошибках десериализации

## Состояния навыка

Перечислены в [`skill_state.py`](skill_state.py:4):

- `INITIATED` — приветствие, ожидание согласия на игру
- `WAITING_CONFIRM` — ожидание подтверждения начала игры
- `WAITING_COLOR` — выбор цвета пользователем
- `WAITING_SKILL_LEVEL` — выбор уровня сложности
- `WAITING_MOVE` — ожидание хода пользователя
- `WAITING_DRAW_CONFIRM` — подтверждение предложения ничьей
- `WAITING_RESIGN_CONFIRM` — подтверждение сдачи
- `WAITING_NEWGAME_CONFIRM` — подтверждение начала новой партии
- `GAME_OVER` — партия завершена

Полная диаграмма переходов: [`docs/diagrams/state_diagram.md`](docs/diagrams/state_diagram.md).

## Голосовые команды

Доступны в большинстве состояний игры:

- «Помощь» — справка по игре
- «Покажи доску» — текущая позиция в виде FEN/Unicode
- «Новая игра» — начать новую партию
- «Уровень сложности» — изменить уровень игры
- «Повтори» — повтор последнего ответа Алисы (`YANDEX.REPEAT`)
- «Отмени ход» / «Назад» — откатить последний ход (если доступно)
- «Ничья» — предложить ничью
- «Сдаюсь» — сдаться

## Установка

1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/axtrace/alisa_chess.git
   cd alisa_chess
   ```

2. Создайте и активируйте виртуальное окружение:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

3. Установите Python-зависимости:
   ```bash
   pip install -r requirements.txt
   ```

4. Положите бинарь Stockfish в корень проекта рядом с `alice_chess.py` под именем `stockfish` (исполняемый файл):
   ```bash
   chmod +x ./stockfish
   ```
   Бинарь не входит в репозиторий, его нужно скачать или собрать самостоятельно с [официального сайта](https://stockfishchess.org/download/).

## Структура проекта

- [`alice_chess.py`](alice_chess.py:1) — основной класс `AliceChess`, точка входа в обработку запроса
- [`alice_serverless.py`](alice_serverless.py:1) — точка входа для Yandex Cloud Functions (`handler(event, context)`)
- [`game.py`](game.py:1) — игровая логика, обёртка над `chess.Board` и UCI-движком Stockfish
- [`game_state.py`](game_state.py:1) — Pydantic-схемы `GameStateV1`/`GameStateV2`, миграции и сериализация
- [`skill_state.py`](skill_state.py:1) — enum состояний навыка
- [`handlers/`](handlers/) — обработчики состояний (`WaitingMoveHandler`, `InitiatedHandler`, `BaseConfirmationHandler` и т. д.)
- [`request_validators/`](request_validators/) — валидаторы интентов
- [`move_extractor.py`](move_extractor.py:1) — парсинг хода пользователя из интентов и текста (включая кириллицу)
- [`speaker.py`](speaker.py:1), [`text_preparer.py`](text_preparer.py:1) — построение текста и TTS-ответа
- [`texts.py`](texts.py:1) — шаблоны фраз
- [`intents/`](intents/) — YAML-описания интентов Алисы
- [`tests/`](tests/) — юнит-тесты (pytest/unittest)
- [`docs/`](docs/) — архитектурная документация и диаграммы

## Пример сценария

```text
Алиса: Давайте сыграем в шахматы.
Юзер: Да.
Алиса: За какую сторону играем — белые или чёрные?
Юзер: Белые.
Алиса: Хорошо. Ваш ход.
Юзер: e2 e4.
Алиса: Конь f6. Ваш ход.
Юзер: Покажи доску.
Алиса: [показывает текущую позицию]
...
Алиса: Мат. Спасибо за игру.
```

## Формат состояния

Состояние игры передаётся через `state.user.game_state` и обновляется через `user_state_update`. Схема описана в [`game_state.py`](game_state.py:60) (`GameStateV2`):

```json
{
  "request": {"command": "e2e4", "...": "..."},
  "state": {
    "user": {
      "game_state": {
        "_version": 2,
        "board_state": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "skill_state": "WAITING_MOVE",
        "prev_skill_state": "WAITING_CONFIRM",
        "user_color": "WHITE",
        "comp_color": "BLACK",
        "skill_level": 1,
        "time_level": 0.1
      }
    },
    "session": {
      "last_message_id": 3,
      "previous_response": {"text": "...", "tts": "...", "end_session": false}
    }
  }
}
```

- `board_state` — FEN текущей позиции.
- `skill_state` / `prev_skill_state` — текущее и предыдущее состояния навыка (значения из [`SkillState`](skill_state.py:4)).
- `_version` — версия схемы; при чтении состояний с другой схемой выполняется автоматическая миграция (см. [`GameState.from_dict`](game_state.py:103)).
- `session_state.last_message_id` — используется для идемпотентности (повторный `message_id` возвращает предыдущий ответ).
- `session_state.previous_response` — последний ответ, возвращается при `YANDEX.REPEAT`.

## Тестирование

Запуск всех тестов:

```bash
python3 -m pytest tests/ -v
```

Или через unittest:

```bash
python3 -m unittest discover tests
```

## Развёртывание

Поддерживается развёртывание как Yandex Cloud Function. Точка входа — `alice_serverless.handler`. Workflow для деплоя лежат в [`.github/workflows/`](.github/workflows/). Подробнее в [`docs/deployment.md`](docs/deployment.md).

**Изменения после одобрения модератора:**
Удалены процессы `Manual Deploy to TESTING YaCloud Functions` и `Manual Deploy to PROD YaCloud Functions`, остались только `Manual Deploy 2 PROD YaCloud Functions` и `Auto Deploy 2 TESTING YaCloud Functions`. Переменные оставлены с постфиксом `_2` для совместимости.

## Архитектура

- Основная логика — класс [`AliceChess`](alice_chess.py:18); обрабатывает запрос как контекстный менеджер, гарантированно закрывая UCI-движок.
- Игровая обёртка — класс [`Game`](game.py:9) с ленивой инициализацией Stockfish и обязательным `engine.quit()` через `__exit__`.
- Маршрутизация по состояниям реализована в [`AliceChess.handle_request`](alice_chess.py:49) на основе `SkillState`.
- Каждое состояние обрабатывается соответствующим хендлером из [`handlers/`](handlers/), наследующим [`BaseHandler`](handlers/base_handler.py:8).
- Специальные команды (помощь, показ доски, повтор, новая игра и т. д.) обрабатываются в [`SpecialIntentHandler`](handlers/special_intent_handler.py:10) независимо от текущего состояния.
- Обработка ошибок двухуровневая: `BaseHandler.safe_handle` возвращает дружелюбное сообщение, а `alice_serverless.handler` ловит катастрофические исключения и не теряет `user_state_update`.

Подробности: [`docs/architecture.md`](docs/architecture.md), диаграммы состояний и последовательности в [`docs/diagrams/`](docs/diagrams/).

## Технические детали

- Шахматный движок: Stockfish, локальный бинарь, UCI-протокол через [python-chess](https://github.com/niklasf/python-chess).
- Валидация состояния: [Pydantic v2](https://docs.pydantic.dev/) (`requirements.txt`).
- Сервер исторически использовал отдельный HTTP-API ([axtrace/chessapi](https://github.com/axtrace/chessapi)) — в текущей версии Stockfish запускается локально внутри функции.

## Участие в разработке

PR приветствуются. Перед отправкой — прогоните тесты и убедитесь, что `pytest` зелёный.

## Лицензия

[MIT License](LICENSE) © 2024 axtrace
