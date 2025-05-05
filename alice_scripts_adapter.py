def say(text, tts=None, end_session=False):
    """
    Adapter function to match Yandex.Alice response format.
    :param text: Text to display
    :param tts: Text to speak (TTS)
    :param end_session: Whether to end the session
    :return: Response dictionary in Yandex.Alice format
    """
    return {
        'text': text,
        'tts': tts if tts is not None else text,
        'end_session': end_session,
        'buttons': []
    } 