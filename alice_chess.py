from flask import Flask, request
from game import Game
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



class AliceChess:
    """Основной класс для обработки запросов к навыку шахмат."""
    
    def __init__(self, game: Game):
        """Инициализирует обработчик запросов.
        
        Args:
            game: Экземпляр игры
        """
        self.game = game
        self.speaker = Speaker()
        self.text_preparer = TextPreparer()
        
    def handle_request(self, request):
        """Обрабатывает входящий запрос.
        
        Args:
            request: Данные запроса
        """
        state = self.game.get_skill_state()
        
        # Выбираем обработчик в зависимости от состояния
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
        elif state == 'GAME_OVER':
            handler = GameOverHandler(self.game, request)
        else:
            raise ValueError(f"Неизвестное состояние: {state}")
            
        return handler.handle()
