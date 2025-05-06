import texts
from .base_handler import BaseHandler
from request_validators.intent_validator import IntentValidator


class GameOverHandler(BaseHandler):
    """Обработчик состояния окончания игры."""
    
    def __init__(self, game, request):
        super().__init__(game, request)
        self.intent_validator = IntentValidator(request)

    def handle(self):
        """Обрабатывает запрос в состоянии окончания игры."""
        if self.intent_validator.validate_new_game():
            self.game.set_skill_state('INITIATED')
            return self.say(texts.hi_text)
            
        return self.say(texts.game_over_text) 