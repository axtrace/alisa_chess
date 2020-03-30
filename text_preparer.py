import texts


class TextPreparer(object):
    """
    Class for prepare text for show and text for speak from text.py
    """

    def init(self):
        pass

    @staticmethod
    def say_do_not_get(command_text, attempt):
        not_get = texts.not_get_move.format(command_text)
        not_get_tts = not_get
        # if attempt % 3 == 1:
        #     # every N case try to remember of
        #     not_get += texts.names_for_files.format('', '', '', '', '', '', '')
        #     not_get_tts += texts.names_for_files.format('sil <[60]>',
        #                                                 'sil <[60]>',
        #                                                 'sil <[60]>',
        #                                                 'sil <[60]>',
        #                                                 'sil <[60]>',
        #                                                 'sil <[60]>',
        #                                                 'sil <[60]>')
        #     not_get += texts.names_for_pieces.format('', '', '', '', '')
        #     not_get_tts += texts.names_for_pieces.format('sil <[70]>',
        #                                                  'sil <[60]>',
        #                                                  'sil <[60]>',
        #                                                  'sil <[60]>',
        #                                                  'sil <[60]>')
        #
        #     not_get += texts.coord_rules.format('Слон d3')
        #     not_get_tts += texts.coord_rules.format('Слон дэ 3')
        return not_get, not_get_tts

    @staticmethod
    def say_your_move(comp_move='', move_to_say='', prev_turn='',
                      prev_turn_tts='', text_to_show='', text_to_say=''):
        # form speech for your move

        text = text_to_show if text_to_show else ''
        tts = text_to_say if text_to_say else ''
        if prev_turn:
            # if previous turn was given
            tts += f'{prev_turn_tts} пошли '
            text += f'{prev_turn_tts} пошли '
        if comp_move:
            # if comp move was given
            # move_to_say = speaker.say_move(comp_move, 'ru')
            text += f'{comp_move}. '
            tts += f'{move_to_say}. '

        text += 'Ваш ход!'
        tts += 'Ваш ход!'

        return text, tts

    @staticmethod
    def say_not_legal_move(user_move, say_user_move):
        text = texts.not_legal_move.format(user_move)
        tts = texts.not_legal_move.format(say_user_move)
        return text, tts

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
    def say_hi_text(move, move_tts):
        text = texts.choose_turn_text
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

        text += texts.undo_available
        text_tts += texts.undo_available

        text += texts.engine_info
        text_tts += texts.engine_info

        # text += texts.current_level_text.format(level)
        # text_tts += texts.current_level_text.format(level)

        return text, text_tts
