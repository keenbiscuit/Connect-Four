from fastapi.testclient import TestClient

from backend.app import main
from backend.app.game_state import RED, YELLOW
from backend.app.services.game_manager import GameManager


def make_client() -> TestClient:
    # create a new game manager instance for every test
    main.game_manager = GameManager()
    return TestClient(main.app)


# Test for retrieving a game by its ID
def test_get_game_by_id():
    client = make_client()

    # Create a new game
    response = client.post("/games")
    game_id = response.json()["game_id"]

    # Make a move in the the game and assert the board is updated along with the current player and status
    move_response = client.post(f"/games/{game_id}/moves", json={"column": 0})
    assert move_response.status_code == 200
    move_data = move_response.json()
    assert move_data["board"][0][0] == RED
    assert move_data["current_player"] == YELLOW
    assert move_data["status"] == "active"
    assert move_data["winner"] is None

    # Retrieve the game by its ID
    get_response = client.get(f"/games/{game_id}")
    assert get_response.status_code == 200
    data = get_response.json()
    assert data["game_id"] == game_id
    assert data["board"] == move_data["board"]
    assert data["status"] == move_data["status"]
    assert data["current_player"] == move_data["current_player"]
    assert data["winner"] == move_data["winner"]


def test_get_nonexistent_game():
    client = make_client()

    # Attempt to retrieve a non-existent game
    get_response = client.get("/games/unknown_game_id")
    assert get_response.status_code == 404
    data = get_response.json()
    assert "error" in data["detail"]
    assert data["detail"]["error"] == "Game not found"
