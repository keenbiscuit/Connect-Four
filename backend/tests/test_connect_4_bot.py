
from backend.app.game_state import RED, GameState
from backend.app.services.bot_decision import choose_column


def test_choose_center_column_on_initial_board():
    
    game = GameState()
    
    column = choose_column(game)
    assert column == 3
    

def test_choose_column_skips_full_center_column():
    game = GameState()

    # Simulate the center column being full
    for _ in range(6):
        game.board[_][3] = RED

    column = choose_column(game)
    assert column == 2
    
    

def test_choose_column_chooses_next_preferred_column():
    game = GameState()

    # Simulate the center and adjacent columns being full
    for _ in range(6):
        game.board[_][2] = RED
        game.board[_][3] = RED

    column = choose_column(game)
    assert column == 4
    

def test_choose_column_does_not_mutate_board():
    game = GameState()

    board_copy = []
    for row in game.board:
        board_copy.append(row.copy())

    choose_column(game)
    assert game.board == board_copy

   