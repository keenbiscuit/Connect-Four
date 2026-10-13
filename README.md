# Real-Time Multiplayer Connect Four

A full-stack, real-time multiplayer Connect Four application built with **Python, FastAPI, WebSockets, and React**.

Two players can join the same game, take turns in real time, receive synchronized board updates, see win/loss results, and start a new round with Play Again. The FastAPI backend is server-authoritative: it validates player identity, turn order, moves, wins, draws, and rematches.

> Deployment in progress  
> Frontend: Vercel  
> Backend: Render

## Live Demo

- Frontend: Coming soon
- API: Coming soon
- API documentation: Coming soon

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

The application uses a server-authoritative design.

- The React client displays the board and sends player actions.
- FastAPI owns game creation, move validation, turn order, win detection, and draw detection.
- The `GameManager` stores active games in memory.
- Each `GameState` owns its board, current player, move history, and game-completion logic.
- WebSockets deliver authoritative game-state messages to connected clients.
- The client treats server responses as the source of truth.

```text
React Client
    │
    ├── REST: Create and retrieve games
    │
    └── WebSocket: Receive real-time game state
                │
                ▼
         FastAPI Backend
                │
                ├── GameManager
                └── GameState
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

A client connects to a game-specific WebSocket endpoint. For a valid game, the server sends an immediate authoritative state message.

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
  "current_player": RED or YELLOW,
  "assigned_player" : RED or YELLOW,
  "player_count" : 1,
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

## Local Development

### Backend

From the repository root:

```bash
cd backend
python -m venv .venv
```

Activate the virtual environment:

```bash
# macOS/Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the API:

```bash
uvicorn main:app --reload
```

The FastAPI API will be available at:

```text
http://localhost:8000/health
```

Interactive API documentation:

```text
http://localhost:8000/docs
```

### Frontend

From the repository root:

```bash
cd frontend
npm install
npm run dev
```

Set the local backend values in the frontend environment configuration:

```text
VITE_API_BASE_URL=http://localhost:5173
VITE_WS_BASE_URL=ws://localhost:5173
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
- Initial WebSocket game-state delivery

GitHub Actions runs the backend test suite on each relevant push and pull request.

## Deployment

The app is deployed as two services:

| Service | Platform | Responsibility |
|---|---|---|
| Frontend | Vercel | Serves the React application |
| Backend | Render | Runs the FastAPI REST and WebSocket API |

### Backend: Render

Render deploys the backend from the repository’s `backend` directory.

```text
Root Directory: backend
Build Command: pip install -r requirements.txt
Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT
```

### Frontend: Vercel

Vercel deploys the frontend from the repository’s `frontend` directory.

Set these Vercel environment variables:

```text
VITE_API_BASE_URL=[https://YOUR-RENDER-SERVICE.onrender.com](https://YOUR-RENDER-SERVICE.onrender.com)
VITE_WS_BASE_URL=wss://YOUR-RENDER-SERVICE.onrender.com
```

After Vercel creates the production URL, configure FastAPI CORS to allow that exact frontend origin.

## Current Limitations

- Active games are stored in memory.
- Game state resets if the backend restarts or is redeployed.
- Persistent completed-game history has not yet been added.
- Redis Pub/Sub is intentionally deferred until the core multiplayer experience is complete.

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
- [ ] Deploy FastAPI/WebSocket backend to Render
- [ ] Deploy React frontend to Vercel
- [ ] Add an AI power-up that suggests or plays one strategically selected move per player per game
- [ ] Persist completed games with MongoDB
- [ ] Add Redis Pub/Sub when multi-instance scaling is needed