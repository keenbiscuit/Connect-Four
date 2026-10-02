# Tests for the Connect-4 FastAPI POST endpoints

from fastapi.testclient import TestClient
from backend.app import main
from backend.app.services.game_manager import GameManager
from backend.app.game_state import RED, YELLOW

# Helper function to create a test client with a fresh game manager
def make_client() -> TestClient:
    main.game_manager = GameManager()
    return TestClient(main.app)


# Test for creating a new game
def test_create_game():
    client = make_client()
    response = client.post("/games")
    assert response.status_code == 201
    data = response.json()
    assert "game_id" in data
    assert "board" in data
    assert "status" in data
    assert "current_player" in data
    assert "winner" in data
    assert isinstance(data["game_id"], str)
    assert isinstance(data["board"], list)
    assert all(isinstance(row, list) for row in data["board"])
    #assert all rows have length 7
    assert all(len(row) == 7 for row in data["board"])
    #assert the board has 6 rows
    assert len(data["board"]) == 6

    #assert the status is active
    assert data["status"] == "active"

    #assert the current player is either "RED" or "YELLOW"
    assert data["current_player"] == RED

    #assert the winner is either None since game is fresh
    assert data["winner"] is None

#Test new game alternates player
def test_create_game_alternates_player():
    client = make_client()

    # Create three new games to test player alternation
    first = client.post("/games")
    second = client.post("/games")
    third = client.post("/games")

    # Assert that all three games were created successfully
    assert first.status_code == 201
    assert second.status_code == 201
    assert third.status_code == 201

    # Assert that the current player alternates correctly
    assert first.json()["current_player"] == RED
    assert second.json()["current_player"] == YELLOW
    assert third.json()["current_player"] == RED

def test_drop_piece_places_red_piece_and_switches_player():
    client = make_client()

    # Create a new game
    response = client.post("/games")
    game_id = response.json()["game_id"]

    # Drop a piece in the first column
    move_response = client.post(f"/games/{game_id}/moves", json={"column": 0})
    assert move_response.status_code == 200
    data = move_response.json()

    # Assert that the piece was placed and the current player switched
    assert data["board"][0][0] == RED
    assert data["current_player"] == YELLOW

    # Drop a piece in the same column for the next player
    move_response = client.post(f"/games/{game_id}/moves", json={"column": 0})
    assert move_response.status_code == 200
    data = move_response.json()

    # Assert that the piece was placed and the current player switched back
    assert data["board"][1][0] == YELLOW
    assert data["current_player"] == RED

def test_unkown_game_ID():
    client = make_client()

    # Attempt to make a move in a non-existent game
    move_response = client.post(f"/games/unknown_game_id/moves", json={"column": 0})
    assert move_response.status_code == 404
    data = move_response.json()
    assert "error" in data["detail"]
    assert data["detail"]["error"] == "Game not found"

def test_invalid_column():
    client = make_client()

    # Create a new game
    response = client.post("/games")
    game_id = response.json()["game_id"]

    # Attempt to make a move in an invalid column
    move_response = client.post(f"/games/{game_id}/moves", json={"column": 10})
    assert move_response.status_code == 422
    data = move_response.json()
    assert "error" in data["detail"]
    assert data["detail"]["error"] == "Invalid column"

def test_negative_column_is_invalid():
    client = make_client()

    # Create a new game
    response = client.post("/games")
    game_id = response.json()["game_id"]

    # Attempt to make a move in a negative column
    move_response = client.post(f"/games/{game_id}/moves", json={"column": -1})
    assert move_response.status_code == 422
    data = move_response.json()
    assert "error" in data["detail"]
    assert data["detail"]["error"] == "Invalid column"

def test_column_full():
    client = make_client()

    # Create a new game
    response = client.post("/games")
    game_id = response.json()["game_id"]

    # Fill the first column
    for _ in range(6):
        move_response = client.post(f"/games/{game_id}/moves", json={"column": 0})
        assert move_response.status_code == 200

    # Attempt to make a move in the already full column
    move_response = client.post(f"/games/{game_id}/moves", json={"column": 0})
    assert move_response.status_code == 409
    data = move_response.json()
    assert "error" in data["detail"]
    assert data["detail"]["error"] == "Column is full"

def test_move_after_game_finished():
    client = make_client()

    # Create a new game
    response = client.post("/games")
    game_id = response.json()["game_id"]

    # Simulate a game that has already finished by making RED win
    # RED moves
    client.post(f"/games/{game_id}/moves", json={"column": 0})
    # YELLOW moves
    client.post(f"/games/{game_id}/moves", json={"column": 1})
    # RED moves
    client.post(f"/games/{game_id}/moves", json={"column": 0})
    # YELLOW moves
    client.post(f"/games/{game_id}/moves", json={"column": 1})
    # RED moves
    client.post(f"/games/{game_id}/moves", json={"column": 0})
    # YELLOW moves
    client.post(f"/games/{game_id}/moves", json={"column": 1})
    # RED moves to win
    winning_move = client.post(
    f"/games/{game_id}/moves",
    json={"column": 0},
    )

    assert winning_move.status_code == 200

    winning_data = winning_move.json()
    assert winning_data["status"] == "win"
    assert winning_data["winner"] == RED # which == 1

    # Attempt to make a move after the game has finished
    move_response = client.post(f"/games/{game_id}/moves", json={"column": 1})
    assert move_response.status_code == 409
    data = move_response.json()
    assert "error" in data["detail"]
    assert data["detail"]["error"] == "Game has already finished"

