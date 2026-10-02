# contains the GameState class representing the state of a Connect 4 game
from backend.app.models.move_result import MoveResult


ROWS = 6
COLUMNS = 7
EMPTY = 0
RED = 1
YELLOW = 2

class GameState:
    def __init__(self, starting_player: int = RED) -> None:
        self.board = [
            [EMPTY for _ in range(COLUMNS)]
            for _ in range(ROWS)
        ]

        self.status = "active" # can be "active", "win", or "draw"
        self.winner = None # can be RED, YELLOW, or None depending on the game outcome
        self.current_player = starting_player  # or YELLOW, depending on who starts
        self.starting_player = starting_player

    # Drop a piece into a column for the current player
    def drop_piece(self, column: int) -> MoveResult:

        # Post game guard
        if self.status != "active":
            return MoveResult(success=False,
                              column=column,
                              player=self.current_player,
                              row=None,
                              reason="game_finished",
                              status=self.status,
                              winner=self.winner)
        
        if not self.is_valid_column_index(column):
            return MoveResult(success=False,
                              column=column,
                              player=self.current_player,
                              row=None,
                              reason="invalid_column",
                              status=self.status,
                              winner=self.winner)

        # Check if the column is full before attempting to drop a piece
        if self.is_column_full(column):
            return MoveResult(success=False,
                              column=column,
                              player=self.current_player,
                              row=None,
                              reason="column_full",
                              status=self.status,
                              winner=self.winner)
        
        # Find the open row for the column
        row = self.find_open_row(column)
        assert row is not None, "No open row found for the column"

        # Place the current player's piece in the found open row
        self.board[row][column] = self.current_player

        # Check if the move resulted in a win
        win = self.check_win(row, column)
        if win:
            self.status = "win"
            self.winner = self.current_player
            result = MoveResult(
                success=True,
                column=column,
                player=self.current_player,
                row=row, reason=None,
                status=self.status,
                winner=self.winner)
            
        # If the game is not won, check for a draw next
        elif self.check_draw():
            self.status = "draw"
            self.winner = None
            result = MoveResult(success=True,
                                column=column,
                                player=self.current_player,
                                row=row,
                                reason=None,
                                status=self.status,
                                winner=self.winner)
            
        else:
            # Prepare the result of the move
            result = MoveResult(success=True,
                                column=column, 
                                player=self.current_player,
                                row=row, reason=None, 
                                status=self.status, 
                                winner=self.winner)
            # Switch to the other player for the next turn
            self.current_player = RED if self.current_player == YELLOW else YELLOW

        # Return the result of the move, including the column, current player, row, and any error message
        return result
    
    
    # Check if a column index is valid (within bounds and not full)
    def is_valid_column_index(self, column: int) -> bool:
        if 0 <= column < COLUMNS:
            return True
        return False

    # Check if a column is full
    def is_column_full(self, column: int) -> bool:
        # A column is full if the topmost row is not empty

        if self.board[ROWS - 1][column] == EMPTY:
            return False
        return True

# Helper to find open row for a column
    def find_open_row(self, column:int) -> int | None:
        # Ensure the column index is valid before searching for an open row
        if not self.is_valid_column_index(column):
            return None

        # Return the first empty row in the specified column, or None if the column is full
        for row in range(ROWS):
             if self.board[row][column] == EMPTY:
                return row
        return None

# Helper to check if the last move was a winning move
    def check_win(self, row:int, column:int) -> bool:
        # Check all directions for a connect 4
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]  # horizontal, vertical, diagonal /
        for dr, dc in directions:
            count = 1
            # Check in the positive direction
            r, c = row + dr, column + dc
            while 0 <= r < ROWS and 0 <= c < COLUMNS and self.board[r][c] == self.current_player:
                count += 1
                r += dr
                c += dc
            # Check in the negative direction
            r, c = row - dr, column - dc
            while 0 <= r < ROWS and 0 <= c < COLUMNS and self.board[r][c] == self.current_player:
                count += 1
                r -= dr
                c -= dc
            if count >= 4:
                return True
        return False

    #Helper to check if the game is a draw (no more valid moves)
    def check_draw(self) -> bool:
        return all(self.is_column_full(col) for col in range(COLUMNS))
    
