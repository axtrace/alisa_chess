import texts
from .base_handler import BaseHandler
from move_extractor import MoveExtractor
from request_validators.intent_validator import IntentValidator


class WaitingMoveHandler(BaseHandler):
    """Обработчик состояния ожидания хода пользователя."""
    
    def __init__(self, game, request):
        super().__init__(game, request)
        self.move_ext = MoveExtractor()
        self.intent_validator = IntentValidator(request)

    def handle(self):
        """Обрабатывает запрос в состоянии ожидания хода."""
        # Проверяем специальные намерения
        if self.intent_validator.validate_help():
            return self.say(texts.help_text)
            
        if self.intent_validator.validate_new_game():
            self.game.set_skill_state('INITIATED')
            return self.say(texts.hi_text)
            
        if self.intent_validator.validate_draw():
            self.game.set_skill_state('WAITING_DRAW_CONFIRM')
            return self.say(texts.draw_offer_text)
            
        if self.intent_validator.validate_resign():
            self.game.set_skill_state('WAITING_RESIGN_CONFIRM')
            return self.say(texts.resign_offer_text)
            
        if self.intent_validator.validate_unmake():
            if self.game.unmake_move():
                text, text_tts = self.text_preparer.say_your_move('', '', '', '', self.game.get_board(), '')
                return self.say(text, tts=text_tts)
            return self.say(texts.cant_unmake_text)
            
        if self.intent_validator.validate_repeat_last_move():
            last_move = self.game.get_last_move()
            if last_move:
                text = f"Последний ход: {last_move}"
                text_tts = self.speaker.say_move(last_move)
                board_printed = self.game.get_board()
                return self.say(board_printed + text, tts=text_tts)
            return self.say("Пока не было сделано ни одного хода.")

        # Проверяем ход
        is_move_defined, user_move = self.move_ext.extract_move(self.request)
        if not is_move_defined:
            return self.say(texts.not_get_turn_text)
            
        # Проверяем корректность хода
        if not self.game.is_valid_move(user_move):
            return self.say(texts.wrong_turn_text)
            
        # Делаем ход
        self.game.user_move(user_move)
        
        # Проверяем на шах и мат
        if self.game.is_checkmate():
            self.game.set_skill_state('GAME_OVER')
            text, text_tts = self.text_preparer.say_your_move(user_move, '', '', '', self.game.get_board(), '')
            return self.say(text + texts.checkmate_text, tts=text_tts)
            
        # Проверяем на пат
        if self.game.is_stalemate():
            self.game.set_skill_state('GAME_OVER')
            text, text_tts = self.text_preparer.say_your_move(user_move, '', '', '', self.game.get_board(), '')
            return self.say(text + texts.stalemate_text, tts=text_tts)
            
        # Проверяем на шах
        if self.game.is_check():
            text, text_tts = self.text_preparer.say_your_move(user_move, '', '', '', self.game.get_board(), '')
            return self.say(text + texts.check_text, tts=text_tts)
            
        # Проверяем на превращение пешки
        if self.game.is_promotion():
            self.game.set_skill_state('WAITING_PROMOTION')
            return self.say(texts.promotion_text)
            
        # Делаем ход компьютера
        comp_move = self.game.comp_move()
        
        # Проверяем на шах и мат после хода компьютера
        if self.game.is_checkmate():
            self.game.set_skill_state('GAME_OVER')
            text, text_tts = self.prep_text_to_say(comp_move, user_move, self.game.get_board(), '')
            return self.say(text + texts.checkmate_text, tts=text_tts)
            
        # Проверяем на пат после хода компьютера
        if self.game.is_stalemate():
            self.game.set_skill_state('GAME_OVER')
            text, text_tts = self.prep_text_to_say(comp_move, user_move, self.game.get_board(), '')
            return self.say(text + texts.stalemate_text, tts=text_tts)
            
        # Проверяем на шах после хода компьютера
        if self.game.is_check():
            text, text_tts = self.prep_text_to_say(comp_move, user_move, self.game.get_board(), '')
            return self.say(text + texts.check_text, tts=text_tts)
            
        # Проверяем на превращение пешки после хода компьютера
        if self.game.is_promotion():
            self.game.set_skill_state('WAITING_PROMOTION')
            text, text_tts = self.prep_text_to_say(comp_move, user_move, self.game.get_board(), '')
            return self.say(text + texts.promotion_text, tts=text_tts)
            
        # Обычный ход
        text, text_tts = self.prep_text_to_say(comp_move, user_move, self.game.get_board(), '')
        return self.say(text, tts=text_tts)

    def prep_text_to_say(self, comp_move, prev_turn, text_to_show, text_to_say, lang='ru'):
        """Подготавливает текст для озвучивания хода."""
        move_to_say = self.speaker.say_move(comp_move, lang) if comp_move else ''
        prev_turn_tts = self.speaker.say_turn(prev_turn, lang) if prev_turn else ''
        text, text_tts = self.text_preparer.say_your_move(comp_move, move_to_say, prev_turn, prev_turn_tts, text_to_show, text_to_say)
        return text, text_tts 