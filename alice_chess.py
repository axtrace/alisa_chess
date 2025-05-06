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


app = Flask(__name__)


class AliceChess:
    """Основной класс для обработки запросов к навыку шахмат."""
    
    def __init__(self):
        self.game = Game()
        self.speaker = Speaker()
        self.text_preparer = TextPreparer()
        
    def handle_request(self, request):
        """Обрабатывает входящий запрос."""
        state = self.game.get_skill_state()
        
        # Выбираем обработчик в зависимости от состояния
        if state == 'INITIATED':
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


@app.route('/alice', methods=['POST'])
def alice():
    """Обработчик POST-запросов от Алисы."""
    request_json = request.get_json()
    alice_chess = AliceChess()
    response = alice_chess.handle_request(request_json)
    return response


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

