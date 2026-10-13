# Real-Time Multiplayer Connect Four

A full-stack, real-time multiplayer Connect Four application built with **React, Python, FastAPI, and WebSockets**.

Two players can join the same game, take turns in real time, see synchronized board updates, receive win/loss results, and start a new round with Play Again. The FastAPI backend is server-authoritative: it owns player assignment, game state, turn validation, moves, wins, draws, and rematches.

> Live deployment  
> Frontend: Vercel  
> Backend: Render

## Live Demo

- **Play the game:** https://connect-four-bice-nu.vercel.app
- **Backend API:** https://connect-four-wbku.onrender.com
- **Interactive API docs:** https://connect-four-wbku.onrender.com/docs

## Features

- Real-time two-player Connect Four matches
- Interactive React board with column controls, player status, results, and Play Again UI
- Create or join a game using a game ID
- Red and Yellow player assignment
- Server-authoritative player identity and turn validation
- Synchronized board and game-status updates through WebSockets
- Standard 6×7 Connect Four game rules
- Gravity-based piece placement
- Horizontal, vertical, and diagonal win detection
- Draw detection
- Winner sees “You won”; opponent sees “You lost”
- Server-authoritative Play Again flow
- Board resets for both connected players
- Starting player switches between rounds
- REST API for game creation and initial state retrieval
- Automated backend tests with GitHub Actions CI

## Play Again / Rematch Behavior

After a win or draw, either player can request a new round using Play Again.

The server resets the existing game rather than creating disconnected client-side state:

1. The server clears the board.
2. The server clears the previous winner and completed-game status.
3. The server preserves the two players connected to the game.
4. The server switches the starting player for the new round.
5. The server broadcasts the new authoritative game state to both clients.

This ensures both players begin the rematch from the same state and that neither client can independently choose who moves first.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React |
| Backend | Python, FastAPI |
| Real-time communication | WebSockets |
| Testing | Pytest, FastAPI TestClient |
| CI | GitHub Actions |
| Backend hosting | Render |
| Frontend hosting | Vercel |
| Planned persistence | MongoDB |
| Planned real-time scaling | Redis Pub/Sub |

## Architecture

The application uses a server-authoritative, event-driven multiplayer design.

- The React client renders the board, column controls, player status, match result, and Play Again action.
- FastAPI owns the authoritative game state and validates every player action.
- `GameManager` stores active games, player assignments, and per-game WebSocket connections in memory.
- `GameState` owns the board, current player, move application, win/draw evaluation, and round-reset behavior.
- Clients use REST to create games and WebSockets for player assignment, game actions, and synchronized state updates.
- The server validates moves and rematches, then broadcasts authoritative state to both connected players.

```text
Player 1 React Client                 Player 2 React Client
          │                                      │
          └──────────── WebSockets ──────────────┘
                           │
                           ▼
                 FastAPI Game Server
                           │
       ┌───────────────────┼───────────────────┐
       ▼                   ▼                   ▼
  GameManager         GameState        Connection Tracking
       │                   │                   │
       └───────── Authoritative state ─────────┘
```

## Game Rules

- The board has 6 rows and 7 columns.
- Red is represented by `1`; Yellow is represented by `2`.
- A move selects a column, and the piece falls to the lowest open row.
- Players alternate turns unless the move ends the game.
- The first player to connect four pieces horizontally, vertically, or diagonally wins.
- If the board fills without a winner, the game ends in a draw.

## Real-Time Game Flow

1. A player creates a game through the REST API.
2. Both players connect to `/ws/games/{game_id}`.
3. The server assigns or recognizes each player’s game identity.
4. The server sends the current authoritative game state.
5. A player sends a move through their WebSocket connection.
6. The server validates player identity, turn, game status, and the selected column.
7. The server applies valid moves and broadcasts the updated state to both players.
8. At game completion, each client renders a result relative to its assigned player color.
9. When a player chooses Play Again, the server resets the existing game, alternates the starting player, and broadcasts the reset state to both clients.

