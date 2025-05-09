import texts
from .base_handler import BaseHandler
from request_validators.intent_validator import IntentValidator


class WaitingDrawConfirmHandler(BaseHandler):
    """Обработчик состояния ожидания подтверждения ничьей."""
    
    def __init__(self, game, request):
        super().__init__(game, request)
        self.intent_validator = IntentValidator(request)

    def handle(self):
        """Обрабатывает запрос в состоянии ожидания подтверждения ничьей."""
        print(f"WaitingDrawConfirmHandler. handle. Запрос: {self.request}")
        if self.intent_validator.validate_yes():
            self.game.set_skill_state('INITIATED')
            return self.say(texts.draw_accepted_text)
            
        if self.intent_validator.validate_no():
            # self.game.set_skill_state('WAITING_MOVE')
            self.restore_prev_state()
            return self.say(texts.draw_declined_text)
            
        return self.say(texts.draw_offer_text) 