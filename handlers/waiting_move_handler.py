import texts
from .base_handler import BaseHandler
from move_extractor import MoveExtractor
from request_validators.intent_validator import IntentValidator
from text_preparer import TextPreparer
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class WaitingMoveHandler(BaseHandler):
    """Обработчик состояния ожидания хода пользователя."""
    
    def __init__(self, game, request):
        super().__init__(game, request)
        self.move_ext = MoveExtractor()
        self.intent_validator = IntentValidator(request)
        self.text_preparer = TextPreparer()

    def handle(self):
        """Обрабатывает запрос в состоянии ожидания хода."""
        logger.info(f"WaitingMoveHandler.handle. Запрос: {self.request}")
        
        user_color = self.game.get_user_color()

        # Обработка и выполнение хода пользователя
        user_moves, reason_type = self._handle_user_move()

        # Если вернулась какая-то причина, то обрабатываем её (ход некорректен)
        if reason_type != "OK":
            logger.info(f"WaitingMoveHandler.handle. reason_type: {reason_type}")
            return self._reason_handler(reason_type, user_moves) 
        
        # Если причина не вернулась и вернулся список ходов, то выбираем первый
        if isinstance(user_moves, list):
            user_move = user_moves[0]
        else:
            user_move = user_moves

        # Если игра после хода ПОЛЬЗОВАТЕЛЯ закончилась, то говорим об этом
        game_state = self._check_game_state(current_move=user_move, prev_turn=user_color)
        if game_state:
            return game_state
            
        # Делаем один ход компьютера
        comp_color = self.game.who() # who возвращает сторону, которая делает ход. До хода компьютера - это и есть сторона компьютера
        comp_move = self.game.comp_move()
        
        # Если игра после хода КОМПЬЮТЕРА закончилась, то говорим об этом
        game_state = self._check_game_state(current_move=comp_move, prev_turn=comp_color)
        if game_state:
            return game_state
            
        # Озвучиваем ход компьютера
        text, text_tts = self.prep_text_to_say(comp_move=comp_move, prev_turn=comp_color, text_to_show=self.game.get_board() + '\nВаш ход!', text_to_say='. Ваш ход!')
        return self.say(text, tts=text_tts)

    def _handle_user_move(self):
        """Обрабатывает ход пользователя.
        
        Returns:
            str: Ход пользователя или None, если ход некорректен
        """
        matching_moves, extracted_move = self.move_ext.extract_move(self.request, self.game.board)
        
        if extracted_move is None:
            return None, "NOT_DEFINED"
        elif not matching_moves:
            return extracted_move, "INVALID"
        elif len(matching_moves) > 1:
            return matching_moves, "AMBIGUOUS"
        
        user_move = matching_moves[0]
              
        # Делаем ход
        try:
            self.game.user_move(user_move)
        except ValueError:
            return user_move, "INVALID"
        
        logger.info(f"WaitingMoveHandler._handle_user_move. Ход сделан: {user_move}")
        return user_move, "OK"

    def _check_game_state(self, current_move, prev_turn=''):
        """Проверяет состояние игры после хода.
        
        Args:
            current_move: Текущий ход
            previous_move: Предыдущий ход (опционально)
            
        Returns:
            str: Ответ с описанием состояния или None, если игра продолжается
        """
        # Проверяем на недостаточность материала
        if self.game.is_insufficient_material():
            self.game.set_skill_state('GAME_OVER')
            text, text_tts = self.prep_text_to_say(comp_move=current_move, prev_turn=prev_turn, text_to_show=self.game.get_board(), text_to_say='')
            text += '\n' + texts.insufficient_material_text
            text_tts += '\n' + texts.insufficient_material_text_tts
            return self.say(text, tts=text_tts)
        
        # Проверяем на пятикратное повторение
        if self.game.is_fivefold_repetition():
            self.game.set_skill_state('GAME_OVER')
            text, text_tts = self.prep_text_to_say(comp_move=current_move, prev_turn=prev_turn, text_to_show=self.game.get_board(), text_to_say='')
            text += '\n' + texts.fivefold_repetition_text
            text_tts += '\n' + texts.fivefold_repetition_text
            return self.say(text, tts=text_tts)
        
        # Проверяем на мат
        if self.game.is_checkmate():
            self.game.set_skill_state('GAME_OVER')
            text, text_tts = self.prep_text_to_say(comp_move=current_move, prev_turn=prev_turn, text_to_show=self.game.get_board(), text_to_say='')
            text += '\n' + texts.checkmate_text
            text_tts += '\n' + texts.checkmate_text
            text_tts = '<speaker audio=\"alice-sounds-game-win-1.opus\">' + text_tts
            return self.say(text, tts=text_tts)
            
        # Проверяем на пат
        if self.game.is_stalemate():
            self.game.set_skill_state('GAME_OVER')
            text, text_tts = self.prep_text_to_say(comp_move=current_move, prev_turn=prev_turn, text_to_show=self.game.get_board(), text_to_say='')
            text += '\n' + texts.stalemate_text
            text_tts += '\n' + texts.stalemate_text
            return self.say(text, tts=text_tts)
            
        return None
    
    def _unmake_handler(self):
        """Обрабатывает отмену последнего хода."""
        if self.game.undo_move():
            text, text_tts = self.text_preparer.say_your_move('', '', '', '', self.game.get_board(), '')
            return self.say(text, tts=text_tts)
        return self.say(texts.cant_unmake_text)
    

    def _reason_handler(self, reason_type, user_move):
        """Обрабатывает причину некорректного хода."""
        logger.info(f"WaitingMoveHandler._reason_handler. reason_type: {reason_type}, user_move: {user_move}")
        if reason_type == "NOT_DEFINED":
            command_text = self.request.get('request', {}).get('command', '')
            text, text_tts = self.text_preparer.say_do_not_get(command_text=command_text)
            return self.say(text, tts=text_tts)
        if reason_type == "INVALID":
            text, text_tts = self.text_preparer.say_not_legal_move(user_move=user_move)
            return self.say(text, tts=text_tts)
        if reason_type == "AMBIGUOUS":
            text, text_tts = self.text_preparer.say_ambiguous_move(moves=user_move)

            return self.say(text, tts=text_tts) 
            