
from backend.app.game_state import GameState


def choose_column(game: GameState) -> int | None:
    # Using preference order 3, 2, 4, 1, 5, 0, 6
    preference_order = [3, 2, 4, 1, 5, 0, 6]
    for column in preference_order:
        if not game.is_column_full(column):
            return column
    # If all columns are full, return -1 as an indicator (should not happen in a normal game)
    return None