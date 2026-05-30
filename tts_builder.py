"""TTS-разметка Алисы.

Модуль централизованно хранит SSML-конструкции, специфичные для Алисы
(`sil <[N]>`, `<speaker audio="...">`, `accent+` и т. п.), и предоставляет
билдер для их применения в текстах TTS. Хендлеры и `text_preparer`/`speaker`
должны использовать эти helper'ы вместо инлайн-литералов.

Документация: https://yandex.ru/dev/dialogs/alice/doc/speech-tuning.html
"""

from __future__ import annotations


class TtsBuilder:
    """Хелперы для построения TTS-разметки Алисы."""

    # Звуки из библиотеки Алисы.
    SOUND_GAME_WIN = "alice-sounds-game-win-1.opus"

    # Длительности пауз в сантисекундах.
    PAUSE_SHORT = 60
    PAUSE_MEDIUM = 70
    PAUSE_LONG = 100

    @staticmethod
    def silence(centiseconds: int = PAUSE_SHORT) -> str:
        """Возвращает SSML-паузу заданной длительности (в сантисекундах)."""
        return f"sil <[{centiseconds}]>"

    @staticmethod
    def speaker(audio: str) -> str:
        """Возвращает SSML-тег воспроизведения звука из библиотеки Алисы."""
        return f'<speaker audio="{audio}">'

    @classmethod
    def with_silence_suffix(cls, text: str, centiseconds: int = PAUSE_SHORT) -> str:
        """Добавляет паузу в конец текста."""
        return f"{text} {cls.silence(centiseconds)}"

    @classmethod
    def with_sound_prefix(cls, audio: str, text: str) -> str:
        """Добавляет звук в начало текста."""
        return f"{cls.speaker(audio)}{text}"
