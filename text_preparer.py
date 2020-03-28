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
        if attempt % 3 == 1:
            # every N case try to remember of
            not_get += texts.names_for_files.format('', '', '', '', '', '', '')
            not_get_tts += texts.names_for_files.format('sil <[60]>',
                                                        'sil <[60]>',
                                                        'sil <[60]>',
                                                        'sil <[60]>',
                                                        'sil <[60]>',
                                                        'sil <[60]>',
                                                        'sil <[60]>')
        return not_get, not_get_tts

    @staticmethod
    def say_your_move(comp_move='', move_to_say='', prev_turn='',
                      prev_turn_tts='', text_to_show='', text_to_say=''):
        # form speech for your move

        text = text_to_show + '. ' if text_to_show else ''
        tts = text_to_say + '. ' if text_to_say else ''
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
            winner = ' Победили ' + prev_turn_tts

        text = f'{comp_move}. Игра окончена!'
        text_tts = f'{comp_move_tts}. Игра окончена! sil <[70]>'

        text += f' Результат: {reason_tts}.{winner}'
        text_tts += f' Результат: {reason_tts}.{winner}'

        # text += f''
        text_tts += f' Спасибо за игру!'

        text += f' Если хотите сыграть еще раз, заново запустите навык'
        text_tts += f' Если хотите сыграть еще раз, заново запустите навык'

        return text, text_tts

    @staticmethod
    def say_hi_text(move, move_tts):
        text = texts.hi_turn_text.format('', '', '', '', '',
                                         move) + texts.choose_turn_text
        text_tts = texts.hi_turn_text.format('sil <[70]>', 'sil <[60]>',
                                             'sil <[60]>', 'sil <[60]>',
                                             'sil <[60]>',
                                             move_tts) + texts.choose_turn_text
        return text, text_tts

    @staticmethod
    def say_help_text(move, move_tts):
        text = texts.help_text.format('', '', '', '', '',
                                      move) + texts.choose_turn_text
        text_tts = texts.help_text.format('sil <[70]>', 'sil <[60]>',
                                          'sil <[60]>', 'sil <[60]>',
                                          'sil <[60]>',
                                          move_tts) + texts.choose_turn_text
        return text, text_tts
