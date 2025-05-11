import texts
from speaker import Speaker


class TextPreparer(object):
    """
    Class for prepare text for show and text for speak from text.py
    """

    def __init__(self):
        self.speaker = Speaker()

    def say_do_not_get(self, command_text, attempt=0):
        not_get = texts.not_get_move.format(command_text)
        not_get_tts = not_get
        return not_get, not_get_tts

    def say_your_move(self, comp_move='', prev_turn='', text_to_show='', text_to_say='', lang='ru'):
        # form speech for your move

        print(f"say_your_move received: comp_move={comp_move}, prev_turn={prev_turn}, text_to_show={text_to_show}, text_to_say={text_to_say}")  # Отладочный вывод

        text = text_to_show if text_to_show else ''
        text_tts = text_to_say if text_to_say else ''

        move_to_say = self.speaker.say_move(comp_move, lang) if comp_move else ''
        prev_turn_tts = self.speaker.say_turn(prev_turn, lang) if prev_turn else ''

        if prev_turn:
            # if previous turn was given
            text_tts += f'{prev_turn_tts} пошли '
            text += f'\n{prev_turn_tts} пошли '
        if comp_move:
            # if comp move was given
            text += f'{comp_move}. '
            text_tts += f'{move_to_say}. '

        text += '\nВаш ход!'
        text_tts += 'Ваш ход!'

        return text, text_tts

    @staticmethod
    def say_repeat_last_move(self,last_move):
        text = texts.repeat_last_move.format(last_move)
        text_tts = self.speaker.say_move(last_move)
        return text, text_tts

    def say_not_legal_move(self, user_move='', text_to_show='', text_to_say=''):

        text = text_to_show if text_to_show else ''
        text_tts = text_to_say if text_to_say else ''
        if user_move:
            text += texts.not_legal_move.format(user_move)
            user_move_tts = self.speaker.say_move(user_move)
            text_tts += texts.not_legal_move.format(user_move_tts)
        return text, text_tts

    @staticmethod
    def say_result(comp_move, comp_move_tts, reason, reason_tts,
                   prev_turn_tts):
        winner = ''
        if reason == '#':
            winner = 'Победили ' + prev_turn_tts

        text = texts.gameover_text.format(comp_move, '', reason_tts,
                                          winner)
        text_tts = texts.gameover_text.format(comp_move_tts, 'sil <[70]>',
                                              reason_tts, winner)

        return text, text_tts

    @staticmethod
    def say_choose_color():
        text = texts.choose_turn_text
        text_tts = text
        return text, text_tts

    @staticmethod
    def say_undo_unavailable():
        text = texts.undo_unavailable.strip()
        text_tts = text
        return text, text_tts

    @staticmethod
    def say_help_text():

        text = texts.help_text_intro
        text_tts = texts.help_text_intro

        text += texts.names_for_pieces.format('', '', '', '', '')
        text_tts += texts.names_for_pieces.format('sil <[70]>',
                                                  'sil <[60]>',
                                                  'sil <[60]>',
                                                  'sil <[60]>',
                                                  'sil <[60]>')

        text += texts.coord_rules.format('Слон d3')
        text_tts += texts.coord_rules.format('Слон дэ 3')

        text += texts.undo_unavailable
        text_tts += texts.undo_unavailable

        text += texts.engine_info
        text_tts += texts.engine_info

        return text, text_tts

    def say_ambiguous_move(self, moves):
        text = texts.ambiguous_move
        text_tts = texts.ambiguous_move
        for m in moves:
            text += f'{m}\n'
            text_tts += self.speaker.say_move(m)
        return text, text_tts