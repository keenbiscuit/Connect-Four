from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient
import pytest

from backend.app import main
from backend.app.game_state import EMPTY, RED, YELLOW
from backend.app.services.game_manager import GameManager


def make_test_client():
    main.game_manager = GameManager()
    main.active_connections = {}  # Reset active connections for each test
    main.player_roles = {}  # Reset player roles for each test
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
        assert data["assigned_player"] == RED
        assert data["winner"] is None
        assert game_id in main.active_connections
        assert len(main.active_connections[game_id]) == 1
        assert game_id in main.player_roles
        assert len(main.player_roles[game_id]) == 1
        assert RED in main.player_roles[game_id]

    assert game_id not in main.active_connections
    assert game_id not in main.player_roles


def test_two_websocket_connections():
    # Create a test client
    client = make_test_client()

    # create an HTTP game
    response = client.post("/games")
    assert response.status_code == 201
    game_id = response.json()["game_id"]

    # connect to the websocket with two clients
    with client.websocket_connect(f"/ws/games/{game_id}") as websocket1:
        with client.websocket_connect(f"/ws/games/{game_id}") as websocket2:
            # receive the initial game state for both clients
            data1 = websocket1.receive_json()
            data2 = websocket2.receive_json()
            assert data1["type"] == "game_state"
            assert data2["type"] == "game_state"
            assert data1["game_id"] == game_id
            assert data2["game_id"] == game_id
            assert data1["board"] == [[EMPTY] * 7 for _ in range(6)]
            assert data2["board"] == [[EMPTY] * 7 for _ in range(6)]
            assert data1["status"] == "active"
            assert data2["status"] == "active"
            assert data1["current_player"] == RED
            assert data2["current_player"] == RED
            assert data1["winner"] is None
            assert data2["winner"] is None

            assert data1["assigned_player"] == RED  # Ensure different assigned players
            assert (
                data2["assigned_player"] == YELLOW
            )  # Ensure different assigned players

            # check that both connections are registered
            assert game_id in main.active_connections
            assert len(main.active_connections[game_id]) == 2

            # check that both player roles are registered
            assert game_id in main.player_roles
            assert len(main.player_roles[game_id]) == 2
            assert RED in main.player_roles[game_id]
            assert YELLOW in main.player_roles[game_id]

        # assert red still exists in both maps after yellow disconnects
        assert game_id in main.active_connections
        assert len(main.active_connections[game_id]) == 1
        assert RED in main.player_roles.get(game_id, {})
        assert game_id in main.player_roles
        assert len(main.player_roles[game_id]) == 1
        assert YELLOW not in main.player_roles[game_id]

    # assert game_id is removed from both maps after red disconnects
    assert game_id not in main.active_connections
    assert game_id not in main.player_roles


def test_third_connection_rejected():
    # Create a test client
    client = make_test_client()

    # create an HTTP game
    response = client.post("/games")
    assert response.status_code == 201
    game_id = response.json()["game_id"]

    # connect to the websocket with two clients
    with (
        client.websocket_connect(f"/ws/games/{game_id}") as websocket1,
        client.websocket_connect(f"/ws/games/{game_id}") as websocket2,
    ):
        # receive the initial game state for both clients
        data1 = websocket1.receive_json()
        data2 = websocket2.receive_json()
        assert data1["type"] == "game_state"
        assert data2["type"] == "game_state"
        assert data1["game_id"] == game_id
        assert data2["game_id"] == game_id

        # Attempt to connect a third client to the same game

        with pytest.raises(WebSocketDisconnect):  # noqa: SIM117
            # attempt to connect a third client to the same game
            with client.websocket_connect(f"/ws/games/{game_id}"):
                assert False, "Expected WebSocketDisconnect"

        assert game_id in main.active_connections
        assert len(main.active_connections[game_id]) == 2
        assert game_id in main.player_roles
        assert len(main.player_roles[game_id]) == 2
        assert RED in main.player_roles[game_id]
        assert YELLOW in main.player_roles[game_id]
