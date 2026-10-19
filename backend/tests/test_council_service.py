from copy import deepcopy

import pytest

from backend.app.services import council_service


@pytest.fixture
def fake_client(monkeypatch):
    class FakeClient:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    client = FakeClient()

    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setattr(
        council_service,
        "Groq",
        lambda **kwargs: client,
    )

    return client


@pytest.fixture
def yellow_forced_block_board():
    return [
        [2, 0, 2, 0, 0, 1, 0],
        [2, 0, 0, 0, 0, 1, 0],
        [0, 0, 0, 0, 0, 1, 0],
        [0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0],
    ]


def make_immediate_win_board(current_player):
    opponent = 3 - current_player
    board = [[0 for _ in range(7)] for _ in range(6)]

    for row in range(3):
        board[row][1] = current_player
        board[row][5] = opponent

    return board


@pytest.mark.parametrize("current_player", [1, 2], ids=["red", "yellow"])
def test_accepts_captain_immediate_win(
    monkeypatch,
    fake_client,
    current_player,
):
    board = make_immediate_win_board(current_player)
    original_board = deepcopy(board)
    calls = []

    def fake_ask_advisor(**kwargs):
        calls.append(kwargs)

        return {
            "recommended_column": 1,
            "explanation": "Complete the vertical four.",
        }

    monkeypatch.setattr(
        council_service,
        "ask_advisor",
        fake_ask_advisor,
    )

    outcome = council_service.run_guarded_council(
        board=board,
        current_player=current_player,
    )

    final = outcome["final_recommendation"]

    assert outcome["council_status"] == "completed"
    assert outcome["failed_stage"] is None
    assert outcome["error"] is None

    assert final["recommended_column"] == 1
    assert final["source"] == "captain"
    assert final["fallback_reason"] is None
    assert final["tactical_outcome"] == "immediate_win"
    assert final["tactical_check"]["legal"] is True
    assert final["tactical_check"]["tactical_passed"] is True
    assert final["captain_check"]["tactical_passed"] is True

    assert [call["name"] for call in calls] == [
        "ATTACKER",
        "DEFENDER",
        "CAPTAIN",
    ]
    assert all(call["current_player"] == current_player for call in calls)
    assert all(call["client"] is fake_client for call in calls)

    captain_inputs = calls[-1]
    assert captain_inputs["attacker_proposal"] == outcome["reports"]["attacker"]
    assert captain_inputs["defender_review"] == outcome["reports"]["defender"]

    assert all(stage["status"] == "completed" for stage in outcome["stages"].values())
    assert board == original_board
    assert fake_client.closed is True


def test_rejects_captain_move_that_misses_required_block(
    monkeypatch,
    fake_client,
    yellow_forced_block_board,
):
    def fake_ask_advisor(**kwargs):
        return {
            "recommended_column": 3,
            "explanation": "Prefer the center.",
        }

    monkeypatch.setattr(
        council_service,
        "ask_advisor",
        fake_ask_advisor,
    )

    outcome = council_service.run_guarded_council(
        board=yellow_forced_block_board,
        current_player=2,
    )

    final = outcome["final_recommendation"]

    assert outcome["council_status"] == "completed"
    assert outcome["failed_stage"] is None

    assert final["recommended_column"] == 5
    assert final["source"] == "deterministic_fallback"
    assert final["fallback_reason"] == "captain_failed_tactical_check"
    assert final["tactical_outcome"] == "immediate_loss_prevented"

    assert final["captain_check"]["legal"] is True
    assert final["captain_check"]["tactical_passed"] is False
    assert final["tactical_check"]["legal"] is True
    assert final["tactical_check"]["tactical_passed"] is True
    assert fake_client.closed is True


