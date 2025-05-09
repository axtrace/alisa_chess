from game import Game
from chess import Board
from speaker import Speaker
from text_preparer import TextPreparer
from handlers.initiated_handler import InitiatedHandler
from handlers.waiting_confirm_handler import WaitingConfirmHandler
from handlers.waiting_color_handler import WaitingColorHandler
from handlers.waiting_move_handler import WaitingMoveHandler
from handlers.waiting_promotion_handler import WaitingPromotionHandler
from handlers.waiting_draw_confirm_handler import WaitingDrawConfirmHandler
from handlers.waiting_resign_confirm_handler import WaitingResignConfirmHandler
from handlers.game_over_handler import GameOverHandler
from handlers.special_intent_handler import SpecialIntentHandler
from handlers.waiting_newgame_confirm_handler import WaitingNewgameConfirmHandler

class AliceChess:
    """Основной класс для обработки запросов к навыку шахмат."""
    
    def __init__(self, event):
        # Инициализируем игру по состоянию из event или создаем новую
        self._build_game(event)
        self.speaker = Speaker()
        self.text_preparer = TextPreparer()

    def _build_game(self, event):
        """Инициализирует игру по состоянию из event или создает новую.
        
        Args:
            event: Данные запроса
        """
        if 'state' in event and 'user' in event['state'] and 'game_state' in event['state']['user']:
            print(f"Восстанавливаем состояние из: {event['state']['user']['game_state']}")
            self.game = Game.parse_and_build_game(event['state']['user']['game_state'])
            print(f"Состояние восстановлено: {self.game.serialize_state()}")
        else:
            print("Создаем новую игру")
            self.game = Game(board=Board())
    
    def get_game_state(self):
        if self.game is None:
            return ""
        return self.game.serialize_state()
        
    def handle_request(self, request):
        """Обрабатывает входящий запрос.
        
        Args:
            request: Данные запроса
        """

        print(f"handle_request. Запрос: {request}")

        # Сначала проверяем специальные интенты, не зависящие от состояния
        handler = SpecialIntentHandler(self.game, request)
        result = handler.handle()
        if result:
            return result
            
        # Затем обрабатываем запрос в зависимости от состояния игры
        state = self.game.get_skill_state()
        
        if state in ['INITIATED', '']: 
            handler = InitiatedHandler(self.game, request)
        elif state == 'WAITING_CONFIRM':
            handler = WaitingConfirmHandler(self.game, request)
        elif state == 'WAITING_COLOR':
            handler = WaitingColorHandler(self.game, request)
        elif state == 'WAITING_MOVE':
            handler = WaitingMoveHandler(self.game, request)
        elif state == 'WAITING_PROMOTION':
            handler = WaitingPromotionHandler(self.game, request)
        elif state == 'WAITING_DRAW_CONFIRM':
            handler = WaitingDrawConfirmHandler(self.game, request)
        elif state == 'WAITING_RESIGN_CONFIRM':
            handler = WaitingResignConfirmHandler(self.game, request)
        elif state == 'WAITING_NEWGAME_CONFIRM':
            handler = WaitingNewgameConfirmHandler(self.game, request)
        elif state == 'GAME_OVER':
            handler = GameOverHandler(self.game, request)
        else:
            raise ValueError(f"Неизвестное состояние игры: {state}")
            
        return handler.handle()
