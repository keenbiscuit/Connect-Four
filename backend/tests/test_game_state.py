from backend.app.game_state import COLUMNS, ROWS, EMPTY, RED, YELLOW, GameState


def test_new_game_has_empty_board() -> None:
    game = GameState()

    # Check that the board has the correct dimensions and is empty
    assert len(game.board) == ROWS
    assert all(len(row) == COLUMNS for row in game.board)
    assert all(cell == EMPTY for row in game.board for cell in row)
    assert game.current_player == RED


def test_column_full() -> None:
    game = GameState()

    # Initially, no column should be full
    for col in range(COLUMNS):
        assert not game.is_column_full(col)

    # Fill up a column and check that it becomes full
    for row in range(ROWS):
        game.board[row][0] = RED
    assert game.is_column_full(0)

    # Check that other columns are still not full
    for col in range(1, COLUMNS):
        assert not game.is_column_full(col)


def test_find_open_row() -> None:
    game = GameState()

    # Initially, the open row for any column should be 0
    for col in range(COLUMNS):
        assert game.find_open_row(col) == 0

    # Fill up a column partially and check the open row
    game.board[0][0] = RED
    assert game.find_open_row(0) == 1

    # Fill up the entire column and check that it returns None
    for row in range(ROWS):
        game.board[row][1] = RED
    assert game.find_open_row(1) is None

    # Check that other columns still return 0 as the open row
    for col in range(2, COLUMNS):
        assert game.find_open_row(col) == 0


def test_is_valid_column_index() -> None:
    game = GameState()

    # Initially, all columns should be valid
    for col in range(COLUMNS):
        assert game.is_valid_column_index(col)

    # A full column is still a valid index but unavailable for a move
    for row in range(ROWS):
        game.board[row][0] = RED
    assert game.is_column_full(0)
    assert game.is_valid_column_index(0)

    # Check that other columns are still valid
    for col in range(1, COLUMNS):
        assert game.is_valid_column_index(col)

    # Check invalid column indices
    assert not game.is_valid_column_index(-1)
    assert not game.is_valid_column_index(COLUMNS)
    assert not game.is_valid_column_index(COLUMNS + 1)
    assert not game.is_valid_column_index(-COLUMNS)


def test_drop_piece_rejects_invalid_or_full_moves_without_mutation() -> None:
    game = GameState()
    # The current player should initially be RED
    assert game.current_player == RED

    # Initially, the open row for any column should be 0
    for col in range(COLUMNS):
        assert game.find_open_row(col) == 0

    # Drop a piece into an empty column
    result = game.drop_piece(0)
    assert result.success
    assert result.column == 0
    assert result.player == RED
    assert result.row == 0
    assert result.reason is None

    # Fill up a column and attempt to drop another piece
    for row in range(1, ROWS):
        game.board[row][0] = RED

    # Save the current state of the board before making any moves
    board_before = [row[:] for row in game.board]

    player_before = game.current_player

    result = game.drop_piece(0)
    assert not result.success
    assert result.reason == "column_full"

    # Attempt to drop a piece into an invalid column
    result = game.drop_piece(COLUMNS)
    assert not result.success
    assert result.reason == "invalid_column"

    # Attempt to drop a piece into a negative column index
    result = game.drop_piece(-1)
    assert not result.success
    assert result.reason == "invalid_column"

    # After failing to drop a piece into a full or invalid column, the current player should remain the same
    assert game.current_player == player_before

    # The board should remain unchanged for the rejected moves
    assert game.board == board_before


def test_drop_piece_stacks_pieces_and_switches_turns():
    game = GameState()
    # Drop a piece into an empty column
    result = game.drop_piece(0)
    assert result.success
    assert result.row == 0
    assert game.current_player == YELLOW

    # Drop another piece into the same column
    result = game.drop_piece(0)
    assert result.success
    assert result.row == 1
    assert game.current_player == RED

    # Drop a third piece into the same column
    result = game.drop_piece(0)
    assert result.success
    assert result.row == 2
    assert game.current_player == YELLOW

    # Drop a fourth piece into the same column
    result = game.drop_piece(0)
    assert result.success
    assert result.row == 3
    assert game.current_player == RED


def test_drop_piece_detects_winning_move():
    game = GameState()
    # Set up a winning condition for RED
    for row in range(3):
        game.board[row][0] = RED

    # Drop the winning piece
    result = game.drop_piece(0)
    assert result.success
    assert result.row == 3
    assert result.reason is None
    assert result.status == "win"
    assert result.winner == RED
    assert game.status == "win"
    assert game.winner == RED


def test_drop_piece_detects_horizontal_win():
    game = GameState()
    # Set up a horizontal winning condition for RED
    for col in range(3):
        game.board[0][col] = RED

    # Drop the winning piece
    result = game.drop_piece(3)
    assert result.success
    assert result.row == 0
    assert result.reason is None
    assert result.status == "win"
    assert result.winner == RED
    assert game.status == "win"
    assert game.winner == RED


def test_drop_piece_detects_vertical_win():
    game = GameState()
    # Set up a vertical winning condition for RED
    for row in range(3):
        game.board[row][0] = RED

    # Drop the winning piece
    result = game.drop_piece(0)
    assert result.success
    assert result.row == 3
    assert result.reason is None
    assert result.status == "win"
    assert result.winner == RED
    assert game.status == "win"
    assert game.winner == RED


def test_drop_piece_detects_diagonal_win():
    game = GameState()
    # Set up a diagonal winning condition for RED
    game.board[0][0] = RED
    game.board[1][1] = RED
    game.board[2][2] = RED
    game.board[0][3] = YELLOW
    game.board[1][3] = YELLOW
    game.board[2][3] = YELLOW

    # Drop the winning piece
    result = game.drop_piece(3)
    assert result.success
    assert result.row == 3
    assert result.reason is None
    assert result.status == "win"
    assert result.winner == RED
    assert game.status == "win"
    assert game.winner == RED


def test_drop_piece_detects_anti_diagonal_win():
    game = GameState()
    # Set up an anti-diagonal winning condition for RED
    game.board[0][3] = RED
    game.board[1][2] = RED
    game.board[2][1] = RED
    game.board[0][0] = YELLOW
    game.board[1][0] = YELLOW
    game.board[2][0] = YELLOW

    # Drop the winning piece
    result = game.drop_piece(0)
    assert result.success
    assert result.row == 3
    assert result.reason is None
    assert result.status == "win"
    assert result.winner == RED
    assert game.status == "win"
    assert game.winner == RED


def test_post_win_move_attempt_returns_game_finished():
    game = GameState()
    # Set up a horizontal winning condition for RED
    for col in range(3):
        game.board[0][col] = RED
    # Drop the winning piece
    result = game.drop_piece(3)
    assert result.success
    assert result.status == "win"
    assert game.status == "win"

    # Attempt to make another move after the game is finished
    result = game.drop_piece(4)
    assert not result.success
    assert result.reason == "game_finished"
    assert game.status == "win"
    assert game.winner == RED
