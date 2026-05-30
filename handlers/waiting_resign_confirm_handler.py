import texts
from .base_confirmation_handler import BaseConfirmationHandler
from skill_state import SkillState
import logging

logger = logging.getLogger(__name__)


class WaitingResignConfirmHandler(BaseConfirmationHandler):
    """Обработчик состояния ожидания подтверждения сдачи."""

    @property
    def accepted_text(self) -> str:
        return texts.resign_accepted_text

    @property
    def declined_text(self) -> str:
        return texts.resign_declined_text

    @property
    def repeat_text(self) -> str:
        return texts.waiting_resign_confirm_text

    def on_accept(self):
        self.game.set_skill_state(SkillState.INITIATED)

    def handle(self):
        logger.info(f"WaitingResignConfirmHandler.handle. Запрос: {self.request}")
        return super().handle()
