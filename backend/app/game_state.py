ROWS = 6
COLUMNS = 7

class GameState:
    def __init__(self) -> None:
        self.board = [
            [None for _ in range(COLUMNS)]
        for _ in range(ROWS)]

        self.current_player = "RED"  # or "Yellow", depending on who starts