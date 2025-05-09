import texts
from .base_handler import BaseHandler
from move_extractor import MoveExtractor


class WaitingPromotionHandler(BaseHandler):
    """Обработчик состояния ожидания превращения пешки."""
    
    def __init__(self, game, request):
        super().__init__(game, request)
        self.move_ext = MoveExtractor()

    def handle(self):
        """Обрабатывает запрос в состоянии ожидания превращения пешки."""
        print(f"WaitingPromotionHandler. handle. Запрос: {self.request}")
        is_promotion_defined, promotion = self.move_ext.extract_promotion(self.request)
        if not is_promotion_defined:
            return self.say(texts.not_get_turn_text)
            
        # Делаем превращение
        self.game.promote_pawn(promotion)
        
        # Делаем ход компьютера
        comp_move = self.game.comp_move()
        
        # Проверяем на шах и мат после хода компьютера
        if self.game.is_checkmate():
            self.game.set_skill_state('GAME_OVER')
            text, text_tts = self.prep_text_to_say(comp_move, '', self.game.get_board(), '')
            return self.say(text + texts.checkmate_text, tts=text_tts)
            
        # Проверяем на пат после хода компьютера
        if self.game.is_stalemate():
            self.game.set_skill_state('GAME_OVER')
            text, text_tts = self.prep_text_to_say(comp_move, '', self.game.get_board(), '')
            return self.say(text + texts.stalemate_text, tts=text_tts)
            
        # Проверяем на шах после хода компьютера
        if self.game.is_check():
            text, text_tts = self.prep_text_to_say(comp_move, '', self.game.get_board(), '')
            return self.say(text + texts.check_text, tts=text_tts)
            
        # Проверяем на превращение пешки после хода компьютера
        if self.game.is_promotion():
            self.game.set_skill_state('WAITING_PROMOTION')
            text, text_tts = self.prep_text_to_say(comp_move, '', self.game.get_board(), '')
            return self.say(text + texts.promotion_text, tts=text_tts)
            
        # Обычный ход
        text, text_tts = self.prep_text_to_say(comp_move, '', self.game.get_board(), '')
        return self.say(text, tts=text_tts)

    def prep_text_to_say(self, comp_move, prev_turn, text_to_show, text_to_say, lang='ru'):
        """Подготавливает текст для озвучивания хода."""
        move_to_say = self.speaker.say_move(comp_move, lang) if comp_move else ''
        prev_turn_tts = self.speaker.say_turn(prev_turn, lang) if prev_turn else ''
        text, text_tts = self.text_preparer.say_your_move(comp_move, move_to_say, prev_turn, prev_turn_tts, text_to_show, text_to_say)
        return text, text_tts 