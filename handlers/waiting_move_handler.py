import texts
from .base_handler import BaseHandler
from move_extractor import MoveExtractor
from request_validators.intent_validator import IntentValidator
from text_preparer import TextPreparer
from speaker import Speaker

class WaitingMoveHandler(BaseHandler):
    """Обработчик состояния ожидания хода пользователя."""
    
    def __init__(self, game, request):
        super().__init__(game, request)
        self.move_ext = MoveExtractor()
        self.intent_validator = IntentValidator(request)
        self.text_preparer = TextPreparer()
        self.speaker = Speaker()


    def handle(self):
        """Обрабатывает запрос в состоянии ожидания хода."""
        print(f"WaitingMoveHandler. handle. Запрос: {self.request}")
        # Проверяем специальные команды
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

        # Обработка хода пользователя
        user_move, reason_type = self._handle_user_move()

        if not user_move:
            if reason_type == "NOT_DEFINED":
                command_text = self.request.get('request', {}).get('command', '')
                text, text_tts = self.text_preparer.say_do_not_get(command_text)
                return self.say(text, tts=text_tts)
        if reason_type == "INVALID":
            user_move_tts = self.speaker.say_move(user_move)
            text, text_tts = self.text_preparer.say_not_legal_move(user_move, user_move_tts)
            return self.say(text, tts=text_tts)
            
            
        # Проверяем состояние после хода пользователя
        game_state = self._check_game_state(user_move)
        if game_state:
            return game_state
            
        # Ход компьютера
        prev_turn = self.game.who()
        comp_move = self.game.comp_move()
        
        # Проверяем состояние после хода компьютера
        game_state = self._check_game_state(comp_move, user_move)
        if game_state:
            return game_state
            
        # Обычный ход
        text, text_tts = self.prep_text_to_say(comp_move, prev_turn, self.game.get_board(), '')
        return self.say(text, tts=text_tts)

    def _handle_user_move(self):
        """Обрабатывает ход пользователя.
        
        Returns:
            str: Ход пользователя или None, если ход некорректен
        """
        is_move_defined, user_move = self.move_ext.extract_move(self.request)
        if not is_move_defined:
            return None, "NOT_DEFINED"
        
        # if not self.game.is_valid_move(user_move):
        #     return user_move, "INVALID"
        
        # Делаем ход
        try:
            self.game.user_move(user_move)
        except ValueError:
            return user_move, "INVALID"
        
        print(f"WaitingMoveHandler. _handle_user_move. Ход сделан: {user_move}")
        return user_move

    def _check_game_state(self, current_move, previous_move=None):
        """Проверяет состояние игры после хода.
        
        Args:
            current_move: Текущий ход
            previous_move: Предыдущий ход (опционально)
            
        Returns:
            str: Ответ с описанием состояния или None, если игра продолжается
        """
        # Проверяем на мат
        if self.game.is_checkmate():
            self.game.set_skill_state('GAME_OVER')
            text, text_tts = self.prep_text_to_say(current_move, previous_move, self.game.get_board(), '')
            return self.say(text + texts.checkmate_text, tts=text_tts)
            
        # Проверяем на пат
        if self.game.is_stalemate():
            self.game.set_skill_state('GAME_OVER')
            text, text_tts = self.prep_text_to_say(current_move, previous_move, self.game.get_board(), '')
            return self.say(text + texts.stalemate_text, tts=text_tts)
            
        # Проверяем на шах
        if self.game.is_check():
            text, text_tts = self.prep_text_to_say(current_move, previous_move, self.game.get_board(), '')
            return self.say(text + texts.check_text, tts=text_tts)
            
        # Проверяем на превращение пешки
        if self.game.is_promotion():
            self.game.set_skill_state('WAITING_PROMOTION')
            if previous_move:  # Если это ход компьютера
                text, text_tts = self.prep_text_to_say(current_move, previous_move, self.game.get_board(), '')
                return self.say(text + texts.promotion_text, tts=text_tts)
            return self.say(texts.promotion_text)
            
        return None

    def prep_text_to_say(self, current_move, prev_turn, text_to_show, text_to_say, lang='ru'):
        """Подготавливает текст для озвучивания хода.
        
        Args:
            current_move: Текущий ход
            previous_move: Предыдущий ход
            text_to_show: Текст для отображения
            text_to_say: Текст для озвучивания
            lang: Язык озвучивания
        """
        move_to_say = self.speaker.say_move(current_move, lang) if current_move else ''
        prev_turn_tts = self.speaker.say_turn(prev_turn, lang) if prev_turn else ''
        text, text_tts = self.text_preparer.say_your_move(current_move, move_to_say, prev_turn, prev_turn_tts, text_to_show, text_to_say)
        return text, text_tts 