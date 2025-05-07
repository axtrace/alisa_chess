import texts
from .base_handler import BaseHandler
from move_extractor import MoveExtractor
from request_validators.intent_validator import IntentValidator 


class SpecialIntentHandler(BaseHandler):
    """Обработчик специальных намерений."""

    def __init__(self, game, request):
        super().__init__(game, request)
        self.move_ext = MoveExtractor()
        self.intent_validator = IntentValidator(request)

    def handle(self):
        # Проверяем специальные намерения, которые не зависят от состояния игры
        if self.intent_validator.validate_help():
            return self.say(texts.help_text)
            
        if self.intent_validator.validate_new_game():
            self.game.set_skill_state('WAITING_NEWGAME_CONFIRM')
            return self.say(texts.newgame_offer_text)
            
        if self.intent_validator.validate_draw():
            self.game.set_skill_state('WAITING_DRAW_CONFIRM')
            return self.say(texts.draw_offer_text)
            
        if self.intent_validator.validate_resign():
            self.game.set_skill_state('WAITING_RESIGN_CONFIRM')
            return self.say(texts.resign_offer_text)
        
        return None