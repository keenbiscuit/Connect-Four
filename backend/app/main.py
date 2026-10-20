# import FastAPI from the fastapi package

import asyncio
import logging
from copy import deepcopy

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from backend.app.game_state import RED, YELLOW
from backend.app.schemas.create_game_request import CreateGameRequest
from backend.app.schemas.game_response import GameResponse
from backend.app.schemas.move_request import MoveRequest
from backend.app.services.council_service import run_guarded_council
from backend.app.services.game_manager import GameManager

# create a logger for connection errors and council diagnostics
logger = logging.getLogger(__name__)


# create FastAPI app instance
app = FastAPI()

origins = [
    "http://localhost:5173",
    "https://connect-four-bice-nu.vercel.app",
]


# allow the configured frontend origins to make REST requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# create an instance of the GameManager
# REST and WebSocket routes share this same manager
game_manager = GameManager()


# create map to store active websocket connections for each game
active_connections: dict[str, set[WebSocket]] = {}


# create map to store assigned player roles for each game
# game ID → player color mapped to its WebSocket
# player identity comes from this server-owned mapping, not client messages
player_roles: dict[str, dict[int, WebSocket]] = {}


# retain references to background council tasks until they finish
council_tasks: set[asyncio.Task] = set()


# build the client-facing REST response
# internal council bookkeeping is not included in the REST response schema
def build_game_response(game_id, game):
    return GameResponse(
        game_id=game_id,
        board=game.board,
        status=game.status,
        current_player=game.current_player,
        mode=game.mode,
        bot_player=game.bot_player,
        winner=game.winner,
    )


# build council availability information for a specific player
# round and position identifiers let the client reject outdated advice
def council_metadata(game, player):
    return {
        "round_id": game.round_id,
        "position_version": game.position_version,
        "council_remaining": 0 if player in game.council_used else 1,
        "council_pending": player in game.council_pending,
    }


# build an authoritative game-state message for a specific recipient
# assigned_player and council availability are personalized for that player
def game_state_message(
    game_id,
    game,
    recipient_player,
    last_move=None,
):
    return {
        "type": "game_state",
        "game_id": game_id,
        "board": deepcopy(game.board),
        "status": game.status,
        "current_player": game.current_player,
        "assigned_player": recipient_player,
        "starting_player": game.starting_player,
        "players_connected": len(player_roles.get(game_id, {})),
        "mode": game.mode,
        "bot_player": game.bot_player,
        "winner": game.winner,
        "last_move": last_move,
        **council_metadata(game, recipient_player),
    }


# broadcast the updated game state to all connected players for the game
async def broadcast_game_state(game_id, game, last_move=None):
    # snapshot the recipients because connections can change while awaiting sends
    recipients = list(player_roles.get(game_id, {}).items())

    for recipient_player, recipient_ws in recipients:
        try:
            await recipient_ws.send_json(
                game_state_message(
                    game_id=game_id,
                    game=game,
                    recipient_player=recipient_player,
                    last_move=last_move,
                )
            )
        except (WebSocketDisconnect, RuntimeError, OSError):
            # one disconnected recipient should not stop delivery to the others
            logger.debug(
                "Could not send game state to a disconnected player.",
                exc_info=True,
            )


# send a private council error with the player's current availability
# raw provider errors and API response bodies stay on the server
async def send_council_error(
    websocket,
    game_id,
    game,
    player,
    message,
):
    await websocket.send_json(
        {
            "type": "council_error",
            "game_id": game_id,
            "message": message,
            **council_metadata(game, player),
        }
    )


