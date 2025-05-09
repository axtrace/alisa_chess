import texts
from .base_handler import BaseHandler
from request_validators.intent_validator import IntentValidator


class WaitingResignConfirmHandler(BaseHandler):
    """Обработчик состояния ожидания подтверждения сдачи."""
    
    def __init__(self, game, request):
        super().__init__(game, request)
        self.intent_validator = IntentValidator(request)

    def handle(self):
        """Обрабатывает запрос в состоянии ожидания подтверждения сдачи.""" 
        print(f"WaitingResignConfirmHandler. handle. Запрос: {self.request}")
        if self.intent_validator.validate_yes():
            self.game.set_skill_state('INITIATED')
            return self.say(texts.resign_accepted_text)
            
        if self.intent_validator.validate_no():
            # self.game.set_skill_state('WAITING_MOVE')
            self.restore_prev_state()
            return self.say(texts.resign_declined_text)
            
        return self.say(texts.resign_offer_text) 