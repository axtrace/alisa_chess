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
        print(f"SpecialIntentHandler. handle. Проверяем запрос: {self.request}")
        if self.intent_validator.validate_new_session():
            print(f"SpecialIntentHandler. validate_new_session. Запрос: {self.request}")
            state_text = texts.state_texts.get(self.game.get_skill_state(), '')
            state = self.request.get('state',{}).get('user',{}).get('game_state', {})
            if state:
                return self.say(texts.resume_text + '\n' + state_text)
            else:
                return self.say(texts.hi_text)
        
        if self.intent_validator.validate_help():
            print(f"SpecialIntentHandler. validate_help. Запрос: {self.request}")
            state_text = texts.state_texts.get(self.game.get_skill_state(), '')
            return self.say(texts.help_text + '\n' + state_text)
        
        if self.intent_validator.validate_new_game():
            print(f"SpecialIntentHandler. validate_new_game. Запрос: {self.request}")
            self.game.set_skill_state('WAITING_NEWGAME_CONFIRM')
            return self.say(texts.waiting_newgame_confirm_text)
            
        if self.intent_validator.validate_draw():
            print(f"SpecialIntentHandler. validate_draw. Запрос: {self.request}")
            self.game.set_skill_state('WAITING_DRAW_CONFIRM')
            return self.say(texts.waiting_draw_confirm_text)
            
        if self.intent_validator.validate_resign():
            print(f"SpecialIntentHandler. validate_resign. Запрос: {self.request}")
            self.game.set_skill_state('WAITING_RESIGN_CONFIRM')
            return self.say(texts.waiting_resign_confirm_text)
        
        if self.intent_validator.validate_unmake():
            print(f"SpecialIntentHandler. validate_unmake. Запрос: {self.request}")
            self.game.unmake_move()
            return self.say(texts.unmake_text)
        
        if self.intent_validator.validate_repeat_last_move():
            print(f"SpecialIntentHandler. validate_repeat_last_move. Запрос: {self.request}")
            
            last_move = self.game.get_last_move()
            comp_color = 'WHITE' if self.game.get_user_color() == 'BLACK' else 'BLACK'

            if last_move:
                text, text_tts = self.prep_text_to_say(comp_move=last_move, prev_turn=comp_color, text_to_show=self.game.get_board(), text_to_say='')
                return self.say(text, tts=text_tts)
            else:
                text = texts.no_moves_text
                return self.say(text)
        
        if self.intent_validator.validate_set_skill_level():
            print(f"SpecialIntentHandler. validate_set_skill_level. Запрос: {self.request}")
            self.game.set_skill_state('WAITING_SKILL_LEVEL')
            current_level = self.game.get_skill_level()
            return self.say(texts.waiting_skill_level_text.format(current_level))
        
        if self.intent_validator.validate_get_skill_level():
            print(f"SpecialIntentHandler. validate_get_skill_level. Запрос: {self.request}")
            current_level = self.game.get_skill_level()
            return self.say(texts.get_skill_level_text.format(current_level))
        
        if self.intent_validator.validate_show_board():
            print(f"SpecialIntentHandler. validate_show_board. Запрос: {self.request}")
            last_move = self.game.get_last_move()
            comp_color = 'WHITE' if self.game.get_user_color() == 'BLACK' else 'BLACK'
            add_text = self.game.get_board() + '\n'*2 + 'FEN: ' + self.game.board.fen() + '\n'
            text, text_tts = self.prep_text_to_say(comp_move=last_move, prev_turn=comp_color, text_to_show=add_text, text_to_say='Показала доску в чате')
            return self.say(text, tts=text_tts)    
        
        return None