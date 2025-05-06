from alice_scripts_adapter import say

import texts
from game import Game
from move_extractor import MoveExtractor
from speaker import Speaker
from text_preparer import TextPreparer


class AliceChess:
    """Класс для обработки шахматного навыка Алисы."""
    
    def __init__(self, game: Game, request):
        self.game = game
        self.request = request
        self.move_ext = MoveExtractor()
        self.speaker = Speaker()
        print(f"AliceChess initialized with game: {self.game} and request: {self.request}")

    def process_request(self):
        """Обрабатывает входящий запрос и возвращает ответ."""
        print(f"Processing request. Command: {self.request.get('request', {}).get('command')}, state: {self.game.get_skill_state()}")
        
        # Получаем текущее состояние
        state = self.game.get_skill_state()
        
        # Обработка в зависимости от состояния
        if state in ['INITIATED', '']:
            return self._handle_initiated()
        elif state == 'WAITING_CONFIRM':
            return self._handle_waiting_confirm()
        elif state == 'WAITING_COLOR':
            return self._handle_waiting_color()
        elif state == 'WAITING_MOVE':
            return self._handle_waiting_move()
        elif state == 'WAITING_PROMOTION':
            return self._handle_waiting_promotion()
        elif state == 'GAME_OVER':
            return self._handle_game_over()
            
        # Если состояние не определено, начинаем сначала
        return self._handle_initiated()

    def _handle_initiated(self):
        """Обработка начального состояния."""
        self.game.set_skill_state('WAITING_CONFIRM')
        return say(texts.hi_text, tts=texts.hi_text)

    def _handle_waiting_confirm(self):
        """Обработка ожидания подтверждения начала игры."""
        if not self.is_request_yes():
            return say(texts.dng_start_text)
            
        self.game.set_skill_state('WAITING_COLOR')
        text, text_tts = TextPreparer.say_choose_color()
        return say(text, tts=text_tts)

    def _handle_waiting_color(self):
        """Обработка ожидания выбора цвета."""
        is_color_defined, user_color = self.move_ext.extract_color(self.request)
        if not is_color_defined:
            return say(texts.not_get_turn_text)
            
        self.game.set_user_color(user_color)
        self.game.set_skill_state('WAITING_MOVE')
        
        # Если пользователь играет черными, делаем первый ход
        if user_color == 'BLACK':
            prev_turn = self.game.who()
            comp_move = self.game.comp_move()
            text, text_tts = self.prep_text_to_say(comp_move, prev_turn, self.game.get_board(), '')
            return say(text, tts=text_tts)
            
        # Если белыми, ждем ход пользователя
        text, text_tts = TextPreparer.say_your_move('', '', 'WHITE', '', self.game.get_board(), '')
        return say(text, tts=text_tts)

    def _handle_waiting_move(self):
        """Обработка ожидания хода пользователя."""
        # Проверяем, не просит ли пользователь отменить ход
        if self.is_request_unmake():
            return say(texts.undo_unavailable_text)
            
        # Извлекаем ход из запроса
        move = self.move_ext.extract_move(self.request)
        if not move:
            return say(texts.not_get_move_text)
            
        # Проверяем легальность хода
        if not self.game.is_move_legal(move):
            text, text_tts = TextPreparer.say_not_legal_move(move, self.speaker.say_move(move))
            text += self.game.get_board()
            return say(text, tts=text_tts)
            
        # Делаем ход пользователя
        prev_turn = self.game.who()
        self.game.user_move(move)
        
        # Проверяем, не нужно ли превращение пешки
        if self.game.needs_promotion():
            self.game.set_skill_state('WAITING_PROMOTION')
            text, text_tts = TextPreparer.say_choose_promotion()
            return say(text, tts=text_tts)
            
        # Проверяем, не закончилась ли игра
        if self.game.is_game_over():
            self.game.set_skill_state('GAME_OVER')
            return self._handle_game_over()
            
        # Делаем ход компьютера
        prev_turn = self.game.who()
        comp_move = self.game.comp_move()
        
        # Формируем ответ
        text, text_tts = self.prep_text_to_say(comp_move, prev_turn, self.game.get_board(), '')
        return say(text, tts=text_tts)

    def _handle_waiting_promotion(self):
        """Обработка ожидания выбора фигуры для превращения пешки."""
        piece = self.move_ext._get_piece_(self.request)
        if not piece or piece not in ['Q', 'R', 'B', 'N']:
            return say(texts.not_get_promotion_text)
            
        self.game.promote_pawn(piece)
        self.game.set_skill_state('WAITING_MOVE')
        
        # Проверяем, не закончилась ли игра
        if self.game.is_game_over():
            self.game.set_skill_state('GAME_OVER')
            return self._handle_game_over()
            
        # Делаем ход компьютера
        prev_turn = self.game.who()
        comp_move = self.game.comp_move()
        
        # Формируем ответ
        text, text_tts = self.prep_text_to_say(comp_move, prev_turn, self.game.get_board(), '')
        return say(text, tts=text_tts)

    def _handle_game_over(self):
        """Обработка завершенной игры."""
        reason = self.game.gameover_reason()
        board_printed = self.game.get_board()
        text, text_tts = TextPreparer.say_result('', '', reason,
                                               self.speaker.say_reason(reason, 'ru'),
                                               '')
        return say(board_printed + text, tts=text_tts, end_session=True)

    def prep_text_to_say(self, comp_move, prev_turn, text_to_show, text_to_say, lang='ru'):
        """Подготавливает текст для озвучивания хода."""
        move_to_say = self.speaker.say_move(comp_move, lang) if comp_move else ''
        prev_turn_tts = self.speaker.say_turn(prev_turn, lang) if prev_turn else ''
        text, text_tts = TextPreparer.say_your_move(comp_move, move_to_say, prev_turn, prev_turn_tts, text_to_show,
                                                    text_to_say)
        return text, text_tts

    def is_request_yes(self):
        """Проверяет, является ли запрос подтверждением."""
        if self._has_intent('YANDEX.CONFIRM'):
            return True
        confirm_words = ['да', 'yes', 'ок', 'ok', 'давай']
        return self._has_text(confirm_words)

    def is_request_unmake(self):
        """Проверяет, является ли запрос отменой хода."""
        if self._has_intent('YANDEX.UNMAKE'):
            return True
        unmake_words = ['отмена', 'cancel', 'назад', 'back']
        return self._has_text(unmake_words)

    def _has_intent(self, intent_name):
        """Проверяет наличие интента в запросе."""
        if not all(key in self.request.get('request', {}) for key in ['nlu', 'intents']):
            return False
        return intent_name in self.request['request']['nlu']['intents']

    def _has_text(self, list_of_words):
        """Проверяет текстовое совпадение с словами."""
        command = self.request.get('request', {}).get('command', '').lower()
        return command in list_of_words

