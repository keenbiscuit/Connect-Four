from copy import deepcopy

import pytest

from backend.app.game_state import (
    COLUMNS,
    EMPTY,
    RED,
    ROWS,
    YELLOW,
    GameState,
)


def test_reset_active_game_is_rejected_without_changes():
    game = GameState()
    game.drop_piece(0)
    before = deepcopy(vars(game))

    assert game.reset_game() is False
    assert vars(game) == before


def test_reset_after_win():
    game = GameState(starting_player=YELLOW)

    for column in (0, 1, 0, 1, 0, 1, 0):
        assert game.drop_piece(column).success is True

    assert game.status == "win"
    assert game.winner == YELLOW

    assert game.reset_game() is True

    assert game.board == [[EMPTY for _ in range(COLUMNS)] for _ in range(ROWS)]
    assert game.status == "active"
    assert game.winner is None
    assert game.current_player == YELLOW
    assert game.starting_player == YELLOW

    result = game.drop_piece(3)
    assert result.success is True
    assert result.player == YELLOW


def test_reset_after_draw():
    game = GameState()
    game.board = [
        [RED, RED, YELLOW, YELLOW, RED, RED, YELLOW],
        [YELLOW, YELLOW, RED, RED, YELLOW, YELLOW, RED],
        [RED, RED, YELLOW, YELLOW, RED, RED, YELLOW],
        [YELLOW, YELLOW, RED, RED, YELLOW, YELLOW, RED],
        [RED, RED, YELLOW, YELLOW, RED, RED, YELLOW],
        [YELLOW, YELLOW, RED, RED, YELLOW, YELLOW, RED],
    ]
    game.status = "draw"
    game.current_player = YELLOW

    assert game.reset_game() is True

    assert game.board == [[EMPTY for _ in range(COLUMNS)] for _ in range(ROWS)]
    assert game.status == "active"
    assert game.winner is None
    assert game.current_player == RED


@pytest.mark.parametrize(
    ("mode", "bot_player"),
    [
        ("human_vs_human", None),
        ("human_vs_bot", YELLOW),
    ],
)
def test_reset_preserves_configuration(mode, bot_player):
    game = GameState(
        starting_player=RED,
        mode=mode,
        bot_player=bot_player,
    )
    game.status = "win"
    game.winner = RED

    assert game.reset_game() is True

    assert game.starting_player == RED
    assert game.mode == mode
    assert game.bot_player == bot_player


def test_second_reset_is_rejected():
    game = GameState()
    game.status = "win"
    game.winner = RED

    assert game.reset_game() is True

    before = deepcopy(vars(game))

    assert game.reset_game() is False
    assert vars(game) == before
