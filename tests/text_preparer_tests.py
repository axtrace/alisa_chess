import unittest
from text_preparer import TextPreparer


class MyTestCase(unittest.TestCase):
    def setUp(self):
        self.tp = TextPreparer()

    def test_something(self):
        res, res_tts = self.tp.say_not_legal_move('Nf3', 'Конь эф 3')
        self.assertEqual(res, '\nХод Nf3 невозможен. Попробуйте ещё раз.\n')
        self.assertEqual(res_tts, '\nХод Конь эф 3 невозможен. Попробуйте ещё раз.\n')


if __name__ == '__main__':
    unittest.main()
