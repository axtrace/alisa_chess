Нарисуем диаграмки для облегчения понимания, чего же делает наш скилл.

# Последовательность вызовов. Приветствие

Рассмотрим диаграмму последовательностей вызовов при обработке поступившего зарпоса. 
Указаны основные моменты обработки запроса без детализации по классам.

```mermaid
sequenceDiagram

  autonumber
  
  actor user as User
  participant yd as "Yandex Dialogs"
  participant chess as "Chess skill" 
  
  loop
    user ->> yd: request
    yd ->> chess: request + intents
    %% alice_chess_skill -> alice_chess_skill: processRequest()
    alt request is help
      chess  -->> yd: say_help()
      yd -->> user: say_help()
    else state == ''
      chess -> chess: game.set_skill_state('SAY_YES')
      chess  -->> yd: say_hi()
      yd -->> user: say_hi()
    else state == 'SAY_YES'
      chess -> chess: game.set_skill_state('SAY_CHOOSE_COLOR')
    else state == 'SAY_CHOOSE_COLOR'
      chess -> chess: game.set_skill_state('CHOOSE_COLOR')
      chess  -->> yd: say_choose_color()
      yd -->> user: say_choose_color()
    else state == 'CHOOSE_COLOR'
      alt is_color_define == True
          chess -> chess: game.set_user_color(user_color)
          chess -> chess: game.set_skill_state('NOTIFY_STEP')
      else NOT is_color_define
           chess  -->> Yandex_Dialogs: say_not_get_turn
           yd -->> user: say_not_get_turn()
      end
    else state == 'NOTIFY_STEP'
      opt user color == 'BLACK' && was no attempts
       chess -> chess: game.comp_move()
      end
      loop NOT gameover
        chess  -->> yd: comp_move + board
        yd -->> user: comp_move + board
        user -> yd: request
        yd -->> chess: request + intents
        alt move is legal
            chess -> chess: game.user_move()
        else NOT move is legal
            chess -->> yd: say_not_legal_move()
            yd -->> user: say_not_legal_move()
        end
      end
     chess -->> yd: game_result + board
     yd -->> user:  game_result + board
    end
  end
```

Следующим шагом видится переработка кода + детализация схемы по вызываемым классам
