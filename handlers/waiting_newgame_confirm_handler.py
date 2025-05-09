import texts
from .base_handler import BaseHandler
from request_validators.intent_validator import IntentValidator


class WaitingNewgameConfirmHandler(BaseHandler):
    """Обработчик состояния ожидания подтверждения новой игры."""
    
    def __init__(self, game, request):
        super().__init__(game, request)
        self.intent_validator = IntentValidator(request)

    def handle(self):
        """Обрабатывает запрос в состоянии ожидания подтверждения новой игры."""
        print(f"WaitingNewgameConfirmHandler. handle. Запрос: {self.request}")
        if self.intent_validator.validate_yes():
            self.reset_game()
            self.game.set_skill_state('WAITING_CONFIRM')
            return self.say(texts.hi_text)
            
        if self.intent_validator.validate_no():
            self.restore_prev_state()
            return self.say(texts.newgame_declined_text)
            
        return self.say(texts.newgame_offer_text) 