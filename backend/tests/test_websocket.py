from fastapi.testclient import TestClient

from backend.app import main
from backend.app.game_state import EMPTY, RED
from backend.app.services.game_manager import GameManager


def make_test_client():
    main.game_manager = GameManager()
    return TestClient(main.app)


def test_websocket_connection():
    # Create a test client
    client = make_test_client()

    # create an HTTP game
    response = client.post("/games")
    assert response.status_code == 201
    game_id = response.json()["game_id"]

    # connect to the websocket
    with client.websocket_connect(f"/ws/games/{game_id}") as websocket:
        # receive the initial game state
        data = websocket.receive_json()
        assert data["type"] == "game_state"
        assert data["game_id"] == game_id
        assert data["board"] == [[EMPTY] * 7 for _ in range(6)]
        assert data["status"] == "active"
        assert data["current_player"] == RED
        assert data["winner"] is None
