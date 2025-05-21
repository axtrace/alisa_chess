import texts
from .base_handler import BaseHandler
from request_validators.intent_validator import IntentValidator
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class WaitingNewgameConfirmHandler(BaseHandler):
    """Обработчик состояния ожидания подтверждения новой игры."""
    
    def __init__(self, game, request):
        super().__init__(game, request)
        self.intent_validator = IntentValidator(request)

    def handle(self):
        """Обрабатывает запрос в состоянии ожидания подтверждения новой игры."""
        logger.info(f"WaitingNewgameConfirmHandler. handle. Запрос: {self.request}") 
        if self.intent_validator.validate_yes():
            self.reset_game()
            self.game.set_skill_state('WAITING_CONFIRM')
            state_text = texts.state_texts.get(self.game.get_skill_state(), '')
            return self.say(state_text)
            
        if self.intent_validator.validate_no():
            self.restore_prev_state()
            state_text = texts.state_texts.get(self.game.get_skill_state(), '')
            return self.say(texts.newgame_declined_text + '\n' + state_text)
            
        return self.say(texts.waiting_newgame_confirm_text) 