# run one council request independently of the WebSocket receive loop
# this function returns advice only; it never applies a game move
async def process_council_request(
    websocket,
    game_id,
    game,
    player,
    request_token,
    board_snapshot,
    request_round,
    request_version,
):
    # a disconnected player may have been replaced by another socket
    # private advice must only go to the socket that still owns this role
    def owns_role():
        return player_roles.get(game_id, {}).get(player) is websocket

    # advice is usable only for the game, round, board, and turn it analyzed
    def same_position():
        return (
            game_manager.get_game(game_id) is game
            and game.round_id == request_round
            and game.position_version == request_version
            and game.status == "active"
            and game.current_player == player
            and game.board == board_snapshot
        )

    # remove only this request's pending marker
    # an older task should not remove a newer request's token
    def clear_pending():
        if game.council_pending.get(player) is request_token:
            game.council_pending.pop(player, None)

    try:
        if not owns_role():
            return

        # tell the requesting player that council work is starting
        await websocket.send_json(
            {
                "type": "council_pending",
                "game_id": game_id,
                **council_metadata(game, player),
            }
        )

        # the council service makes synchronous API calls
        # run it in a worker thread so other WebSocket messages can be processed
        outcome = await run_in_threadpool(
            run_guarded_council,
            board_snapshot,
            player,
        )

        # do not deliver private advice to a socket that lost ownership
        if not owns_role():
            return

        # a move or reset may have happened while the council was running
        # discard stale advice without consuming the player's council use
        if not same_position():
            clear_pending()

            await send_council_error(
                websocket,
                game_id,
                game,
                player,
                "The position changed while the council was thinking. "
                "Your use was not consumed.",
            )
            return

        final = outcome["final_recommendation"]

        # reserve the player's use immediately before delivery
        # a labelled deterministic fallback also counts as a recommendation
        clear_pending()
        game.council_used.add(player)

        try:
            # send only the guarded recommendation, not raw advisor reports
            await websocket.send_json(
                {
                    "type": "council_result",
                    "game_id": game_id,
                    **council_metadata(game, player),
                    "recommended_column": final["recommended_column"],
                    "explanation": final["explanation"],
                    "source": final["source"],
                    "fallback_reason": final["fallback_reason"],
                    "tactical_outcome": final["tactical_outcome"],
                }
            )
        except Exception:
            # restore the use after failed delivery, but do not modify
            # usage bookkeeping belonging to a newer round
            if game.round_id == request_round:
                game.council_used.discard(player)
            raise

    except (WebSocketDisconnect, RuntimeError, OSError):
        clear_pending()

        if owns_role():
            # record server-side details without exposing them to the browser
            logger.warning(
                "Council request or delivery failed.",
                exc_info=True,
            )

            try:
                await send_council_error(
                    websocket,
                    game_id,
                    game,
                    player,
                    "The council could not finish this request. "
                    "Your use was not consumed.",
                )
            except (WebSocketDisconnect, RuntimeError, OSError):
                # the requesting socket may already be disconnected
                pass

    except Exception:
        clear_pending()
        logger.exception("Unexpected council request failure.")

        if owns_role():
            try:
                await send_council_error(
                    websocket,
                    game_id,
                    game,
                    player,
                    "The council is unavailable. " "Your use was not consumed.",
                )
            except (WebSocketDisconnect, RuntimeError, OSError):
                pass

    finally:
        # always remove this request's pending marker
        clear_pending()

        # a replacement connection may have joined while the old request ran
        # refresh its availability now that the old request has finished
        replacement = player_roles.get(game_id, {}).get(player)

        if replacement is not None and replacement is not websocket:
            try:
                await replacement.send_json(
                    {
                        "type": "council_status",
                        "game_id": game_id,
                        **council_metadata(game, player),
                    }
                )
            except (WebSocketDisconnect, RuntimeError, OSError):
                pass


# define health check endpoint
@app.get("/health")
def health():
    return {"status": "ok"}


# define endpoint for retrieving a game by its ID
@app.get(
    "/games/{game_id}",
    response_model=GameResponse,
    status_code=status.HTTP_200_OK,
)
def get_game(game_id: str):
    game = game_manager.get_game(game_id)

    if game is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Game not found"},
        )

    return build_game_response(game_id, game)


