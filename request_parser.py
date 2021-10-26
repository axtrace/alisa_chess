class RequestParser(object):
    """
    Class for parse and extract some part from Requests
    """

    def __init__(self, request):
        self.request = request
        self.intents = self.get_intents()

    def is_unmake(self):
        return self.request.has_intents('UNDO')

    def is_help(self):
        # define if user asked help
        help_lemmas = ['помощь', 'умеешь']
        return self.has_intents(['YANDEX.HELP', 'YANDEX.WHAT_CAN_YOU_DO']) or self.request.has_lemmas(*help_lemmas)

    def is_yes(self):
        # define if user confirm flow
        yes_lemmas = ['да', 'давай', 'ага', 'угу', 'yes', 'yeh', 'ok',
                      'ок', 'поехали', 'старт']
        return self.has_intents(['YANDEX.CONFIRM']) or self.request.has_lemmas(*yes_lemmas)

    def has_lemmas(self, lemma):
        return self.request.has_lemmas(lemma)

    def get_castling(self):
        if self.has_intents(['SHORT_CASTLING']):
            return 'O-O'
        elif self.has_intents(['LONG_CASTLING']):
            return 'O-O-O'
        elif self.has_intents(['CASTLING']):
            # todo: return flag and try to find some castling in possible moves
            return None
        return None

    def get_command(self):
        return self.request.get('request', {}).get('command', {})

    def get_intents(self):
        return self.request.get('request', {}).get('nlu', {}).get('intents', {})

    def has_intents(self, intent_list):
        # intents is not empty and then intersect i
        # t with incoming list as a sets
        # returns false in case when both lists are empty but let it be
        return self.intents and bool(set(self.intents) & set(intent_list))

    def get_entities(self):
        # todo somewhere
        pass
