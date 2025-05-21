import texts
from .base_handler import BaseHandler
from request_validators.intent_validator import IntentValidator
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class WaitingConfirmHandler(BaseHandler):
    """Обработчик состояния ожидания подтверждения начала игры."""
    
    def __init__(self, game, request):
        super().__init__(game, request)
        self.validator = IntentValidator(request)

    def handle(self):
        """Обрабатывает запрос в состоянии ожидания подтверждения."""
        logger.info(f"WaitingConfirmHandler. handle. Запрос: {self.request}") 
        if self.validator.validate_yes():    
            self.game.set_skill_state('WAITING_COLOR')
            text, text_tts = self.text_preparer.say_choose_color()
            return self.say(text, tts=text_tts) 
        else:
            return self.say(texts.dng_start_text)