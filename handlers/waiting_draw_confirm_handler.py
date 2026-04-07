import texts
from .waiting_confirmation_handler import WaitingConfirmationHandler
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class WaitingDrawConfirmHandler(WaitingConfirmationHandler):
    """Обработчик состояния ожидания подтверждения ничьей."""

    @property
    def accepted_text(self) -> str:
        return texts.draw_accepted_text

    @property
    def declined_text(self) -> str:
        return texts.draw_declined_text

    @property
    def repeat_text(self) -> str:
        return texts.waiting_draw_confirm_text

    def on_accept(self):
        self.game.set_skill_state('INITIATED')

    def handle(self):
        logger.info(f"WaitingDrawConfirmHandler.handle. Запрос: {self.request}")
        return super().handle()
