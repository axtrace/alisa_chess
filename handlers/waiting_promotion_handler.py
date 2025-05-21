import texts
from .base_handler import BaseHandler
from move_extractor import MoveExtractor
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class WaitingPromotionHandler(BaseHandler):
    """Обработчик состояния ожидания превращения пешки."""
    
    def __init__(self, game, request):
        super().__init__(game, request)
        self.move_ext = MoveExtractor()

    def handle(self):
        """Обрабатывает запрос в состоянии ожидания превращения пешки."""
        logger.info(f"WaitingPromotionHandler. handle. Запрос: {self.request}") 
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
            
        # Проверяем на превращение пешки после хода компьютера
        if self.game.is_promotion():
            self.game.set_skill_state('WAITING_PROMOTION')
            text, text_tts = self.prep_text_to_say(comp_move, '', self.game.get_board(), '')
            return self.say(text + texts.promotion_text, tts=text_tts)
            
        # Обычный ход
        text, text_tts = self.prep_text_to_say(comp_move, '', self.game.get_board(), '')
        return self.say(text, tts=text_tts)