# alisa_chess

[Русский](README.md) · **English**

Play blindfold chess with Yandex Alice. You say your moves aloud, and Alice announces her replies.

## Features

- Play by voice with Yandex Alice.
- Play against a local Stockfish binary that communicates over UCI through [python-chess](https://github.com/niklasf/python-chess).
- Enter moves in standard algebraic notation (SAN), long coordinate notation (`e2e4`), or spoken Russian, such as «пешка е4» (“pawn e4”) or «конь на эф 3» (“knight to f3”).
- Choose a piece for pawn promotion. The default is a queen.
- Ask for help, start a game, resign, offer a draw, undo a move, show the board, or change the difficulty.
- Ask «Назови позицию» (“Describe the position”) to hear the pieces on both sides. Ask «Где мои кони?» (“Where are my knights?”) to hear just the squares your knights occupy.
- Say «Отмени ход» (“Undo my move”) to take back your move and Alice’s reply. This also restores the previous record of the opponent’s last move.
- Game state persists across requests through `user_state_update`. The versioned Pydantic v2 schema provides a fallback if deserialization fails.
- Requests with a repeated `message_id` replay the previous response. The `YANDEX.REPEAT` intent also retrieves the last reply from `session_state`.

## Skill states

The [`SkillState` enum](skill_state.py#L4) defines the following states.

| State | Meaning |
| --- | --- |
| `INITIATED` | Alice greets the player and invites them to play. |
| `WAITING_CONFIRM` | Waiting for the player to confirm they want to play. |
| `WAITING_COLOR` | The player chooses White or Black. |
| `WAITING_SKILL_LEVEL` | The player chooses the difficulty. |
| `WAITING_MOVE` | Waiting for the player’s move. |
| `WAITING_DRAW_CONFIRM` | Waiting for confirmation of a draw offer. |
| `WAITING_RESIGN_CONFIRM` | Waiting for the player to confirm resignation. |
| `WAITING_NEWGAME_CONFIRM` | Waiting for confirmation before starting a new game. |
| `GAME_OVER` | The game has ended. |

See the [state transition diagram](docs/diagrams/state_diagram.md) for the full sequence.

## Voice commands

These Russian commands are available in most game states.

| Say | Action |
| --- | --- |
| «Помощь» | Get help with the game. |
| «Покажи доску» | Show the current position as FEN and a Unicode board. |
| «Новая игра» | Start a new game. |
| «Уровень сложности» | Change the difficulty. |
| «Повтори» | Repeat Alice’s last reply (`YANDEX.REPEAT`). |
| «Отмени ход» or «Назад» | Take back the last move when available. |
| «Ничья» | Offer a draw. |
| «Сдаюсь» | Resign. |

## Installation

1. Clone the repository.

   ```bash
   git clone https://github.com/axtrace/alisa_chess.git
   cd alisa_chess
   ```

2. Create and activate a virtual environment.

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

3. Install the Python dependencies.

   ```bash
   pip install -r requirements.txt
   ```

4. Download Stockfish from the [official website](https://stockfishchess.org/download/) or build it yourself. Place the binary in the project root next to `alice_chess.py`, name it `stockfish`, and make it executable.

   ```bash
   chmod +x ./stockfish
   ```

## Project layout

| Path | Purpose |
| --- | --- |
| [`alice_chess.py`](alice_chess.py) | The `AliceChess` class coordinates request handling. |
| [`alice_serverless.py`](alice_serverless.py) | Yandex Cloud Functions entry point, `handler(event, context)`. |
| [`game.py`](game.py) | Game logic, wrapping `chess.Board` and the Stockfish UCI engine. |
| [`game_state.py`](game_state.py) | Pydantic schemas (`GameStateV1` and `GameStateV2`), migration, and serialization. |
| [`skill_state.py`](skill_state.py) | The skill state enum. |
| [`handlers/`](handlers/) | State handlers, including `WaitingMoveHandler`, `InitiatedHandler`, and `BaseConfirmationHandler`. |
| [`request_validators/`](request_validators/) | Intent validators. |
| [`move_extractor.py`](move_extractor.py) | Parses moves from intents and text, including Cyrillic input. |
| [`speaker.py`](speaker.py), [`text_preparer.py`](text_preparer.py) | Build the display text and text-to-speech (TTS) reply. |
| [`texts.py`](texts.py) | Phrase templates. |
| [`intents/`](intents/) | Alice intent definitions in YAML. |
| [`tests/`](tests/) | Unit tests using pytest and unittest. |
| [`docs/`](docs/) | Architecture documentation and diagrams. |

## Example game

This exchange is translated from Russian.

```text
Alice: Shall we play chess?
Player: Yes.
Alice: Would you like to play White or Black?
Player: White.
Alice: All right. Your move.
Player: e2 e4.
Alice: Knight to f6. Your move.
Player: Show the board.
Alice: [shows the current position]
...
Alice: Checkmate. Thanks for playing.
```

## Game state format

Alice sends the game state in `state.user.game_state`. The skill saves updates through `user_state_update`. The schema is defined in [`GameStateV2`](game_state.py#L60).

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

- `board_state` stores the current position in FEN.
- `skill_state` and `prev_skill_state` hold the current and previous [`SkillState`](skill_state.py#L4) values.
- `_version` identifies the schema version. [`GameState.from_dict`](game_state.py#L104) migrates older states when it reads them.
- `session_state.last_message_id` makes requests idempotent. A repeated `message_id` returns the previous reply.
- `session_state.previous_response` stores the last reply for `YANDEX.REPEAT`.

## Testing

Run the full test suite with pytest.

```bash
python3 -m pytest tests/ -v
```

To run tests with unittest, use the discovery command.

```bash
python3 -m unittest discover tests
```

## Deployment

GitHub Actions deploys the Cloud Functions. Merging into the main branch updates the test voice skill. To update the production skill or the test API, trigger the corresponding workflow manually. The [deployment guide](docs/deployment.md) covers triggers, package contents, and version checks.

After moderator approval, the project retired the `Manual Deploy to TESTING YaCloud Functions` and `Manual Deploy to PROD YaCloud Functions` workflows. The two remaining voice skill workflows are `Manual Deploy 2 PROD YaCloud Functions` and `Auto Deploy 2 TESTING YaCloud Functions`. Their variables retain the `_2` suffix for compatibility.

## Architecture

- [`AliceChess`](alice_chess.py#L19) handles each request as a context manager so the UCI engine is closed afterwards.
- [`Game`](game.py#L13) starts Stockfish on demand and calls `engine.quit()` through `__exit__`.
- [`AliceChess.handle_request`](alice_chess.py#L53) routes requests by `SkillState`.
- Each state has a [handler](handlers/) that inherits from [`BaseHandler`](handlers/base_handler.py#L10).
- [`SpecialIntentHandler`](handlers/special_intent_handler.py#L15) handles commands such as help, show board, repeat, and new game across states.
- `BaseHandler.safe_handle` returns a user-friendly message on error. The outer `alice_serverless.handler` catches otherwise unhandled exceptions and preserves `user_state_update`.

See the [architecture guide](docs/architecture.md) and the [state and sequence diagrams](docs/diagrams/) for details.

## Roadmap

Two proposals target engine performance.

- The [Redis position cache](docs/adr/0004-position-cache-redis.md) aims to make repeated positions 50–100 times faster to evaluate.
- The [Stockfish microservice](docs/adr/0005-stockfish-microservice.md) would avoid cold starts by keeping an engine running and providing a fallback.

The [full roadmap](docs/ROADMAP.md) includes the schedule and tasks.

## Technical details

- The skill runs Stockfish as a local binary and communicates with it over UCI through [python-chess](https://github.com/niklasf/python-chess).
- [Pydantic v2](https://docs.pydantic.dev/) validates game state. See [`requirements.txt`](requirements.txt) for the dependency specification.
- Earlier versions called the separate [axtrace/chessapi HTTP API](https://github.com/axtrace/chessapi). The current version runs Stockfish inside the Cloud Function.

## Contributing

Pull requests are welcome. Run the test suite and make sure pytest passes before submitting a change.

## License

MIT License © 2024 axtrace
