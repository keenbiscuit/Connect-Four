from backend.app.game_state import COLUMNS, ROWS, GameState


def test_new_game_has_empty_board() -> None:
    game = GameState()

    assert len(game.board) == ROWS
    assert len(game.board[0]) == COLUMNS
    assert game.current_player == "RED"
    assert all(cell is None for row in game.board for cell in row)