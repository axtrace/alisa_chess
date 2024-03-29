hi_text = """
Давайте сыграем в шахматы вслепую.
Ходы объявляются устно.
Для начала игры скажите 'Да'
Если хотите узнать больше, скажите 'Помощь'
"""

help_text_intro = """
Навык Шахматы вслепую. Ходим по очереди.
Ходы называем в формате: фигура + только координаты клетки, куда ходим.
"""

undo_unavailable = """
Отменять ходы нельзя.
"""
engine_info = """
В качестве шахматного движка используется Stockfish 10.
Уровень сложности пока что всегда 1.
Но скоро я научусь играть лучше и можно будет менять уровень сложности.
"""

choose_turn_text = """
Начинаем игру. Вы будете играть за белых? Или за черных?
"""

dng_start_text = """
Простите, я вас не поняла.
Скажите 'Да', если хотите сыграть в шахматы вслепую.
Скажите 'Помощь', если нужна помощь.
Скажите 'Хватит', если хотите закрыть навык.
"""

not_get_turn_text = """
Простите, я вас не поняла.
Скажите 'Белые' или 'Черные', если хотите сыграть.
Скажите 'Помощь', если нужна помощь.
Скажите 'Хватит', если хотите закрыть навык.
"""

not_get_move = """
Простите, я не смогла понять ваш ход из фразы '{}'.
Повторите, пожалуйста.
Скажите 'Помощь', если возникают проблемы с распознаванием.
"""

names_for_files = """
Для облегчения понимания можно использовать имена вместо букв:
Анна{}, Борис{}, Цапля{}, Дмитрий{}, Елена{}, Федор{}, Женя{}, Шура
"""

names_for_pieces = """
Названия фигур{}: Король{}, Ферзь{}, Ладья{}, Слон{}, Конь.
Пешку можно не называть.
"""

coord_rules = """
После фигуры называйте только координаты финальной клетки.
Пример хода: '{}'
Фразу о взятии можно не произносить.
Для рокировки необходимо сказать: длинная рокировка или короткая рокировка.
"""

current_level_text = """
Чтобы узнать и изменить текущий уровень сложности, скажите 'Сложность'
"""

not_legal_move = """
Ход '{}' невозможен. Попробуйте ещё раз.
"""

gameover_text = """
{}
Игра окончена! {}
Результат: {}.
{}
Спасибо за игру!

Если хотите сыграть еще раз, заново запустите навык
"""
