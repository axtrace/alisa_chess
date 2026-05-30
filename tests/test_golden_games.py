"""Интеграционные «золотые партии».

Эти тесты проверяют, что навык корректно обрабатывает реалистичные
последовательности запросов Алисы: состояние одного ответа передаётся
во вход следующего запроса (как это делает платформа), а реакции
проверяются на полном response payload, а не на отдельных моках.

Stockfish заменён глобальной фикстурой в `tests/conftest.py` стабом,
который всегда отвечает e2e4. Это накладывает ограничение на сценарии
с большим числом ходов компьютера, поэтому здесь мы покрываем
короткие, но информативные сценарии.
"""

import unittest

from alice_serverless import handler
from skill_state import SkillState


def _base_event():
    """Минимальный шаблон запроса Алисы."""
    return {
        "meta": {
            "locale": "ru-RU",
            "timezone": "UTC",
            "client_id": "ru.yandex.searchplugin/7.16",
            "interfaces": {"screen": {}},
        },
        "session": {
            "message_id": 0,
            "session_id": "golden-session",
            "skill_id": "golden-skill",
            "user": {"user_id": "golden-user"},
            "application": {"application_id": "golden-app"},
            "user_id": "golden-user",
            "new": True,
        },
        "request": {
            "command": "",
            "original_utterance": "",
            "nlu": {"tokens": [], "entities": [], "intents": {}},
            "markup": {"dangerous_context": False},
            "type": "SimpleUtterance",
        },
        "state": {"session": {}, "user": {}, "application": {}},
        "version": "1.0",
    }


def make_event(command, intents=None, *, user_state=None, session_state=None, message_id=0, new=False):
    """Собирает запрос Алисы с заданными командой/интентами и накопленным состоянием."""
    event = _base_event()
    event["session"]["new"] = new
    event["session"]["message_id"] = message_id
    event["request"]["command"] = command
    event["request"]["original_utterance"] = command
    if command:
        event["request"]["nlu"]["tokens"] = command.split()
    if intents:
        event["request"]["nlu"]["intents"] = intents
    if user_state:
        event["state"]["user"] = {"game_state": user_state}
    if session_state:
        event["state"]["session"] = session_state
    return event


class GoldenSession:
    """Имитирует клиента Алисы: прокидывает state из ответа в следующий запрос."""

    def __init__(self):
        self.user_state = None
        self.session_state = None
        self.message_id = 0
        self.responses = []

    def send(self, command, intents=None, *, new=False):
        event = make_event(
            command,
            intents=intents,
            user_state=self.user_state,
            session_state=self.session_state,
            message_id=self.message_id,
            new=new,
        )
        response = handler(event, None)
        self.responses.append(response)
        self.user_state = (response.get("user_state_update") or {}).get("game_state")
        self.session_state = response.get("session_state")
        self.message_id += 1
        return response

    def resend_last(self):
        """Повторяет последний запрос с тем же message_id (идемпотентность)."""
        last = self.responses[-1]
        event = make_event(
            "",
            user_state=self.user_state,
            session_state=self.session_state,
            message_id=self.message_id - 1,
        )
        response = handler(event, None)
        self.responses.append(response)
        return response, last


