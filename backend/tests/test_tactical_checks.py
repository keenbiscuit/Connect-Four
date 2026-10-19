from copy import deepcopy

import pytest

from tactical_checks import (
    analyze_tactics,
    check_recommendation,
    has_four,
)


@pytest.fixture
def forced_block_board():
    return [
        [0, 2, 1, 2, 0, 1, 0],
        [0, 2, 2, 2, 0, 1, 0],
        [0, 1, 0, 1, 0, 1, 0],
        [0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0],
    ]


def test_only_column_five_prevents_immediate_loss(forced_block_board):
    analysis = analyze_tactics(forced_block_board, 2)

    assert analysis["immediate_winning_columns"] == []
    assert analysis["opponent_immediate_winning_columns"] == [5]
    assert analysis["acceptable_columns"] == [5]

    assert check_recommendation(analysis, 5)["tactical_passed"] is True

    for column in (0, 1, 2, 3, 4, 6):
        check = check_recommendation(analysis, column)

        assert check["tactical_passed"] is False
        assert check["opponent_winning_replies"] == [5]


def test_yellow_win_has_priority_over_block(forced_block_board):
    board = deepcopy(forced_block_board)
    board[2][1] = 2

    analysis = analyze_tactics(board, 2)

    assert analysis["immediate_winning_columns"] == [1]
    assert analysis["opponent_immediate_winning_columns"] == [5]
    assert analysis["requirement"] == "take_immediate_win"
    assert analysis["acceptable_columns"] == [1]

    winning_check = check_recommendation(analysis, 1)

    assert winning_check["tactical_passed"] is True
    assert winning_check["opponent_winning_replies"] == []

    blocking_check = check_recommendation(analysis, 5)

    assert blocking_check["tactical_passed"] is False


def test_analysis_does_not_change_board(forced_block_board):
    original = deepcopy(forced_block_board)

    analyze_tactics(forced_block_board, 2)

    assert forced_block_board == original


@pytest.mark.parametrize(
    "cells",
    [
        [(0, 0), (0, 1), (0, 2), (0, 3)],
        [(0, 0), (1, 0), (2, 0), (3, 0)],
        [(0, 0), (1, 1), (2, 2), (3, 3)],
        [(0, 3), (1, 2), (2, 1), (3, 0)],
    ],
)
def test_has_four_in_each_direction(cells):
    board = [[0] * 7 for _ in range(6)]

    for row, column in cells:
        board[row][column] = 2

    assert has_four(board, 2) is True
    assert has_four(board, 1) is False


def test_rejects_floating_disc():
    board = [[0] * 7 for _ in range(6)]
    board[1][0] = 1

    with pytest.raises(ValueError, match="floating disc"):
        analyze_tactics(board, 2)
