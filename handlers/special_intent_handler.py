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
            print(f"SpecialIntentHandler. validate_help. Запрос: {self.request}")
            return self.say(texts.help_text)
        
            
        if self.intent_validator.validate_new_game():
            print(f"SpecialIntentHandler. validate_new_game. Запрос: {self.request}")
            self.game.set_skill_state('WAITING_NEWGAME_CONFIRM')
            return self.say(texts.newgame_offer_text)
            
        if self.intent_validator.validate_draw():
            print(f"SpecialIntentHandler. validate_draw. Запрос: {self.request}")
            self.game.set_skill_state('WAITING_DRAW_CONFIRM')
            return self.say(texts.draw_offer_text)
            
        if self.intent_validator.validate_resign():
            print(f"SpecialIntentHandler. validate_resign. Запрос: {self.request}")
            self.game.set_skill_state('WAITING_RESIGN_CONFIRM')
            return self.say(texts.resign_offer_text)
        if self.intent_validator.validate_unmake():
            print(f"SpecialIntentHandler. validate_unmake. Запрос: {self.request}")
            self.game.unmake_move()
            return self.say(texts.unmake_text)
        
        if self.intent_validator.validate_repeat_last_move():
            print(f"SpecialIntentHandler. validate_repeat_last_move. Запрос: {self.request}")
            self.game.repeat_last_move()
            return self.say(texts.repeat_last_move_text)

        if self.intent_validator.validate_get_skill_level():
            print(f"SpecialIntentHandler. validate_get_skill_level. Запрос: {self.request}")
            current_level = self.game.get_skill_level()
            return self.say(texts.get_skill_level_text.format(level=current_level))
        
        if self.intent_validator.validate_set_skill_level():
            print(f"SpecialIntentHandler. validate_set_skill_level. Запрос: {self.request}")
            self.game.set_skill_state('WAITING_SKILL_LEVEL')
            current_level = self.game.get_skill_level()
            return self.say(texts.set_skill_level_text.format(level=current_level))
        
        if self.intent_validator.validate_show_board():
            print(f"SpecialIntentHandler. validate_show_board. Запрос: {self.request}")
            text=self.game.get_board() + '\n'*2 + 'FEN: ' + self.game.board.fen()
            text_tts = 'Показала доску в чате.'
            return self.say(text, tts=text_tts)    
        
        return None