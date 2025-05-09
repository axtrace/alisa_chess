import texts
from .base_handler import BaseHandler
from move_extractor import MoveExtractor


class WaitingColorHandler(BaseHandler):
    """Обработчик состояния ожидания выбора цвета."""
    
    def __init__(self, game, request):
        super().__init__(game, request)
        self.move_ext = MoveExtractor()

    def handle(self):
        """Обрабатывает запрос в состоянии ожидания выбора цвета."""
        print(f"WaitingColorHandler. handle. Запрос: {self.request}")
        is_color_defined, user_color = self.move_ext.extract_color(self.request)
        if not is_color_defined:
            return self.say(texts.not_get_turn_text)
            
        self.game.set_user_color(user_color)
        self.game.set_skill_state('WAITING_MOVE')
        
        # Если пользователь играет черными, делаем первый ход
        if user_color == 'BLACK':
            prev_turn = self.game.who()
            prev_turn = ''
            comp_move = self.game.comp_move()
            text, text_tts = self.prep_text_to_say(comp_move, prev_turn, self.game.get_board(), '')
            return self.say(text, tts=text_tts)
            
        text, text_tts = self.text_preparer.say_your_move('', '', '', '', self.game.get_board(), '')
        return self.say(text, tts=text_tts)

    def prep_text_to_say(self, comp_move, prev_turn, text_to_show, text_to_say, lang='ru'):
        """Подготавливает текст для озвучивания хода."""
        move_to_say = self.speaker.say_move(comp_move, lang) if comp_move else ''
        prev_turn_tts = self.speaker.say_turn(prev_turn, lang) if prev_turn else ''
        text, text_tts = self.text_preparer.say_your_move(comp_move, move_to_say, prev_turn, prev_turn_tts, text_to_show, text_to_say)
        return text, text_tts 