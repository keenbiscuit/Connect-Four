from copy import deepcopy

ROWS = 6
COLUMNS = 7
EMPTY = 0
RED = 1
YELLOW = 2


def validate_board(board):
    if (
        not isinstance(board, list)
        or len(board) != ROWS
        or any(not isinstance(row, list) or len(row) != COLUMNS for row in board)
    ):
        raise ValueError("Board must contain six rows of seven cells.")

    for column in range(COLUMNS):
        found_empty = False

        for row in range(ROWS):
            cell = board[row][column]

            if type(cell) is not int or cell not in (EMPTY, RED, YELLOW):
                raise ValueError("Cells must be integers 0, 1, or 2.")

            if cell == EMPTY:
                found_empty = True
            elif found_empty:
                raise ValueError(f"Column {column} contains a floating disc.")


def legal_columns(board):
    return [column for column in range(COLUMNS) if board[ROWS - 1][column] == EMPTY]


def drop_disc(board, column, player):
    next_board = deepcopy(board)

    for row in range(ROWS):
        if next_board[row][column] == EMPTY:
            next_board[row][column] = player
            return next_board

    raise ValueError(f"Column {column} is full.")


def has_four(board, player):
    directions = (
        (0, 1),
        (1, 0),
        (1, 1),
        (1, -1),
    )

    for row in range(ROWS):
        for column in range(COLUMNS):
            for row_step, column_step in directions:
                end_row = row + 3 * row_step
                end_column = column + 3 * column_step

                if not (0 <= end_row < ROWS and 0 <= end_column < COLUMNS):
                    continue

                if all(
                    board[row + offset * row_step][column + offset * column_step]
                    == player
                    for offset in range(4)
                ):
                    return True

    return False


def immediate_winning_columns(board, player):
    return [
        column
        for column in legal_columns(board)
        if has_four(drop_disc(board, column, player), player)
    ]


def analyze_tactics(board, current_player):
    validate_board(board)

    if type(current_player) is not int or current_player not in (RED, YELLOW):
        raise ValueError("Current player must be 1 or 2.")

    if has_four(board, RED) or has_four(board, YELLOW):
        raise ValueError("Position already contains a winning line.")

    legal = legal_columns(board)

    if not legal:
        raise ValueError("Position is a finished draw.")

    opponent = YELLOW if current_player == RED else RED
    winning = immediate_winning_columns(board, current_player)
    opponent_winning = immediate_winning_columns(board, opponent)

    safe_nonwinning = []
    opponent_replies = {}

    for column in legal:
        next_board = drop_disc(board, column, current_player)

        if has_four(next_board, current_player):
            opponent_replies[column] = []
            continue

        replies = immediate_winning_columns(next_board, opponent)
        opponent_replies[column] = replies

        if not replies:
            safe_nonwinning.append(column)

    if winning:
        requirement = "take_immediate_win"
        acceptable = winning
    elif safe_nonwinning:
        requirement = "avoid_immediate_loss"
        acceptable = safe_nonwinning
    else:
        requirement = "no_move_avoids_immediate_loss"
        acceptable = []

    return {
        "current_player": current_player,
        "legal_columns": legal,
        "immediate_winning_columns": winning,
        "opponent_immediate_winning_columns": opponent_winning,
        "safe_nonwinning_columns": safe_nonwinning,
        "opponent_winning_replies_by_column": opponent_replies,
        "requirement": requirement,
        "acceptable_columns": acceptable,
    }


def check_recommendation(analysis, column):
    legal = type(column) is int and column in analysis["legal_columns"]

    if not legal:
        passed = False
        reason = "Recommendation is not a legal column."
    elif analysis["requirement"] == "no_move_avoids_immediate_loss":
        passed = None
        reason = (
            "Every legal move permits an immediate opponent win. "
            "This checker cannot rank the losing moves."
        )
    else:
        passed = column in analysis["acceptable_columns"]

        if analysis["requirement"] == "take_immediate_win":
            reason = (
                "Recommendation takes an immediate win."
                if passed
                else "Recommendation misses an available immediate win."
            )
        else:
            reason = (
                "Recommendation leaves no immediate opponent winning reply."
                if passed
                else "Recommendation allows an avoidable immediate loss."
            )

    return {
        "recommended_column": column,
        "legal": legal,
        "tactical_passed": passed,
        "reason": reason,
        "opponent_winning_replies": (
            analysis["opponent_winning_replies_by_column"].get(column)
            if legal
            else None
        ),
    }
