# Архитектура проекта

`alisa_chess` — голосовой шахматный навык для Яндекс.Алисы, развёрнутый как Yandex Cloud Function. Движок — локальный бинарь [Stockfish](https://stockfishchess.org/) (минимально совместимая версия — 14+), поднимаемый по UCI через [python-chess](https://github.com/niklasf/python-chess).

## Основные компоненты

### 1. Точка входа (Cloud Function)
- [`alice_serverless.py`](../alice_serverless.py) — функция `handler(event, context)`, верхний уровень catch-all, привязка контекста логирования, формирование ответа в формате протокола Алисы.

### 2. Координатор навыка
- [`alice_chess.py`](../alice_chess.py) — класс `AliceChess`. Маршрутизация по [`SkillState`](../skill_state.py), идемпотентность по `message_id`, чтение/запись `session_state` (включая `previous_response` для `YANDEX.REPEAT`).

### 3. Игровая логика
- [`game.py`](../game.py) — класс `Game`: обёртка над `chess.Board` + UCI. Ленивая инициализация Stockfish, контекстный менеджер `__enter__/__exit__` с гарантированным `engine.quit()`.
- [`move_extractor.py`](../move_extractor.py) — `MoveExtractor`: извлечение хода из NLU-интентов и свободного текста (RU/EN, SAN, длинная нотация, рокировки, превращения).

### 4. Состояние игры и enum
- [`game_state.py`](../game_state.py) — Pydantic-схемы `GameStateV1` / `GameStateV2`, автоопределение версии (`_version`), graceful миграция V1→V2, фабрика `create_game_state_from_game()`, восстановление `restore_game_from_state()`.
- [`skill_state.py`](../skill_state.py) — `class SkillState(str, Enum)`. Используется во всех хендлерах и в `game.py` вместо строковых литералов.

### 5. Обработчики состояний
Каждый файл в [`handlers/`](../handlers/) отвечает за одно состояние навыка и наследуется от [`BaseHandler`](../handlers/base_handler.py):

| Файл | Состояние / роль |
|---|---|
| `base_handler.py` | Абстрактный базовый класс + `safe_handle()` (per-handler try/except) |
| `base_confirmation_handler.py` | Базовый класс для подтверждающих хендлеров (да/нет) |
| `initiated_handler.py` | Стартовое состояние, приветствие |
| `waiting_color_handler.py` | Ожидание выбора цвета пользователем |
| `waiting_confirm_handler.py` | Подтверждение начала игры |
| `waiting_move_handler.py` | Ожидание хода пользователя; основная боевая логика |
| `waiting_skill_level_handler.py` | Установка уровня сложности |
| `waiting_draw_confirm_handler.py` | Подтверждение ничьей |
| `waiting_resign_confirm_handler.py` | Подтверждение сдачи |
| `waiting_newgame_confirm_handler.py` | Подтверждение новой игры |
| `game_over_handler.py` | Завершение партии |
| `special_intent_handler.py` | Универсальные интенты (help, undo, repeat, show_board, …) через `_intent_registry` |

### 6. Тексты и TTS
- [`texts.py`](../texts.py) — все текстовые шаблоны навыка.
- [`text_preparer.py`](../text_preparer.py) — `TextPreparer`: формирование `text` и базового `tts`.
- [`speaker.py`](../speaker.py) — `Speaker`: озвучка ходов, фигур, мат/пат.
- [`tts_builder.py`](../tts_builder.py) — `TtsBuilder`: SSML-хелперы (паузы `silence`, `speaker` для звуковых эффектов, префиксы/суффиксы). Все SSML-теги вынесены сюда из хендлеров.

### 7. Валидаторы
- [`request_validators/`](../request_validators/) — `BaseValidator`, `IntentValidator` (yes/no/help/draw/resign/new_game/set_skill_level/show_board, …).

### 8. NLU-интенты Алисы
- [`intents/*.yaml`](../intents/) — описания намерений и сущностей (фигуры, цвета, рокировки, ходы).

### 9. Логирование
- [`logging_config.py`](../logging_config.py) — единственный источник конфигурации:
  - `JsonFormatter` — структурированный вывод JSON (`ts`, `level`, `logger`, `message`, `ctx`, extra-поля).
  - `setup_logging()` — идемпотентная установка root-handler'а.
  - `_request_context: ContextVar` + `bind_request_context(**fields)` / `clear_request_context()` — привязка `session_id`/`message_id`/`user_id` к каждому запросу.
- Все модули используют `logger = logging.getLogger(__name__)` без `setLevel`. Уровень задаётся переменной окружения `LOG_LEVEL` (по умолчанию `INFO`).

### 10. Тесты
- [`tests/`](../tests/) — pytest/unittest.
- [`tests/conftest.py`](../tests/conftest.py) — autouse-фикстура, глобально подменяющая `chess.engine.SimpleEngine.popen_uci` фейковым движком. Гарантирует, что ни один unit-тест не запустит реальный бинарь Stockfish.

## Поток данных

1. Пользователь обращается к Алисе → платформа вызывает Yandex Cloud Function.
2. [`alice_serverless.handler`](../alice_serverless.py) принимает `event`, вызывает `setup_logging()` (no-op при warm container), привязывает `session_id` / `message_id` / `user_id` к ContextVar.
3. Создаётся `AliceChess` через `with`-блок (гарантирует `engine.quit()` через `Game.__exit__`).
4. `AliceChess.handle_request()`:
   - десериализует `state.user.game_state` через `GameState.from_dict()` (V1→V2 миграция при необходимости);
   - проверяет идемпотентность по `last_message_id` из `session_state`;
   - маршрутизирует на нужный хендлер по `SkillState`.
5. Хендлер парсит интенты/текст, валидирует, при необходимости вызывает `Game.user_move()` / `Game.comp_move()`.
6. Ответ собирается в `text`/`tts` через `TextPreparer`, `Speaker`, `TtsBuilder`.
7. `alice_serverless` возвращает payload с `response`, `user_state_update.game_state`, `session_state.previous_response` (+ `last_message_id`).
8. При исключении на любом уровне срабатывает либо `BaseHandler.safe_handle`, либо катастрофический catch в `alice_serverless` — оба сохраняют `user_state_update` со снимком состояния.

## Конфигурация

### Переменные окружения
| Переменная | Назначение | По умолчанию |
|---|---|---|
| `LOG_LEVEL` | Уровень логирования root-logger'а | `INFO` |

### Настройки деплоя (Yandex Cloud Function)
- Runtime: Python 3.9 (минимально поддерживаемая версия; локально CI прогоняется и на 3.11).
- Entry point: `alice_serverless.handler`.
- Память: 2048 MB (testing), 4096 MB (prod).
- Stockfish-бинарь кладётся рядом как `./stockfish` и НЕ коммитится в репозиторий (см. [`AGENTS.md`](../AGENTS.md), `.gitignore`).
- Зависимости фиксируются в [`requirements.txt`](../requirements.txt) для деплоя; «канонический» источник истины — [`pyproject.toml`](../pyproject.toml).

## Диаграммы

- Конечный автомат состояний: [`docs/diagrams/state_diagram.md`](diagrams/state_diagram.md).
- Sequence обработки запроса: [`docs/diagrams/sd_request_processing.md`](diagrams/sd_request_processing.md).
- Диаграмма классов: [`docs/diagrams/class_diagram.md`](diagrams/class_diagram.md).
- Контекстная диаграмма C4 L1: [`docs/diagrams/alice-chess-c4level1.jpg`](diagrams/alice-chess-c4level1.jpg).

## Связанные документы

- [`AGENTS.md`](../AGENTS.md) — правила и инварианты для агентов и разработчиков.
- [`README.md`](../README.md) — общее описание проекта.
- [`docs/api.md`](api.md) — формат запроса/ответа Алисы.
- [`docs/deployment.md`](deployment.md) — пошаговый деплой.
- [`docs/skill_description.md`](skill_description.md) — публичное описание навыка для каталога.
