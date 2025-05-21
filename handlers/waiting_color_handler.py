import texts
from .base_handler import BaseHandler
from move_extractor import MoveExtractor
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class WaitingColorHandler(BaseHandler):
    """Обработчик состояния ожидания выбора цвета."""
    
    def __init__(self, game, request):
        super().__init__(game, request)
        self.move_ext = MoveExtractor()

    def handle(self):
        """Обрабатывает запрос в состоянии ожидания выбора цвета."""
        logger.info(f"WaitingColorHandler. handle. Запрос: {self.request}") 
        is_color_defined, user_color = self.move_ext.extract_color(self.request)
        if not is_color_defined:
            return self.say(texts.not_get_turn_text)
            
        self.game.set_user_color(user_color)
        self.game.set_skill_state('WAITING_MOVE')
        
        # Если пользователь играет черными, делаем первый ход
        if user_color == 'BLACK':
            # prev_turn = self.game.who()
            comp_color = 'WHITE'
            comp_move = self.game.comp_move()
            text, text_tts = self.prep_text_to_say(comp_move=comp_move, prev_turn=comp_color, text_to_show=self.game.get_board(), text_to_say='')
            return self.say(text, tts=text_tts)
            
        text, text_tts = self.prep_text_to_say(comp_move='', prev_turn='', text_to_show=self.game.get_board(), text_to_say='')
        return self.say(text, tts=text_tts)