# define endpoint for creating a new game
@app.post(
    "/games",
    response_model=GameResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_game(request: CreateGameRequest | None = None):
    # determine the game mode from the request,
    # defaulting to "human_vs_human" if not provided
    if request is not None:
        mode = request.mode
    else:
        mode = "human_vs_human"

    game_id, game = game_manager.create_game(mode=mode)

    # return the newly created game as a response
    return build_game_response(game_id, game)


# define endpoint for dropping a piece in a game
# this existing REST route does not enforce WebSocket player identity
# and does not broadcast its changes to connected sockets
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Game not found"},
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
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": "Column is full"},
            )

        # if the game has already finished
        elif result.reason == "game_finished":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": "Game has already finished"},
            )

        # if none of the specific reasons matched,
        # raise a generic bad request error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": result.reason},
        )

    return build_game_response(game_id, game)


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

    # accept the websocket connection
    await websocket.accept()

    # accepting yields control, so another connection may claim the last role
    # recheck availability before registering this socket
    roles = player_roles.setdefault(game_id, {})

    if len(roles) >= 2:
        await websocket.close(code=1008)
        return

    # choose an available role for the new connection
    assigned_player = RED if RED not in roles else YELLOW

    # register the websocket connection for the game
    active_connections.setdefault(game_id, set()).add(websocket)

    # register the assigned player role for the game
    roles[assigned_player] = websocket

    try:
        # send the initial game state to the connected client or clients
        # existing clients also receive the updated players_connected count
        await broadcast_game_state(game_id, game)

        while True:
            # receive the next client message using WebSocket JSON methods
            try:
                message = await websocket.receive_json()
            except ValueError:
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": "Invalid JSON message",
                    }
                )
                continue

            # valid JSON may still be a list, number, string, or null
            # require an object before reading its message type
            if not isinstance(message, dict):
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": "Messages must be JSON objects",
                    }
                )
                continue

            # verify this socket still owns its assigned player role
            roles = player_roles.get(game_id, {})

            if roles.get(assigned_player) is not websocket:
                await websocket.close(code=1008)
                return

            message_type = message.get("type")

            # handle the received move message
            if message_type == "move":
                column = message.get("column")

                # if column is not a non-boolean integer, reject the move
                if type(column) is not int:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": "Invalid column type",
                        }
                    )
                    continue

                # if the assigned player is not the current player,
                # reject the move
                if assigned_player != game.current_player:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": "It's not your turn",
                        }
                    )
                    continue

                result = game.drop_piece(column)

                if not result.success:
                    # send result.reason as an error message to the client
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": f"Move failed: {result.reason}",
                        }
                    )
                    continue

                # broadcast the updated game state to all connected clients
                # include the successful move for frontend animation
                await broadcast_game_state(
                    game_id,
                    game,
                    last_move={
                        "row": result.row,
                        "column": result.column,
                        "player": result.player,
                    },
                )

            # handle a private council recommendation request
            elif message_type == "council_request":
                # completed games do not have a next move to recommend
                if game.status != "active":
                    await send_council_error(
                        websocket,
                        game_id,
                        game,
                        assigned_player,
                        "The game has already finished.",
                    )
                    continue

                # use the server-assigned role rather than a client-supplied color
                if assigned_player != game.current_player:
                    await send_council_error(
                        websocket,
                        game_id,
                        game,
                        assigned_player,
                        "You can ask the council only on your turn.",
                    )
                    continue

                # match the frontend policy: both players must be connected
                if len(roles) != 2:
                    await send_council_error(
                        websocket,
                        game_id,
                        game,
                        assigned_player,
                        "Wait for both players to connect.",
                    )
                    continue

                # prevent duplicate work while this player's request is running
                if assigned_player in game.council_pending:
                    await send_council_error(
                        websocket,
                        game_id,
                        game,
                        assigned_player,
                        "A council request is already running.",
                    )
                    continue

                # each player color gets one delivered recommendation per round
                if assigned_player in game.council_used:
                    await send_council_error(
                        websocket,
                        game_id,
                        game,
                        assigned_player,
                        "You have already used the council this round.",
                    )
                    continue

                # claim the pending slot before scheduling the task
                # the unique token makes cleanup ownership-safe
                request_token = object()
                game.council_pending[assigned_player] = request_token

                # capture the current board and identifiers before background work
                # the council must not analyze the live mutable board
                task = asyncio.create_task(
                    process_council_request(
                        websocket=websocket,
                        game_id=game_id,
                        game=game,
                        player=assigned_player,
                        request_token=request_token,
                        board_snapshot=deepcopy(game.board),
                        request_round=game.round_id,
                        request_version=game.position_version,
                    )
                )

                # retain the task until completion, then remove its reference
                council_tasks.add(task)
                task.add_done_callback(council_tasks.discard)

            # handle the received reset message
            elif message_type == "reset":
                # socket ownership was checked above for every supported action
                # GameState allows resets only after a win or draw
                if not game.reset_game():
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": "Only completed games can be reset",
                        }
                    )
                    continue

                # broadcast the new round and restored council availability
                # last_move defaults to None so the old animation is cleared
                await broadcast_game_state(game_id, game)

            else:
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": "Unsupported Message type",
                    }
                )

    except WebSocketDisconnect:
        # a normal disconnect still runs the cleanup below
        pass

    finally:
        # remove the websocket connection from the active connections set
        # when the client disconnects
        connections = active_connections.get(game_id)

        if connections is not None:
            connections.discard(websocket)

        # if there are no more connections for the game,
        # remove the game_id from active_connections
        if connections is not None and not connections:
            active_connections.pop(game_id, None)

        # retrieve the actual role mapping, or None if the game has no roles
        roles = player_roles.get(game_id)

        # safely remove only this endpoint's own role
        # do not remove a role now owned by a replacement connection
        if roles is not None and roles.get(assigned_player) is websocket:
            roles.pop(assigned_player, None)

        # if there are no more roles for the game,
        # remove the game_id from player_roles
        if roles is not None and not roles:
            player_roles.pop(game_id, None)

        # notify remaining players that the connection count changed
        await broadcast_game_state(game_id, game)
