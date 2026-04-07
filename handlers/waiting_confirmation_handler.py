import texts
from .base_handler import BaseHandler
from request_validators.intent_validator import IntentValidator
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class WaitingConfirmationHandler(BaseHandler):
    """Базовый класс для хендлеров, ожидающих подтверждения (да/нет)."""

    def __init__(self, game, request):
        super().__init__(game, request)
        self.intent_validator = IntentValidator(request)

    @property
    def accepted_text(self) -> str:
        """Текст при подтверждении."""
        raise NotImplementedError

    @property
    def declined_text(self) -> str:
        """Текст при отказе."""
        raise NotImplementedError

    @property
    def repeat_text(self) -> str:
        """Текст при непонятном ответе (повтор вопроса)."""
        raise NotImplementedError

    def on_accept(self):
        """Действие при подтверждении. Переопределяется в подклассах."""
        pass

    def handle(self):
        """Обрабатывает запрос: да → принять, нет → отклонить, иначе → повторить."""
        if self.intent_validator.validate_yes():
            self.on_accept()
            state_text = texts.state_texts.get(self.game.get_skill_state(), '')
            return self.say(self.accepted_text + '\n' + state_text)

        if self.intent_validator.validate_no():
            self.restore_prev_state()
            state_text = texts.state_texts.get(self.game.get_skill_state(), '')
            return self.say(self.declined_text + '\n' + state_text)

        return self.say(self.repeat_text)