class TestGoldenGames(unittest.TestCase):
    """Golden-сценарии: фиксированные последовательности → проверяем полный response."""

    def _assert_response_shape(self, response):
        """Каждый ответ должен иметь обязательные поля Алисы."""
        self.assertEqual(response["version"], "1.0")
        self.assertIn("session", response)
        self.assertIn("response", response)
        self.assertIn("text", response["response"])
        self.assertIn("tts", response["response"])
        self.assertIn("end_session", response["response"])
        self.assertIn("user_state_update", response)

    # ---------- Сценарий 1: старт с выбором белых ----------

    def test_start_white_flow(self):
        """Пустой первый запрос → «да» → «белые». Игрок ходит первым."""
        session = GoldenSession()

        # 1. Первый запрос без интентов — InitiatedHandler выдаёт приветствие
        #    и переводит в WAITING_CONFIRM.
        r1 = session.send("")
        self._assert_response_shape(r1)
        self.assertFalse(r1["response"]["end_session"])
        self.assertEqual(
            session.user_state["skill_state"], SkillState.WAITING_CONFIRM.value
        )

        # 2. «Да» → переход к выбору цвета
        r2 = session.send("да")
        self._assert_response_shape(r2)
        self.assertEqual(
            session.user_state["skill_state"], SkillState.WAITING_COLOR.value
        )

        # 3. «Белые» → стартует партия, ход пользователя
        r3 = session.send("белые")
        self._assert_response_shape(r3)
        self.assertEqual(
            session.user_state["skill_state"], SkillState.WAITING_MOVE.value
        )
        self.assertEqual(session.user_state["user_color"], "WHITE")
        # Доска не тронута — компьютер ещё не ходил
        self.assertTrue(
            session.user_state["board_state"].startswith(
                "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"
            )
        )
        self.assertIn("ход", r3["response"]["text"].lower())

    # ---------- Сценарий 2: старт с выбором чёрных (компьютер ходит первым) ----------

    def test_start_black_flow(self):
        """Игрок выбирает чёрных → компьютер сразу делает ход e2e4."""
        session = GoldenSession()
        session.send("")
        session.send("да")
        # Используем интент BLACK_WORD: extract_color по тексту работает только
        # с формой без «ё» («черные»), а через интент — детерминированно.
        r3 = session.send("черные", intents={"BLACK_WORD": {}})

        self._assert_response_shape(r3)
        self.assertEqual(
            session.user_state["skill_state"], SkillState.WAITING_MOVE.value
        )
        self.assertEqual(session.user_state["user_color"], "BLACK")
        # Компьютер сходил e2e4 — пешка на e4
        self.assertIn(
            "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR",
            session.user_state["board_state"],
        )

    # ---------- Сценарий 3: идемпотентность по message_id ----------

    def test_idempotency_same_message_id(self):
        """Повтор запроса с тем же message_id возвращает кэшированный response."""
        session = GoldenSession()
        session.send("")
        first = session.send("да")

        # Повторяем тот же запрос (тот же message_id, та же сессия)
        repeat, original = session.resend_last()
        self.assertEqual(repeat["response"]["text"], original["response"]["text"])
        self.assertEqual(repeat["response"]["tts"], original["response"]["tts"])
        # Состояние не должно «уйти» вперёд
        self.assertEqual(
            session.user_state["skill_state"], SkillState.WAITING_COLOR.value
        )

    # ---------- Сценарий 4: помощь во время партии не ломает состояние ----------

    def test_help_during_game_preserves_state(self):
        """В WAITING_MOVE «помощь» отвечает текстом помощи, не меняя ход."""
        session = GoldenSession()
        session.send("")
        session.send("да")
        session.send("белые")
        board_before = session.user_state["board_state"]
        state_before = session.user_state["skill_state"]

        r_help = session.send("помощь", intents={"YANDEX.HELP": {}})
        self._assert_response_shape(r_help)
        # Состояние не сдвинулось
        self.assertEqual(session.user_state["board_state"], board_before)
        self.assertEqual(session.user_state["skill_state"], state_before)

    # ---------- Сценарий 5: сдача через подтверждение ----------

    def test_resign_flow(self):
        """«Сдаюсь» → запрос подтверждения → «да» → GAME_OVER."""
        session = GoldenSession()
        session.send("")
        session.send("да")
        session.send("белые")

        r_resign = session.send("сдаюсь", intents={"RESIGN": {}})
        self._assert_response_shape(r_resign)
        self.assertEqual(
            session.user_state["skill_state"],
            SkillState.WAITING_RESIGN_CONFIRM.value,
        )

        r_confirm = session.send("да")
        self._assert_response_shape(r_confirm)
        # После подтверждения сдачи навык переходит обратно в INITIATED
        # (готов начать новую партию) — см. WaitingResignConfirmHandler.on_accept.
        self.assertEqual(
            session.user_state["skill_state"], SkillState.INITIATED.value
        )

    # ---------- Сценарий 6: новая игра в середине партии ----------

    def test_new_game_in_progress(self):
        """«Новая игра» в WAITING_MOVE → подтверждение → сброс к WAITING_COLOR."""
        session = GoldenSession()
        session.send("")
        session.send("да")
        session.send("белые")

        r_new = session.send("новая игра", intents={"NEW_GAME": {}})
        self._assert_response_shape(r_new)
        self.assertEqual(
            session.user_state["skill_state"],
            SkillState.WAITING_NEWGAME_CONFIRM.value,
        )

        r_confirm = session.send("да")
        self._assert_response_shape(r_confirm)
        # После подтверждения навык снова ждёт выбора цвета
        self.assertEqual(
            session.user_state["skill_state"], SkillState.WAITING_COLOR.value
        )
        # Доска сброшена
        self.assertTrue(
            session.user_state["board_state"].startswith(
                "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"
            )
        )


if __name__ == "__main__":
    unittest.main()
