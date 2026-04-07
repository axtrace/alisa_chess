import texts
from .waiting_confirmation_handler import WaitingConfirmationHandler
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class WaitingNewgameConfirmHandler(WaitingConfirmationHandler):
    """Обработчик состояния ожидания подтверждения новой игры."""

    @property
    def accepted_text(self) -> str:
        return ''

    @property
    def declined_text(self) -> str:
        return texts.newgame_declined_text

    @property
    def repeat_text(self) -> str:
        return texts.waiting_newgame_confirm_text

    def on_accept(self):
        self.reset_game()
        self.game.set_skill_state('WAITING_COLOR')

    def handle(self):
        logger.info(f"WaitingNewgameConfirmHandler.handle. Запрос: {self.request}")
        if self.intent_validator.validate_yes():
            self.on_accept()
            state_text = texts.state_texts.get(self.game.get_skill_state(), '')
            return self.say(state_text)

        if self.intent_validator.validate_no():
            self.restore_prev_state()
            state_text = texts.state_texts.get(self.game.get_skill_state(), '')
            return self.say(self.declined_text + '\n' + state_text)

        return self.say(self.repeat_text)
