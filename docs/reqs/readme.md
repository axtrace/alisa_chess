# Оглавление
- [Глоссарий](#glossary)
- [Проблема](#problem)
- [Решение](#solution)
- [Стейкхолдеры](#stakeholders)
- [Сущности предметной области](#er)
- [Бизнес-требования](#brq)
- [Контекстная диаграмма](#context-diagram)
- [Сценарии](#usecases)
- [Функциональные и нефункциональные требования](#fr_nfr)
- [Базовые тесты](#tests)

----

# <a name="glossary"></a> Глоссарий
* Алиса - Виртуальный голосовой помощник, созданный компанией Яндекс. 
Распознаёт естественную речь, имитирует живой диалог, даёт ответы на вопросы пользователя и, благодаря запрограммированным навыкам, решает прикладные задачи

# <a name="problem"></a> Проблема
Алиса (помощник Яндекса) не поддерживает возможность играть голосом в шахматы. Голосовые шахматы реализованы у конкурентов, например, Алексы.
При этом, с технической точки зрения реализация не должна быть сложной. 
Игра в шахматы может быть монетизируемой, но пока концепции монетизации не разработано.

# <a name="solution"></a> Решение
Реализовать навык для Алисы, с помощью которого можно играть в шахматы голосом. 
Навык должен быть доступен как на устройствах с экраном, так и без.
Использовать готовый шахматный движок. 
Поддержать один язык: русский. 

# <a name="stakeholders"></a> Стейкхолдеры
Основные классы стейкхолдеров и их интересы:
- Пользователь - кайфануть от игры
- Разработчик - кайфануть от рабочего кода
- Продакт-менеджер - кайфануть от наличия навыка

# <a name="er"></a> Сущности предметной области

# <a name="brq"></a> Бизнес-требования и ограничения
## User Stories
### US-1
Я, как пользователь, хочу сыграть с Алисой в шахматы голосом в сокращенной шахматной нотации по современным правилам шахмат ФИДЕ

### US-2
Я, как пользователь, хочу сыграть с Алисой в шахматы голосом без экрана, 
чтобы получить удовольствие от игры и развить свои навыки визуализации ситуации на шахматной доске в уме. 

### US-3
Я, как пользователь, хочу сыграть с Алисой в шахматы голосом с экраном, 
чтобы не затруднять мозг визуалиацией ситуации на шахматной доске. Команды отдаю голосом.

### US-4
Я, как создатель навыка, хочу, чтобы навык одновременно выдерживал до 100 партий, 
чтобы обеспечить хороший пользовательский опыт у достаточного количества игроков

## Constrains
### Constr-1
Время ответа навыка должно быть меньше 3 секунд. Ограничение от платформы навыков Алисы

# <a name="context-diagram"></a> Контекстная диаграмма
## C1
Нарисуем диаграмму уровня C1
```mermaid
    C4Context
      title System Context diagram for Alice Chess Skill
      Person(user, "User", "Игрок в шахматы")
      System(alice, "Yandex Alice", "Голосовой помощник от Яндекса")
      System(skill, "Chess skill", "Навык шахматы вслепую")

      Rel_D(user, alice, "Команды голосом")
      Rel_D(alice, skill, "Команды текстом, ходы")
      Rel_U(skill, alice, "Ответ на команды, ответные ходы, состояние игры")
      Rel_U(alice, user, "Озвучивание сообщений от навыка: ответы, ходы, состояния игры")

```
## C2
Больший интерес может представлять диаграмма уровня C2, отображающая разложение на модули
```mermaid
    C4Container
    title Container diagram for Alice Chess Skill
    Person(user, "User", "Игрок в шахматы")
    System(alice, "Yandex Alice", "Голосовой помощник от Яндекса")
    
    Container_Boundary(c1, "Skill") {
      Container(skill, "Chess Skill", "python", "Обработка команд, преобразование в нотацию, проксирование ходов шахматному движку, управление состоянием игры")
      Container(ce, "Chess Engine", "---", "Шахматный движок StockFish 10")
    }
    
     Rel(user, alice, "Команда", "голос")
     Rel(alice, skill, "Команда", "HTTPS")
     Rel(skill, ce, "Ход, запрос состояния", "code")
     Rel(ce, skill, "Ответный ход, состояние игры", "code")
     Rel(skill, alice, "Ответный ход, состояние игры", "HTTPS")
     Rel(alice, user, "Ответный ход, состояние игры", "голос")
     
```

# <a name="usecases"></a> Сценарии
## Диаграмма юзкейсов

## UC1: Поиграть
### Предусловия
### Постусловия
### Основной сценарий
### Альтернативные сценарии
tbd
Типы ходов:
- Обычный ход
- Невозможный ход
- Ход с двумя стартовыми вариантами
- Взятие фигуры соперника
- Превращение пешки
- Шах
- Мат

## UC2: Посмотреть текущую позицию на доске
tbd
## UC3: Отменить последний ход
tbd
## UC4: Сдаться
tbd

## UC5: Изменить уровень сложности - НЕ РЕАЛИЗОВАН
tbd

# <a name="fr_nfr"></a> Функциональные и нефункциональные требования
## Функциональные требования
FR-1: Преобразовывать входящий от Алисы текст в команды, понятные движку
tbd
FR-2: 
tbd

## Нефункциональные требования
NFR-1: Юзабилити
tbd



### Возможные состояния навыка
tbd

### Диаграммы последовательностей
#### Последовательность вызовов. Приветствие

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


# <a name="tests"></a> Базовые тесты

# <a name="links"></a> Ссылки
1. [Правила шахмат ФИДЕ](https://handbook.fide.com/chapter/E012018)
2. [Шахматые нотации](https://ru.wikipedia.org/wiki/Шахматная_нотация)
3. [Навык Шахматы вслепую на платформе диалогов Яндекса](https://dialogs.yandex.ru/developer/skills/2310188c-c404-4342-8bbe-d397f25d9de2/)