def test_advisor_failure_returns_fallback_and_skips_remaining_stage(
    monkeypatch,
    fake_client,
    yellow_forced_block_board,
):
    calls = []

    def fake_ask_advisor(**kwargs):
        calls.append(kwargs["name"])

        if kwargs["name"] == "DEFENDER":
            raise RuntimeError("Simulated advisor failure")

        return {
            "recommended_column": 5,
            "explanation": "Block the vertical threat.",
        }

    monkeypatch.setattr(
        council_service,
        "ask_advisor",
        fake_ask_advisor,
    )

    outcome = council_service.run_guarded_council(
        board=yellow_forced_block_board,
        current_player=2,
    )

    final = outcome["final_recommendation"]

    assert calls == ["ATTACKER", "DEFENDER"]
    assert outcome["council_status"] == "failed"
    assert outcome["failed_stage"] == "defender"
    assert outcome["error"]["exception_type"] == "RuntimeError"
    assert outcome["error"]["message"] == "Simulated advisor failure"

    assert outcome["stages"]["attacker"]["status"] == "completed"
    assert outcome["stages"]["defender"]["status"] == "failed"
    assert outcome["stages"]["captain"]["status"] == "skipped"
    assert set(outcome["reports"]) == {"attacker"}

    assert final["recommended_column"] == 5
    assert final["source"] == "deterministic_fallback"
    assert final["fallback_reason"] == "council_error"
    assert final["tactical_outcome"] == "immediate_loss_prevented"
    assert final["captain_check"] is None
    assert final["tactical_check"]["tactical_passed"] is True
    assert fake_client.closed is True


def test_missing_credentials_returns_fallback_without_creating_client(
    monkeypatch,
    yellow_forced_block_board,
):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    def unexpected_client_creation(**kwargs):
        pytest.fail("Groq client must not be created without credentials.")

    def unexpected_advisor_call(**kwargs):
        pytest.fail("Advisors must not run without credentials.")

    monkeypatch.setattr(
        council_service,
        "Groq",
        unexpected_client_creation,
    )
    monkeypatch.setattr(
        council_service,
        "ask_advisor",
        unexpected_advisor_call,
    )

    outcome = council_service.run_guarded_council(
        board=yellow_forced_block_board,
        current_player=2,
    )

    final = outcome["final_recommendation"]

    assert outcome["council_status"] == "failed"
    assert outcome["failed_stage"] == "client_setup"
    assert outcome["error"]["exception_type"] == "RuntimeError"
    assert outcome["error"]["message"] == "GROQ_API_KEY is not configured."
    assert outcome["reports"] == {}
    assert all(stage["status"] == "skipped" for stage in outcome["stages"].values())

    assert final["recommended_column"] == 5
    assert final["source"] == "deterministic_fallback"
    assert final["fallback_reason"] == "council_error"
    assert final["tactical_check"]["tactical_passed"] is True


def test_council_passes_a_deep_copy_of_board_to_advisors(
    monkeypatch,
    fake_client,
    yellow_forced_block_board,
):
    board = yellow_forced_block_board
    original_board = deepcopy(board)

    def fake_ask_advisor(**kwargs):
        advisor_board = kwargs["board"]

        assert advisor_board is not board
        assert all(
            copied_row is not original_row
            for copied_row, original_row in zip(advisor_board, board)
        )

        if kwargs["name"] == "ATTACKER":
            advisor_board[5][0] = 1
            raise RuntimeError("Simulated mutation followed by failure")

        pytest.fail("Later advisors should be skipped after failure.")

    monkeypatch.setattr(
        council_service,
        "ask_advisor",
        fake_ask_advisor,
    )

    outcome = council_service.run_guarded_council(
        board=board,
        current_player=2,
    )

    assert board == original_board
    assert outcome["failed_stage"] == "attacker"
    assert outcome["final_recommendation"]["recommended_column"] == 5
    assert fake_client.closed is True


def test_client_cleanup_failure_does_not_discard_recommendation(
    monkeypatch,
    fake_client,
    caplog,
):
    board = make_immediate_win_board(current_player=1)

    def fake_ask_advisor(**kwargs):
        return {
            "recommended_column": 1,
            "explanation": "Complete the vertical four.",
        }

    def failing_close():
        raise RuntimeError("Simulated cleanup failure")

    monkeypatch.setattr(
        council_service,
        "ask_advisor",
        fake_ask_advisor,
    )
    monkeypatch.setattr(fake_client, "close", failing_close)

    with caplog.at_level("WARNING", logger=council_service.__name__):
        outcome = council_service.run_guarded_council(
            board=board,
            current_player=1,
        )

    assert outcome["council_status"] == "completed"
    assert outcome["final_recommendation"]["recommended_column"] == 1
    assert outcome["final_recommendation"]["source"] == "captain"
    assert "Failed to close the council API client." in caplog.text