## API

### Create a game

```text
POST /games
```

Creates a new game and returns its complete initial state.

The starting player alternates between Red and Yellow for newly created games.

### Get game state

```text
GET /games/{game_id}
```

Returns the complete authoritative state for a game.

### Make a move

```text
POST /games/{game_id}/moves
```

Submits a move for the current player.

The backend validates:

- The game exists
- The selected column is valid
- The selected column is not full
- The game has not already ended
- The move follows the current server-owned turn state

### WebSocket game state

```text
/ws/games/{game_id}
```

A client connects to a game-specific WebSocket endpoint. The server assigns the client a player role when applicable, sends the current authoritative state, and broadcasts updated state after valid moves and rematches.

```json
{
  "type": "game_state",
  "game_id": "example-game-id",
  "board": [
   ,[0]
   ,[0]
   ,[0]
   ,[0]
   ,[0]
[0]
  ],
  "status": "active",
  "current_player": 1,
  "assigned_player": 1,
  "player_count": 1,
  "winner": null
}
```

## Error Handling

| Scenario | HTTP status |
|---|---:|
| Unknown game | 404 |
| Invalid column | 422 |
| Attempted move in a full column | 409 |
| Attempted move after game completion | 409 |

## Run Locally

### Backend

From the repository root:

```bash
python -m venv .venv
```

Activate it, then install dependencies:

```bash
pip install -r requirements.txt
```

Start FastAPI:

```bash
uvicorn backend.app.main:app --reload
```

Open API documentation at:

```text
http://localhost:8000/docs
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

## Testing

Run backend tests from the repository root:

```bash
python -m pytest backend/tests --maxfail=1 --disable-warnings -q
```

The test suite covers:

- Game creation
- Initial-player alternation
- Board initialization
- Piece gravity
- Turn changes
- Horizontal, vertical, and diagonal wins
- Draws
- Invalid moves and API error responses
- WebSocket connection, player assignment, move validation, state broadcasts, and rematch behavior

GitHub Actions runs the backend test suite on each relevant push and pull request.

## Deployment

| Component | Platform | Purpose |
|---|---|---|
| React frontend | Vercel | Hosts the browser-based game UI |
| FastAPI backend | Render | Hosts REST endpoints, WebSocket connections, and server-authoritative game logic |

The frontend calls the backend with HTTPS and opens secure WebSocket connections with `wss://`.

### Production configuration

The Vercel frontend uses these build-time environment variables:

```text
VITE_API_BASE_URL=https://connect-four-wbku.onrender.com
VITE_WS_BASE_URL=wss://connect-four-wbku.onrender.com
```

The FastAPI backend allows requests from:

```text
http://localhost:5173
https://connect-four-bice-nu.vercel.app
```

## Current Limitations

- Active games and live connections are stored in memory.
- A backend restart or redeploy clears active games and disconnects players.
- The Render free-tier backend may spin down after 15 minutes with no traffic; the first request afterward can take roughly a minute while the service restarts.
- Completed-game persistence and multi-instance scaling are planned future enhancements.

## Roadmap

- [x] REST game creation, retrieval, and move APIs
- [x] Server-authoritative Connect Four rules
- [x] Interactive React UI and game controls
- [x] Per-game WebSocket connection tracking
- [x] Player assignment and turn validation
- [x] WebSocket move events
- [x] Real-time state broadcasts to both players
- [x] Winner, loser, and draw UI states
- [x] Server-authoritative Play Again / rematch flow
- [x] Alternating starting player across rounds
- [x] Automated backend tests and GitHub Actions CI
- [x] Deploy FastAPI/WebSocket backend to Render
- [x] Deploy React frontend to Vercel
- [ ] Add Human vs Bot mode
- [ ] Add a limited-use AI power-up that suggests a strategic legal move while the player retains final move choice
- [ ] Persist completed games with MongoDB
- [ ] Add Redis Pub/Sub when multi-instance scaling is needed