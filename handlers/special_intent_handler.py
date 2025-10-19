import logging

import texts
from move_extractor import MoveExtractor
from request_validators.intent_validator import IntentValidator
from skill_state import SkillState
from tts_builder import TtsBuilder

from .base_handler import BaseHandler

logger = logging.getLogger(__name__)


class SpecialIntentHandler(BaseHandler):
    """Обработчик специальных намерений."""

    def __init__(self, game, request):
        super().__init__(game, request)
        self.move_ext = MoveExtractor()
        self.intent_validator = IntentValidator(request)
        # Реестр: (имя_валидатора, имя_метода_обработчика).
        # Порядок важен — проверяем интенты в этой последовательности.
        self._intent_registry = [
            ('validate_new_session', self._handle_new_session),
            ('validate_help', self._handle_help),
            ('validate_whatcanyoudo', self._handle_whatcanyoudo),
            ('validate_new_game', self._handle_new_game),
            ('validate_draw', self._handle_draw),
            ('validate_resign', self._handle_resign),
            ('validate_undo', self._handle_undo),
            ('validate_repeat', self._handle_repeat),
            ('validate_repeat_last_move', self._handle_repeat_last_move),
            ('validate_set_skill_level', self._handle_set_skill_level),
            ('validate_get_skill_level', self._handle_get_skill_level),
            ('validate_show_board', self._handle_show_board),
        ]

    def handle(self):
        logger.info(f'SpecialIntentHandler. handle. Проверяем запрос: {self.request}')
        for validator_name, handler_method in self._intent_registry:
            validator = getattr(self.intent_validator, validator_name, None)
            if validator is None:
                logger.warning(f'SpecialIntentHandler. Валидатор {validator_name} не найден в IntentValidator')
                continue
            if validator():
                logger.info(f'SpecialIntentHandler. {validator_name}. Запрос: {self.request}')
                return handler_method()
        return None

    def _handle_new_session(self):
        # Если пользователь начал новую сессию, то проверяем, не ждём ли мы хода с предыдущей сессии
        if self.game.get_skill_state() == SkillState.WAITING_MOVE:
            # Если в первом запросе новой сессии уже пришёл ход — не показываем приветственное
            # сообщение, а сразу передаём управление штатному WaitingMoveHandler, чтобы применить ход.
            if self._has_move_in_request():
                return None
            # Если ждём, то показываем доску и предыдущий ход
            last_move = self.game.get_last_move()
            comp_color = self.game.get_comp_color()
            if last_move:
                text, text_tts = self.prep_text_to_say(
                    comp_move=last_move, prev_turn=comp_color, text_to_show=self.game.get_board(), text_to_say=''
                )
                text = texts.resume_text + '\n' + text + '\nВаш ход!'
                text_tts = texts.resume_text + '\n' + text_tts + '\nВаш ход!'
            else:
                text = texts.resume_text + '\n' + self.game.get_board() + '\nВаш ход!'
                text_tts = (
                    texts.resume_text
                    + '\n'
                    + TtsBuilder.with_silence_suffix('Показала доску на экране.')
                    + '\nВаш ход!'
                )
            return self.say(text, tts=text_tts)
        if self.game.get_skill_state() == SkillState.WAITING_SKILL_LEVEL:
            state_text = texts.state_texts.get(self.game.get_skill_state(), '')
            state_text = state_text.format(self.game.get_skill_level())
            return self.say(state_text)
        return None

    def _has_move_in_request(self) -> bool:
        """Возвращает True, если в запросе пользователя есть распознаваемый шахматный ход.

        Используется для случая, когда новая сессия открывается сразу с ходом
        (player продолжает партию и присылает ход в первом же запросе).
        """
        try:
            _, extracted_move = self.move_ext.extract_move(self.request, self.game.board)
        except Exception as e:
            logger.warning(f'SpecialIntentHandler._has_move_in_request. Ошибка извлечения хода: {e}')
            return False
        return extracted_move is not None

    def _handle_help(self):
        state_text = texts.state_texts.get(self.game.get_skill_state(), '')
        engine_info = texts.engine_info.format(self.game.get_engine_name(), self.game.get_skill_level())
        return self.say(texts.help_text + '\n' + engine_info + '\n' + state_text)

    def _handle_whatcanyoudo(self):
        return self.say(texts.what_can_you_do_text)

    def _handle_new_game(self):
        self.game.set_skill_state(SkillState.WAITING_NEWGAME_CONFIRM)
        return self.say(texts.waiting_newgame_confirm_text)

    def _handle_draw(self):
        self.game.set_skill_state(SkillState.WAITING_DRAW_CONFIRM)
        return self.say(texts.waiting_draw_confirm_text)

    def _handle_resign(self):
        self.game.set_skill_state(SkillState.WAITING_RESIGN_CONFIRM)
        return self.say(texts.waiting_resign_confirm_text)

    def _handle_undo(self):
        if self.game.undo_move():
            comp_color = self.game.get_comp_color()
            text, text_tts = self.prep_text_to_say(
                comp_move='', prev_turn=comp_color, text_to_show=self.game.get_board(), text_to_say=''
            )
            text = texts.undo_text + '\n' + text
            text_tts = texts.undo_text + '\n' + text_tts
            return self.say(text, tts=text_tts)
        else:
            return self.say(texts.no_undo_text)

    def _handle_repeat(self):
        prev_response = self.request.get('state', {}).get('session', {}).get('previous_response', {})
        # Проверяем, что previous_response содержит корректную структуру
        if isinstance(prev_response, dict) and 'text' in prev_response:
            return prev_response
        # Если previous_response некорректен, возвращаем сообщение об ошибке
        return self.say('Не могу повторить предыдущее сообщение. Попробуйте другой запрос.')

    def _handle_repeat_last_move(self):
        last_move = self.game.get_last_move()
        comp_color = self.game.get_comp_color()
        if last_move:
            text, text_tts = self.prep_text_to_say(
                comp_move=last_move, prev_turn=comp_color, text_to_show=self.game.get_board(), text_to_say=''
            )
            return self.say(text, tts=text_tts)
        return self.say(texts.no_moves_text)

    def _handle_set_skill_level(self):
        self.game.set_skill_state(SkillState.WAITING_SKILL_LEVEL)
        current_level = self.game.get_skill_level()
        return self.say(texts.waiting_skill_level_text.format(current_level))

    def _handle_get_skill_level(self):
        current_level = self.game.get_skill_level()
        return self.say(texts.get_skill_level_text.format(current_level))

    def _handle_show_board(self):
        last_move = self.game.get_last_move()
        comp_color = self.game.get_comp_color()
        add_text = self.game.get_board() + '\n' * 2 + 'FEN: ' + self.game.board.fen() + '\n'
        text, text_tts = self.prep_text_to_say(
            comp_move=last_move,
            prev_turn=comp_color,
            text_to_show=add_text,
            text_to_say=TtsBuilder.with_silence_suffix('Показала доску в чате.'),
        )
        return self.say(text, tts=text_tts)
