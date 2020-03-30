import unittest
from speaker import Speaker


class MyTestCase(unittest.TestCase):
    def setUp(self):
        self.speaker = Speaker()

    def test_empty(self):
        speak = self.speaker.say_move('', 'ru')
        self.assertEqual(speak, '')

    def test_simple_move(self):
        speak = self.speaker.say_move('a3', 'ru')
        self.assertEqual(speak, 'а 3')

    def test_simple_move_chek(self):
        speak = self.speaker.say_move('b3+', 'ru')
        self.assertEqual(speak, 'бэ 3 шах')

    def test_move_with_piece(self):
        speak = self.speaker.say_move('Nf3', 'ru')
        self.assertEqual(speak, 'Конь эф 3')

    def test_move_with_promotion(self):
        speak = self.speaker.say_move('c8Q', 'ru')
        self.assertEqual(speak, 'цэ 8 Ферзь')

    def test_move_with_file_from(self):
        speak = self.speaker.say_move('de3', 'ru')
        self.assertEqual(speak, 'дэ е 3')

    def test_move_with_file_from_and_promotion(self):
        speak = self.speaker.say_move('fg8Q+', 'ru')
        self.assertEqual(speak, 'эф же 8 Ферзь шах')

    def test_move_with_piece_and_file_from(self):
        speak = self.speaker.say_move('Rdf8', 'ru')
        self.assertEqual(speak, 'Ладья дэ эф 8')

    def test_move_with_piece_and_rank_from(self):
        speak = self.speaker.say_move('Bdf8', 'ru')
        self.assertEqual(speak, 'Слон дэ эф 8')

    def test_short_castling(self):
        speak = self.speaker.say_move('0-0', 'ru')
        self.assertEqual(speak, 'Короткая рокировка')

    def test_short_castling_OO(self):
        speak = self.speaker.say_move('O-O', 'ru')
        self.assertEqual(speak, 'Короткая рокировка')

    def test_long_castling_OOO(self):
        speak = self.speaker.say_move('O-O-O', 'ru')
        self.assertEqual(speak, 'Длинная рокировка')

    def test_long_castling(self):
        speak = self.speaker.say_move('0-0-0', 'ru')
        self.assertEqual(speak, 'Длинная рокировка')

    def test_short_castling_check(self):
        speak = self.speaker.say_move('0-0+', 'ru')
        self.assertEqual(speak, 'Короткая рокировка шах')

    def test_long_castling_mate(self):
        speak = self.speaker.say_move('0-0-0#', 'ru')
        self.assertEqual(speak, 'Длинная рокировка мат')

    def test_capture_with_piece(self):
        speak = self.speaker.say_move('Nxe5', 'ru')
        self.assertEqual(speak, 'Конь берёт е 5')

    def test_capture_with_piece_and_square_from(self):
        speak = self.speaker.say_move('Bf3xg4', 'ru')
        self.assertEqual(speak, 'Слон эф 3 берёт же 4')

    def test_capture_with_file_from(self):
        speak = self.speaker.say_move('exd6', 'ru')
        self.assertEqual(speak, 'е берёт дэ 6')

    def test_capture_with_piece_and_file_from(self):
        speak = self.speaker.say_move('Rdxh8', 'ru')
        self.assertEqual(speak, 'Ладья дэ берёт аш 8')

    def test_capture(self):
        speak = self.speaker.say_move('Bf3xa3', 'ru')
        self.assertEqual(speak, 'Слон эф 3 берёт а 3')

    def test_say_who(self):
        speak = self.speaker.say_turn('White', 'ru')
        self.assertEqual(speak, 'Белые')

    def test_say_reason(self):
        speak = self.speaker.say_reason('#', 'ru')
        self.assertEqual(speak, 'мат')


if __name__ == '__main__':
    unittest.main()
