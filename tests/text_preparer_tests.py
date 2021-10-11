import unittest
from text_preparer import TextPreparer


class MyTestCase(unittest.TestCase):
    def setUp(self):
        self.tp = TextPreparer()

    def test_say_not_legal_move(self):
        res, res_tts = self.tp.say_not_legal_move('Nf3', 'Конь эф 3')
        self.assertEqual(res, "\nХод 'Nf3' невозможен. Попробуйте ещё раз.\n")
        self.assertEqual(res_tts,
                         "\nХод 'Конь эф 3' невозможен. Попробуйте ещё раз.\n")

    def test_say_your_move(self):
        res, res_tts = self.tp.say_your_move('Nf3', 'Конь эф 3')
        self.assertEqual(res, "Nf3. Ваш ход!")
        self.assertEqual(res_tts, "Конь эф 3. Ваш ход!")

    def test_help(self):
        help_tts_expected = """
Навык Шахматы вслепую. Ходим по очереди. 
Ходы называем в формате: фигура + только координаты клетки, куда ходим.

Названия фигурsil <[70]>: Корольsil <[60]>, Ферзьsil <[60]>, Ладьяsil <[60]>, Слонsil <[60]>, Конь.
Пешку можно не называть. 

После фигуры называйте только координаты финальной клетки. 
Пример хода: 'Слон дэ 3'
Фразу о взятии можно не произносить.
Для рокировки необходимо сказать: длинная рокировка или короткая рокировка.

Отменять ходы нельзя.

В качестве шахматного движка используется Stockfish 10.
Уровень сложности пока что всегда 1. 
Но скоро я научусь играть лучше и можно будет менять уровень сложности.
        """
        res, res_tts = self.tp.say_help_text()
        self.assertEqual(help_tts_expected.strip(), res_tts.strip())


if __name__ == '__main__':
    unittest.main()
