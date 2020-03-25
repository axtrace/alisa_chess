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
        self.assertEqual(speak, 'а3')

    def test_move_with_piece(self):
        speak = self.speaker.say_move('Nf3', 'ru')
        self.assertEqual(speak, 'Конь f3')

    def test_short_castling(self):
        speak = self.speaker.say_move('0-0', 'ru')
        self.assertEqual(speak, 'Короткая рокировка')

    def test_long_castling(self):
        speak = self.speaker.say_move('0-0-0', 'ru')
        self.assertEqual(speak, 'Длинная рокировка')

    def test_caputure(self):
        speak = self.speaker.say_move('Bf3xa3', 'ru')
        self.assertEqual(speak, 'Конь берёт а3')

    def test_caputure(self):
        speak = self.speaker.say_move('Bf3xa3', 'ru')
        self.assertEqual(speak, 'Конь берёт а3')

if __name__ == '__main__':
    unittest.main()
