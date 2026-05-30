# AGENTS.md

Инструкции для LLM-агентов (Codex, Cursor, Cline, Continue, Claude Code и др.), работающих с репозиторием `alisa_chess`. Цель документа — задать единые правила игры, перечислить инварианты проекта и помочь агенту сразу попасть в актуальный контекст без длинной разведки.

---

## 1. О проекте в одном абзаце

`alisa_chess` — голосовой шахматный навык для Яндекс.Алисы. Развёртывается как Yandex Cloud Function ([`alice_serverless.handler`](alice_serverless.py:7)). Ходы движка вычисляет локальный бинарь Stockfish, поднимаемый по UCI через [python-chess](https://github.com/niklasf/python-chess). Состояние игры передаётся между запросами через `state.user.game_state` (схема описана в [`game_state.py`](game_state.py:1)).

---

## 2. Жёсткие инварианты (НЕ нарушать без явного обсуждения)

Это контракты, которые ломать НЕЛЬЗЯ. Если кажется, что задача требует нарушить — сначала спроси.

1. **Stockfish инициализируется лениво** ([`Game.engine`](game.py:58)). Не делай `popen_uci` в `__init__` без оглядки на холодный старт serverless.
2. **`engine.quit()` обязателен**. Текущее решение — [`Game.__exit__`](game.py:179) и `with AliceChess() as alice` в [`alice_serverless.handler`](alice_serverless.py:18). Любая ветка кода, открывающая движок, должна гарантировать его закрытие.
3. **Идемпотентность по `message_id`**. Повторный запрос с тем же `message_id` обязан вернуть `previous_response` из `session_state` без второго хода движка.
4. **`YANDEX.REPEAT` живёт через `session_state.previous_response`**, а не через `user_state_update`.
5. **`user_state_update` сохраняется ВСЕГДА**, в том числе в catch-all. Никогда не возвращай ответ без `user_state_update` при наличии state — это потеряет партию игрока.
6. **Сессия НЕ закрывается на ошибке хендлера**. `end_session: True` — только в катастрофическом catch в [`alice_serverless`](alice_serverless.py:34) и при `GAME_OVER`.
7. **Сериализация состояния — через Pydantic** ([`GameStateV2`](game_state.py:60)) с версионированием (`_version`) и graceful миграцией V1→V2.
8. **`SkillState` — это enum** ([`skill_state.py`](skill_state.py:4)). При сравнении состояний предпочитай `SkillState.WAITING_MOVE`, а не строку `'WAITING_MOVE'` (миграция в процессе — задача №11).
9. **Тесты должны оставаться зелёными**. Сейчас 49/49 passed. Любое изменение, ломающее тесты, требует одновременного обновления тестов с объяснением, почему ассертион устарел.
10. **Stockfish бинарь НЕ коммитим**, он добавляется отдельно. Любые упоминания в `.gitignore` не трогать без согласования.

---

## 3. Архитектура и где что лежит

| Слой | Файлы | Назначение |
|---|---|---|
| Точка входа (Cloud Function) | [`alice_serverless.py`](alice_serverless.py:1) | `handler(event, context)`, catch-all, формирование response |
| Координатор | [`alice_chess.py`](alice_chess.py:1) | `AliceChess`, маршрутизация по `SkillState`, идемпотентность, `session_state` |
| Игровая модель | [`game.py`](game.py:1) | `Game`: обёртка `chess.Board` + UCI, ленивый движок |
| Состояние | [`game_state.py`](game_state.py:1) | Pydantic-схемы V1/V2, миграции, (de)serialize |
| Enum состояний | [`skill_state.py`](skill_state.py:1) | `SkillState` |
| Хендлеры | [`handlers/`](handlers/) | По одному файлу на состояние, наследуют [`BaseHandler`](handlers/base_handler.py:8) |
| Парсер ходов | [`move_extractor.py`](move_extractor.py:1) | Извлекает ход из интентов и текста (RU/EN, SAN, длинная нотация) |
| Тексты/TTS | [`text_preparer.py`](text_preparer.py:1), [`speaker.py`](speaker.py:1), [`texts.py`](texts.py:1) | Сборка `text`/`tts` ответа |
| Валидаторы | [`request_validators/`](request_validators/) | Проверка интентов |
| Интенты Алисы | [`intents/*.yaml`](intents/) | Описание NLU |
| Тесты | [`tests/`](tests/) | pytest/unittest |
| Документация | [`docs/`](docs/) | Архитектура, deployment, диаграммы |

Диаграмма состояний: [`docs/diagrams/state_diagram.md`](docs/diagrams/state_diagram.md).
Sequence-диаграмма обработки запроса: [`docs/diagrams/sd_request_processing.md`](docs/diagrams/sd_request_processing.md).

---

## 4. Команды агенту

### Запуск тестов

```bash
python3 -m pytest tests/ -v
```

Минимальная норма перед коммитом — все тесты зелёные. Не пушь красные тесты.

### Только один файл / один тест

```bash
python3 -m pytest tests/test_alice_chess.py::TestAliceChess::test_handle_request_promotion -v
```

### Линт / форматирование

Пока не настроены (задача №17). Если планируется правка большого объёма — обсуди с владельцем перед внедрением `ruff`/`mypy`.

### Локальный прогон handler

Stockfish бинарь нужно положить в корень как `./stockfish` и `chmod +x`. Без него инициализация движка упадёт при реальном ходе компьютера.

---

## 5. Стиль и соглашения

- Язык кода: **Python 3.9+** (Yandex Cloud Functions runtime).
- Запятые — пробел после, операторы (`=`, `==`, `>`, `<`, `||` и т. д.) — пробелы вокруг.
- Имена: `snake_case` для функций/файлов/переменных, `PascalCase` для классов, `UPPER_SNAKE` для констант.
- Логирование — через `logging` (модульный logger), без `print` в продакшен-коде. `print` в тестах допустимо как отладка, но лучше убирать перед мержем.
- Pydantic v2: `@field_validator` + `@classmethod`, `model_dump()` вместо `.dict()`.
- Markdown в YAML/документации — корректные ссылки и блоки кода с указанием языка.

### Сообщения коммитов

- Краткое описание на русском или английском.
- Один коммит — одна логическая идея.
- Размер PR — до ~650 строк изменений ([`coding-standard.md`](.roo/rules/coding-standard.md)).

---

## 6. Стратегия изменений

### Минимальная инвазивность

Не делай лишний рефакторинг, если задача не требует. Сохраняй существующий стиль и структуру. Если видишь возможность улучшения, не относящегося к задаче — **отдельный PR**.

### Test-aware

Перед изменением логики проверь, какие тесты её покрывают:

```bash
grep -rn "<имя_функции>" tests/
```

Если меняешь публичный контракт класса — обновляй тесты в том же PR, объясняя в описании, почему ассертион устарел.

### Fact-based

Не предполагай существование файлов/функций, которых нет в репозитории. Перед использованием функции/метода в новом коде — открой исходник и проверь сигнатуру.

### Контракты Алисы

Любые поля ответа (`response.text`, `response.tts`, `end_session`, `buttons`) и поля state (`game_state`, `session_state`) — это контракт с платформой. Перед изменением — проверь [официальные доки Алисы](https://yandex.ru/dev/dialogs/alice/doc/protocol.html) и существующие тесты.

---

## 7. Типичные ловушки

| Симптом | Причина | Решение |
|---|---|---|
| Тест с моком `Game` пытается запустить реальный Stockfish | `@patch('game.Game')` не патчит импорт `from game import Game` в [`alice_chess.py`](alice_chess.py:1) | Использовать `@patch('alice_chess.Game')` |
| Мок `AliceChess` не срабатывает в тесте serverless | Код использует `with AliceChess() as alice:`, фактический объект — это `__enter__()` | `mock_instance.__enter__.return_value = mock_instance` |
| `_find_matching_moves` возвращает пусто на моке | `board.legal_moves` у MagicMock — пустая коллекция | Подменить `game.board` настоящим `chess.Board(fen)` |
| `previous_response` теряется между ходами | Пишется в `user_state_update`, а не в `session_state` | Хранить в `session_state.previous_response` |
| Игра «забывает» партию после ошибки | `user_state_update` не передан в error-ответе | Снимок state на входе → катастрофический catch возвращает его |

---

## 8. Дорожная карта (открытые задачи)

В порядке убывания приоритета. **Если планируешь крупное изменение — сначала проверь, нет ли пересечения с задачей ниже.**

1. Перевести все сравнения состояний на [`SkillState`](skill_state.py:4) (убрать строковые литералы).
2. Заменить if/elif в [`SpecialIntentHandler`](handlers/special_intent_handler.py:10) на реестр интентов (dict: intent → method).
3. Удалить дубликат [`Game.is_move_legal`](game.py:140) / [`is_valid_move`](game.py:245).
4. Безопасная валидация и clamp уровня сложности (try/except + диапазон 1..20).
5. Ввести `TtsBuilder` и вынести SSML-разметку из хендлеров.
6. `pyproject.toml` без пинов версий; убрать [`setup.py`](setup.py:1) и упоминания Flask.
7. `ruff` (lint+format) + `mypy` (постепенно) + `pre-commit` + CI-чек.
8. Единый `logging_config.py`: `JsonFormatter`, `ContextVar`, `bind_request_context`; убрать `setLevel` из модулей.
9. Замокать Stockfish в unit-тестах [`tests/test_game.py`](tests/test_game.py:1) и [`tests/test_handlers.py`](tests/test_handlers.py:1).
10. Актуализировать [`docs/architecture.md`](docs/architecture.md): убрать несуществующие файлы, поправить версию движка.
11. ADR для трёх ключевых решений: state-machine, stockfish-lifecycle, сериализация состояния.
12. Метрики и алерты в Yandex Monitoring (latency, % invalid/ambiguous, error rate, cold start rate).
13. Интеграционные «золотые партии» поверх юнит-тестов.

---

## 9. Чек-лист перед завершением задачи

- [ ] Тесты зелёные: `python3 -m pytest tests/ -v`
- [ ] Если изменён публичный контракт — обновлены тесты + объяснение в описании PR
- [ ] Все инварианты из раздела 2 соблюдены
- [ ] Нет `print()` и `setLevel()` в продакшен-коде (если только это не сознательное решение в рамках задачи)
- [ ] `requirements.txt` синхронизирован, если добавлены/удалены зависимости
- [ ] Документация ([`README.md`](README.md), [`docs/`](docs/)) актуализирована, если меняется API/поведение
- [ ] Изменение умещается в одну логическую идею (PR ≤ ~650 строк)

---

## 10. Что НЕ нужно делать без явного запроса

- Менять стиль форматирования кода.
- Переименовывать публичные методы/классы.
- Удалять «лишний» с твоей точки зрения код — он может быть нужен для совместимости со старым state в продакшене.
- Менять формат текстов из [`texts.py`](texts.py:1) — это влияет на TTS, а значит на пользовательский опыт.
- Добавлять новые зависимости в `requirements.txt` без обсуждения (cold start serverless).
- Коммитить локальные конфиги: `.venv/`, `tokens.py`, `exp.py`, `stockfish` бинарь.
- Запускать `git push` без явной команды владельца.

---

## 11. Полезные ссылки

- README проекта: [`README.md`](README.md)
- Архитектура: [`docs/architecture.md`](docs/architecture.md)
- Деплой: [`docs/deployment.md`](docs/deployment.md)
- API навыка: [`docs/api.md`](docs/api.md)
- Описание навыка для каталога: [`docs/skill_description.md`](docs/skill_description.md)
- Диаграммы: [`docs/diagrams/`](docs/diagrams/)
- Протокол Алисы: https://yandex.ru/dev/dialogs/alice/doc/protocol.html
- python-chess: https://python-chess.readthedocs.io/

---

*Если этот документ противоречит реальности кода — кодовая база авторитетнее. После обнаружения расхождения сразу обнови `AGENTS.md` в том же PR.*
