import texts
from .base_handler import BaseHandler
from move_extractor import MoveExtractor
from request_validators.intent_validator import IntentValidator 
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class SpecialIntentHandler(BaseHandler):
    """Обработчик специальных намерений."""

    def __init__(self, game, request):
        super().__init__(game, request)
        self.move_ext = MoveExtractor()
        self.intent_validator = IntentValidator(request)

    def handle(self):
        # Проверяем специальные намерения, которые не зависят от состояния игры
        logger.info(f"SpecialIntentHandler. handle. Проверяем запрос: {self.request}")
        if self.intent_validator.validate_new_session():
            # Если пользователь хочет начать новую игру, то проверяем, была ли предыдущая игра
            logger.info(f"SpecialIntentHandler. validate_new_session. Запрос: {self.request}")
            state_text = texts.state_texts.get(self.game.get_skill_state(), '')
            state = self.request.get('state',{}).get('user',{}).get('game_state', {})
            if state:
                # Если была предыдущая игра, то показываем доску и предыдущий ход
                last_move = self.game.get_last_move()
                comp_color = 'WHITE' if self.game.get_user_color() == 'BLACK' else 'BLACK'
                if last_move:
                    text, text_tts = self.prep_text_to_say(comp_move=last_move, prev_turn=comp_color, text_to_show=self.game.get_board(), text_to_say='')
                    text = texts.resume_text + '\n' + text
                else:
                    text = texts.resume_text + '\n' + self.game.get_board()
                    text_tts = texts.resume_text + '\n' + 'Показала доску в чате. sil <[60]>'
                return self.say(text, tts=text_tts)
            else:
                return self.say(texts.hi_text)
        
        if self.intent_validator.validate_help():
            logger.info(f"SpecialIntentHandler. validate_help. Запрос: {self.request}")
            state_text = texts.state_texts.get(self.game.get_skill_state(), '')
            return self.say(texts.help_text + '\n' + state_text)
        
        if self.intent_validator.validate_whatcanyoudo():
            logger.info(f"SpecialIntentHandler. validate_whatcanyoudo. Запрос: {self.request}")
            return self.say(texts.what_can_you_do_text)
        
        if self.intent_validator.validate_new_game():
            logger.info(f"SpecialIntentHandler. validate_new_game. Запрос: {self.request}")
            self.game.set_skill_state('WAITING_NEWGAME_CONFIRM')
            return self.say(texts.waiting_newgame_confirm_text)
            
        if self.intent_validator.validate_draw():
            logger.info(f"SpecialIntentHandler. validate_draw. Запрос: {self.request}")
            self.game.set_skill_state('WAITING_DRAW_CONFIRM')
            return self.say(texts.waiting_draw_confirm_text)
            
        if self.intent_validator.validate_resign():
            logger.info(f"SpecialIntentHandler. validate_resign. Запрос: {self.request}")
            self.game.set_skill_state('WAITING_RESIGN_CONFIRM')
            return self.say(texts.waiting_resign_confirm_text)
        
        if self.intent_validator.validate_undo():
            logger.info(f"SpecialIntentHandler. validate_undo. Запрос: {self.request}")
            if self.game.undo_move():
                comp_color = 'WHITE' if self.game.get_user_color() == 'BLACK' else 'BLACK'
                text, text_tts = self.prep_text_to_say(comp_move='', prev_turn=comp_color, text_to_show=self.game.get_board(), text_to_say='')
                text = texts.undo_text + '\n' + text
                text_tts = texts.undo_text + '\n' + text_tts
                return self.say(text, tts=text_tts)
            else:
                return self.say(texts.no_undo_text)
        
        if self.intent_validator.validate_repeat():
            logger.info(f"SpecialIntentHandler. validate_repeat. Запрос: {self.request}")
            prev_response = self.request.get('state',{}).get('session',{}).get('previous_response',{})
            return prev_response
        
        if self.intent_validator.validate_repeat_last_move():
            logger.info(f"SpecialIntentHandler. validate_repeat_last_move. Запрос: {self.request}")
            
            last_move = self.game.get_last_move()
            comp_color = 'WHITE' if self.game.get_user_color() == 'BLACK' else 'BLACK'

            if last_move:
                text, text_tts = self.prep_text_to_say(comp_move=last_move, prev_turn=comp_color, text_to_show=self.game.get_board(), text_to_say='')
                return self.say(text, tts=text_tts)
            else:
                text = texts.no_moves_text
                return self.say(text)
        
        if self.intent_validator.validate_set_skill_level():
            logger.info(f"SpecialIntentHandler. validate_set_skill_level. Запрос: {self.request}")
            self.game.set_skill_state('WAITING_SKILL_LEVEL')
            current_level = self.game.get_skill_level()
            return self.say(texts.waiting_skill_level_text.format(current_level))
        
        if self.intent_validator.validate_get_skill_level():
            logger.info(f"SpecialIntentHandler. validate_get_skill_level. Запрос: {self.request}")
            current_level = self.game.get_skill_level()
            return self.say(texts.get_skill_level_text.format(current_level))
        
        if self.intent_validator.validate_show_board():
            logger.info(f"SpecialIntentHandler. validate_show_board. Запрос: {self.request}")
            last_move = self.game.get_last_move()
            comp_color = 'WHITE' if self.game.get_user_color() == 'BLACK' else 'BLACK'
            add_text = self.game.get_board() + '\n'*2 + 'FEN: ' + self.game.board.fen() + '\n'
            text, text_tts = self.prep_text_to_say(comp_move=last_move, prev_turn=comp_color, text_to_show=add_text, text_to_say='Показала доску в чате. sil <[60]>')
            return self.say(text, tts=text_tts)    
        
        return None