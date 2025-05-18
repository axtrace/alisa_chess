```mermaid
classDiagram
    class AliceChess {
        -Game game
        -Speaker speaker
        -TextPreparer text_preparer
        +handle_request(request)
        +set_game_state(skill_state)
        +get_game_state()
    }

    class Game {
        -ChessEngineAPI engine
        -Board board
        -int skill_level
        -float time_level
        -str winner
        -str skill_state
        -str prev_skill_state
        -str user_color
        +get_user_color()
        +set_user_color(user_color)
        +get_skill_state()
        +set_skill_state(skill_state)
        +get_prev_skill_state()
        +restore_prev_state()
        +user_move(move_san)
        +comp_move()
        +unmake_move()
        +is_game_over()
        +is_move_legal(move)
        +set_skill_level(skill_level)
        +get_skill_level()
        +who()
        +get_board()
        +gameover_reason()
        +reset_board()
        +serialize_state()
        +get_last_move()
        +is_valid_move(move_san)
        +is_checkmate()
        +is_stalemate()
        +is_check()
        +is_insufficient_material()
        +is_fivefold_repetition()
    }

    class ChessEngineAPI {
        -str api_url
        -str api_key
        +get_best_move(fen, depth, time)
    }

    class Speaker {
        -dict piece_names
        -dict letters_for_pronunciation
        -dict check
        -dict mate
        -dict checkmate_names
        -dict captures_names
        -dict promotions_names
        -dict castling_names
        -dict white_black_names
        -dict gameover_reasons
        +say_move(move_san, lang)
        +say_turn(who, lang)
        +say_reason(reason, lang)
    }

    class TextPreparer {
        -Speaker speaker
        +say_help_text()
        +say_ambiguous_move(moves)
    }

    class BaseHandler {
        <<abstract>>
        #Game game
        #Speaker speaker
        #TextPreparer text_preparer
        +handle()
    }

    class SpecialIntentHandler {
        +handle()
    }

    class InitiatedHandler {
        +handle()
    }

    class WaitingConfirmHandler {
        +handle()
    }

    class WaitingColorHandler {
        +handle()
    }

    class WaitingMoveHandler {
        +handle()
        -_check_game_state(current_move, prev_turn)
    }

    class WaitingPromotionHandler {
        +handle()
    }

    class WaitingDrawConfirmHandler {
        +handle()
    }

    class WaitingResignConfirmHandler {
        +handle()
    }

    class GameOverHandler {
        +handle()
    }

    class WaitingNewgameConfirmHandler {
        +handle()
    }

    class WaitingSkillLevelHandler {
        +handle()
    }

    class MoveExtractor {
        -dict piece_map
        +_extract_move_from_text(request)
        +_find_matching_moves(board, move_structure)
    }

    %% Связи между классами
    AliceChess --> Game : содержит
    AliceChess --> Speaker : содержит
    AliceChess --> TextPreparer : содержит
    AliceChess --> BaseHandler : использует

    Game --> ChessEngineAPI : использует

    TextPreparer --> Speaker : использует

    BaseHandler --> Game : использует
    BaseHandler --> Speaker : использует
    BaseHandler --> TextPreparer : использует

    SpecialIntentHandler --|> BaseHandler : наследует
    InitiatedHandler --|> BaseHandler : наследует
    WaitingConfirmHandler --|> BaseHandler : наследует
    WaitingColorHandler --|> BaseHandler : наследует
    WaitingMoveHandler --|> BaseHandler : наследует
    WaitingPromotionHandler --|> BaseHandler : наследует
    WaitingDrawConfirmHandler --|> BaseHandler : наследует
    WaitingResignConfirmHandler --|> BaseHandler : наследует
    GameOverHandler --|> BaseHandler : наследует
    WaitingNewgameConfirmHandler --|> BaseHandler : наследует
    WaitingSkillLevelHandler --|> BaseHandler : наследует

    AliceChess --> MoveExtractor : использует
} 