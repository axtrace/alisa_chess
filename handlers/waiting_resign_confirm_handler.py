import texts
from .base_handler import BaseHandler
from request_validators.intent_validator import IntentValidator
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class WaitingResignConfirmHandler(BaseHandler):
    """Обработчик состояния ожидания подтверждения сдачи."""
    
    def __init__(self, game, request):
        super().__init__(game, request)
        self.intent_validator = IntentValidator(request)

    def handle(self):
        """Обрабатывает запрос в состоянии ожидания подтверждения сдачи.""" 
        logger.info(f"WaitingResignConfirmHandler. handle. Запрос: {self.request}") 
        if self.intent_validator.validate_yes():
            self.game.set_skill_state('INITIATED')
            state_text = texts.state_texts.get(self.game.get_skill_state(), '')
            return self.say(texts.resign_accepted_text + '\n' + state_text)
            
        if self.intent_validator.validate_no():
            # self.game.set_skill_state('WAITING_MOVE')
            self.restore_prev_state()
            state_text = texts.state_texts.get(self.game.get_skill_state(), '')
            return self.say(texts.resign_declined_text + '\n' + state_text)
            
        return self.say(texts.waiting_resign_confirm_text) 