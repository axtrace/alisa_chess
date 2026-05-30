import logging

from game import Game
from handlers.game_over_handler import GameOverHandler
from handlers.initiated_handler import InitiatedHandler
from handlers.special_intent_handler import SpecialIntentHandler
from handlers.waiting_color_handler import WaitingColorHandler
from handlers.waiting_confirm_handler import WaitingConfirmHandler
from handlers.waiting_draw_confirm_handler import WaitingDrawConfirmHandler
from handlers.waiting_move_handler import WaitingMoveHandler
from handlers.waiting_newgame_confirm_handler import WaitingNewgameConfirmHandler
from handlers.waiting_resign_confirm_handler import WaitingResignConfirmHandler
from handlers.waiting_skill_level_handler import WaitingSkillLevelHandler
from skill_state import SkillState

logger = logging.getLogger(__name__)


class AliceChess:
    """Основной класс для обработки запросов к навыку шахмат."""

    def __init__(self):
        self.game = Game()
        self.session_state = {}

    def __enter__(self):
        """Контекстный менеджер для делегирования Game."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Гарантированное закрытие Game при выходе из контекста."""
        if hasattr(self, 'game') and self.game is not None:
            self.game.quit()
        return False  # Не подавляем исключения

    def set_game_state(self, skill_state):
        if self.game is not None:
            self.game.set_skill_state(skill_state)
        return None

    def get_game_state(self):
        if self.game is None:
            return ''
        return self.game.serialize_state()

    def get_session_state(self):
        """Возвращает накопленное session_state для записи в ответ Алисе."""
        return self.session_state

    def handle_request(self, request):
        """Обрабатывает входящий запрос.

        Args:
            request: Входящий запрос от Алисы.

        Returns:
            Ответ для Алисы.
        """

        logger.info(f'handle_request. Запрос: {request}')

        # Проверка идемпотентности по message_id
        current_message_id = request.get('session', {}).get('message_id')
        session_state = request.get('state', {}).get('session', {})
        last_message_id = session_state.get('last_message_id')

        if current_message_id and last_message_id and current_message_id == last_message_id:
            logger.info(f'Идемпотентность: пропускаем дублирующий запрос message_id={current_message_id}')
            # Возвращаем предыдущий ответ из session_state
            previous_response = session_state.get('previous_response', {})
            if previous_response:
                return previous_response
            else:
                return {'text': 'Повторный запрос пропущен', 'tts': 'Повторный запрос пропущен', 'end_session': False}

        state = request.get('state', {}).get('user', {}).get('game_state', {})

        self.game = Game(game_state=state)

        # Сначала проверяем специальные интенты, не зависящие от состояния
        special_intent_handler = SpecialIntentHandler(self.game, request)
        special_intent_result = special_intent_handler.safe_handle()
        if special_intent_result:
            self.session_state = {
                'last_message_id': current_message_id,
                'previous_response': special_intent_result,
            }
            return special_intent_result

        # Затем обрабатываем запрос в зависимости от состояния игры
        state = self.game.get_skill_state()

        if state in (SkillState.INITIATED, ''):
            handler = InitiatedHandler(self.game, request)
        elif state == SkillState.WAITING_CONFIRM:
            handler = WaitingConfirmHandler(self.game, request)
        elif state == SkillState.WAITING_COLOR:
            handler = WaitingColorHandler(self.game, request)
        elif state == SkillState.WAITING_MOVE:
            handler = WaitingMoveHandler(self.game, request)
        elif state == SkillState.WAITING_DRAW_CONFIRM:
            handler = WaitingDrawConfirmHandler(self.game, request)
        elif state == SkillState.WAITING_RESIGN_CONFIRM:
            handler = WaitingResignConfirmHandler(self.game, request)
        elif state == SkillState.WAITING_NEWGAME_CONFIRM:
            handler = WaitingNewgameConfirmHandler(self.game, request)
        elif state == SkillState.GAME_OVER:
            handler = GameOverHandler(self.game, request)
        elif state == SkillState.WAITING_SKILL_LEVEL:
            handler = WaitingSkillLevelHandler(self.game, request)
        else:
            raise ValueError(f'Неизвестное состояние игры: {state}')

        handler_result = handler.safe_handle()

        self.session_state = {
            'last_message_id': current_message_id,
            'previous_response': handler_result,
        }
        return handler_result
