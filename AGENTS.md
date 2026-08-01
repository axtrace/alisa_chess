# AGENTS.md

Instructions for LLM agents (Codex, Cursor, Cline, Continue, Claude Code, etc.) working with the `alisa_chess` repository. The goal of this document is to set common rules of the game, list project invariants, and help the agent get into the current context without lengthy exploration.

> **Note:** The project's [`README.md`](README.md) is written in **Russian**. Keep it in Russian when updating.

---

## 1. About the project in one paragraph

`alisa_chess` is a voice chess skill for Yandex Alice. It is deployed as a Yandex Cloud Function ([`alice_serverless.handler`](alice_serverless.py:7)). Engine moves are computed by a local Stockfish binary launched via UCI using [python-chess](https://github.com/niklasf/python-chess). Game state is passed between requests via `state.user.game_state` (the schema is described in [`game_state.py`](game_state.py:1)).

---

## 2. Strict invariants (do NOT violate without explicit discussion)

These are contracts that must NOT be broken. If it seems a task requires breaking one — ask first.

1. **Stockfish is initialized lazily** ([`Game.engine`](game.py:58)). Do not call `popen_uci` in `__init__` without considering serverless cold start.
2. **`engine.quit()` is mandatory**. The current solution is [`Game.__exit__`](game.py:179) and `with AliceChess() as alice` in [`alice_serverless.handler`](alice_serverless.py:18). Any code path that opens the engine must guarantee it is closed.
3. **Idempotency by `message_id`**. A repeated request with the same `message_id` must return `previous_response` from `session_state` without a second engine move.
4. **`YANDEX.REPEAT` lives in `session_state.previous_response`**, not in `user_state_update`.
5. **`user_state_update` is ALWAYS saved**, including in the catch-all. Never return a response without `user_state_update` when state exists — this would lose the player's game.
6. **The session is NOT closed on a handler error**. `end_session: True` — only in the catastrophic catch in [`alice_serverless`](alice_serverless.py:34) and on `GAME_OVER`.
7. **State serialization is via Pydantic** ([`GameStateV2`](game_state.py:60)) with versioning (`_version`) and graceful V1→V2 migration.
8. **`SkillState` is an enum** ([`skill_state.py`](skill_state.py:4)). When comparing states, prefer `SkillState.WAITING_MOVE` over the string `'WAITING_MOVE'` (migration in progress — task №11).
9. **Tests must stay green**. Currently 69/69 passed. Any change that breaks tests requires updating the tests in the same PR with an explanation of why the assertion is outdated.
10. **The Stockfish binary is NOT committed**, it is added separately. Do not touch any mentions of it in `.gitignore` without coordination.

---

## 3. Architecture and where things are

| Layer | Files | Purpose |
|---|---|---|
| Entry point (Cloud Function) | [`alice_serverless.py`](alice_serverless.py:1) | `handler(event, context)`, catch-all, response building |
| Coordinator | [`alice_chess.py`](alice_chess.py:1) | `AliceChess`, routing by `SkillState`, idempotency, `session_state` |
| Game model | [`game.py`](game.py:1) | `Game`: `chess.Board` wrapper + UCI, lazy engine |
| State | [`game_state.py`](game_state.py:1) | Pydantic schemas V1/V2, migrations, (de)serialize |
| State enum | [`skill_state.py`](skill_state.py:1) | `SkillState` |
| Handlers | [`handlers/`](handlers/) | One file per state, inherit [`BaseHandler`](handlers/base_handler.py:8) |
| Move parser | [`move_extractor.py`](move_extractor.py:1) | Extracts a move from intents and text (RU/EN, SAN, long notation) |
| Texts/TTS | [`text_preparer.py`](text_preparer.py:1), [`speaker.py`](speaker.py:1), [`texts.py`](texts.py:1) | Building the response `text`/`tts` |
| Validators | [`request_validators/`](request_validators/) | Intent validation |
| Alice intents | [`intents/*.yaml`](intents/) | NLU description |
| Tests | [`tests/`](tests/) | pytest/unittest |
| Documentation | [`docs/`](docs/) | Architecture, deployment, diagrams |

State diagram: [`docs/diagrams/state_diagram.md`](docs/diagrams/state_diagram.md).
Request processing sequence diagram: [`docs/diagrams/sd_request_processing.md`](docs/diagrams/sd_request_processing.md).

---

## 4. Commands for the agent

### Running tests

```bash
python3 -m pytest tests/ -v
```

The minimum requirement before a commit is all tests green. Do not push red tests.

### A single file / single test

```bash
python3 -m pytest tests/test_alice_chess.py::TestAliceChess::test_handle_request_promotion -v
```

### Lint / formatting

```bash
ruff check .          # style check
ruff format .         # automatic formatting
mypy .                # type checking (gradually adopted)
pre-commit run --all-files  # run all pre-commit hooks
```

Configured as part of task №17: `ruff` (lint+format), `mypy` (gradual), `pre-commit` + CI check.

### Local handler run

Place the Stockfish binary at the project root as `./stockfish` and run `chmod +x` on it. Without it, engine initialization will fail on a real computer move.

---

## 5. Style and conventions

- Code language: **Python 3.14+** (Yandex Cloud Functions runtime).
- Commas — a space after, operators (`=`, `==`, `>`, `<`, `||`, etc.) — spaces around.
- Names: `snake_case` for functions/files/variables, `PascalCase` for classes, `UPPER_SNAKE` for constants.
- Logging — via `logging` (a module-level logger), no `print` in production code. `print` in tests is acceptable for debugging but should preferably be removed before merge.
- Pydantic v2: `@field_validator` + `@classmethod`, `model_dump()` instead of `.dict()`.
- Markdown in YAML/docs — correct links and code blocks with a language specified.

### Commit messages

- Version control system: git.
- Short description in Russian or English.
- One commit — one logical idea.
- PR size — up to ~650 lines of changes ([`coding-standard.md`](.roo/rules/coding-standard.md)).

---

## 6. Change strategy

### Minimal invasiveness

Do not do extra refactoring unless the task requires it. Preserve the existing style and structure. If you see an improvement opportunity unrelated to the task — **a separate PR**.

### Test-aware

Before changing logic, check which tests cover it:

```bash
grep -rn "<function_name>" tests/
```

If you change a class's public contract — update the tests in the same PR, explaining in the description why the assertion is outdated.

### Fact-based

Do not assume the existence of files/functions that are not in the repository. Before using a function/method in new code — open the source and check the signature.

### Alice contracts

Any response fields (`response.text`, `response.tts`, `end_session`, `buttons`) and state fields (`game_state`, `session_state`) are a contract with the platform. Before changing — check the [official Alice docs](https://yandex.ru/dev/dialogs/alice/doc/protocol.html) and existing tests.

---

## 7. Common pitfalls

| Symptom | Cause | Solution |
|---|---|---|
| A test with a `Game` mock tries to run the real Stockfish | `@patch('game.Game')` does not patch the `from game import Game` import in [`alice_chess.py`](alice_chess.py:1) | Use `@patch('alice_chess.Game')` |
| An `AliceChess` mock does not work in the serverless test | The code uses `with AliceChess() as alice:`, the actual object is `__enter__()` | `mock_instance.__enter__.return_value = mock_instance` |
| `_find_matching_moves` returns empty on a mock | `board.legal_moves` on a MagicMock is an empty collection | Replace `game.board` with a real `chess.Board(fen)` |
| `previous_response` is lost between moves | It is written to `user_state_update` instead of `session_state` | Store it in `session_state.previous_response` |
| The game "forgets" the match after an error | `user_state_update` is not passed in the error response | Snapshot the input state → the catastrophic catch returns it |

---

## 8. Roadmap

*Future improvements may include:*
- Expanding golden tests with more complex scenarios
- Adding engine performance metrics
- Supporting additional voice platforms

---

## 9. Checklist before completing a task

- [ ] Tests are green: `python3 -m pytest tests/ -v`
- [ ] If a public contract changed — tests updated + explanation in the PR description
- [ ] All invariants from section 2 are respected
- [ ] No `print()` and `setLevel()` in production code (unless a conscious decision within the task)
- [ ] `requirements.txt` is synchronized if dependencies were added/removed
- [ ] Documentation ([`README.md`](README.md), [`docs/`](docs/)) is updated if API/behavior changes
- [ ] The change fits into one logical idea (PR ≤ ~650 lines)

---

## 10. What NOT to do without an explicit request

- Change code formatting style.
- Rename public methods/classes.
- Delete "redundant" code from your point of view — it may be needed for compatibility with old state in production.
- Change the text format from [`texts.py`](texts.py:1) — this affects TTS and therefore the user experience.
- Add new dependencies to `requirements.txt` without discussion (serverless cold start).
- Commit local configs: `.venv/`, `tokens.py`, `exp.py`, the `stockfish` binary.
- Run `git push` without an explicit command from the owner.

---

## 11. Useful links

- Project README: [`README.md`](README.md)
- Architecture: [`docs/architecture.md`](docs/architecture.md)
- Deployment: [`docs/deployment.md`](docs/deployment.md)
- Skill API: [`docs/api.md`](docs/api.md)
- Catalog skill description: [`docs/skill_description.md`](docs/skill_description.md)
- Diagrams: [`docs/diagrams/`](docs/diagrams/)
- Alice protocol: https://yandex.ru/dev/dialogs/alice/doc/protocol.html
- python-chess: https://python-chess.readthedocs.io/

---

*If this document contradicts the code reality — the codebase is authoritative. After discovering a discrepancy, immediately update `AGENTS.md` in the same PR.*
