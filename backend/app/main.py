# import FastAPI from the fastapi package
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status

from backend.app.game_state import RED, YELLOW
from backend.app.schemas.game_response import GameResponse
from backend.app.schemas.move_request import MoveRequest
from backend.app.services.game_manager import GameManager

# create FastAPI app instance
app = FastAPI()

# create an instance of the GameManager
game_manager = GameManager()

# create map to store active websocket connections for each game
active_connections: dict[str, set[WebSocket]] = {}

# create map to store assigned player roles for each game
# game ID → player color mapped to its WebSocket
player_roles: dict[str, dict[int, WebSocket]] = {}


# define health check endpoint
@app.get("/health")
def health():
    return {"status": "ok"}


# define endpoint for retrieving a game by its ID
@app.get(
    "/games/{game_id}", response_model=GameResponse, status_code=status.HTTP_200_OK
)
def get_game(game_id: str):
    game = game_manager.get_game(game_id)
    if game is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail={"error": "Game not found"}
        )
    return GameResponse(
        game_id=game_id,
        board=game.board,
        status=game.status,
        current_player=game.current_player,
        winner=game.winner,
    )


# define endpoint for creating a new game
@app.post("/games", response_model=GameResponse, status_code=status.HTTP_201_CREATED)
def create_game():
    game_id, game = game_manager.create_game()
    # return the newly created game as a response
    return GameResponse(
        game_id=game_id,
        board=game.board,
        status=game.status,
        current_player=game.current_player,
        winner=game.winner,
    )


# define endpoint for dropping a piece in a game
@app.post(
    "/games/{game_id}/moves",
    response_model=GameResponse,
    status_code=status.HTTP_200_OK,
)
def drop_piece(game_id: str, move: MoveRequest):

    game = game_manager.get_game(game_id)

    # validate the move request
    if game is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail={"error": "Game not found"}
        )

    # attempt to drop the piece in the specified column
    result = game.drop_piece(move.column)

    # check if the move was successful
    if not result.success:
        # if the drop location is invalid
        if result.reason == "invalid_column":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={"error": "Invalid column"},
            )

        # if the column is full
        elif result.reason == "column_full":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail={"error": "Column is full"}
            )

        # if the game has already finished
        elif result.reason == "game_finished":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": "Game has already finished"},
            )
        # if none of the specific reasons matched, raise a generic bad request error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail={"error": result.reason}
        )

    return GameResponse(
        game_id=game_id,
        board=game.board,
        status=game.status,
        current_player=game.current_player,
        winner=game.winner,
    )


# websocket route
@app.websocket("/ws/games/{game_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str):
    # retrieve the game instance based on the provided game_id
    game = game_manager.get_game(game_id)
    if game is None:
        await websocket.close(code=1008)
        return
    # if both player roles are already assigned, reject third connection
    if len(player_roles.get(game_id, {})) >= 2:
        await websocket.close(code=1008)
        return

    # choose an available role for the new connection
    assigned_player = RED if RED not in player_roles.get(game_id, {}) else YELLOW

    # accept the websocket connection and send the initial game state
    await websocket.accept()

    # register the websocket connection for the game
    if game_id not in active_connections:
        active_connections[game_id] = set()
    active_connections[game_id].add(websocket)

    # register the assigned player role for the game
    if game_id not in player_roles:
        player_roles[game_id] = {}
    player_roles[game_id][assigned_player] = websocket

    # send the initial game state to the connected client
    await websocket.send_json(
        {
            "type": "game_state",
            "game_id": game_id,
            "board": game.board,
            "status": game.status,
            "current_player": game.current_player,
            "assigned_player": assigned_player,
            "winner": game.winner,
        }
    )
    try:
        while True:
            #  will later become client to server move message handler
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        # Will change to logging in the future
        print("Client disconnected")
    # remove the websocket connection from the active connections set when the client disconnects
    finally:
        connections = active_connections.get(game_id)
        if connections is not None:
            connections.discard(websocket)
        # If there are no more connections for the game, remove the game_id from active_connections
        if connections is not None and not connections:
            active_connections.pop(game_id, None)

        roles = player_roles.get(
            game_id
        )  # returns real role or none if no roles exist for the game
        if roles is not None and roles.get(assigned_player) is websocket:
            roles.pop(
                assigned_player, None
            )  # safely removes only endpoints own role from the game
        # If there are no more roles for the game, remove the game_id from player_roles
        if roles is not None and not roles:
            player_roles.pop(game_id, None)
