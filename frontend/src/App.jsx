import "./App.css";
import { useEffect, useState, useRef } from "react";
import.meta.env.VITE_API__BASE_URL;
import.meta.env.VITE_WS_BASE__URL;

const EMPTY = 0;
const RED = 1;
const YELLOW = 2;

// const sampleGame = {
//   board: [
//     [0, 0, 0, 0, 0, 0, 0],
//     [0, 0, 0, 0, 0, 0, 0],
//     [0, 0, 0, 0, 0, 0, 0],
//     [0, 0, 0, 0, 0, 0, 0],
//     [0, 0, 0, 2, 0, 0, 0],
//     [0, 0, 0, 1, 0, 0, 0],
//   ],
//   current_player: RED,
//   assigned_player: RED,
//   status: "active",
//   winner: null,
// };

function playerName(player) {
  if (player === RED) return "Red";
  if (player === YELLOW) return "Yellow";
  return "Unassigned";
}

function cellColor(cell) {
  if (cell === RED) return "red";
  if (cell === YELLOW) return "yellow";
  return "empty";
}

function turnMessage(game) {
  if (game.winner !== null) {
    return `${playerName(game.winner)} wins`;
  }

  if (game.status !== "active") {
    return "Game finished";
  }

  return game.current_player === game.assigned_player
    ? "Your turn"
    : `${playerName(game.current_player)}’s turn`;
}

function PlayerCard({ player, assignedPlayer, currentPlayer, isActive }) {
  const color = cellColor(player);
  const isYou = player === assignedPlayer;
  const hasTurn = isActive && player === currentPlayer;

  return (
    <div className={`player-card ${hasTurn ? "player-card-active" : ""}`}>
      <span
        className={`player-piece player-piece-${color}`}
        aria-hidden="true"
      />

      <div className="player-details">
        <span className="player-name">{playerName(player)}</span>
        <span className="player-description">
          {isYou ? "Your pieces" : "Other player’s pieces"}
        </span>
      </div>

      {hasTurn && <span className="turn-badge">Turn</span>}
    </div>
  );
}

function Board({ board, cantClick, onColumnClick, lastMove, resultMessage }) {
  return (
    <div className="board-panel">
      <div className="column-controls" aria-label="Column controls">
        {board[0].map((_, columnIndex) => (
          <button
            key={columnIndex}
            className="column-button"
            disabled
            type="button"
            aria-label={`Drop a piece in column ${columnIndex + 1}; unavailable in preview`}
          >
            <span>{columnIndex + 1}</span>
            <span className="column-arrow" aria-hidden="true">
              ↓
            </span>
          </button>
        ))}
      </div>

      <div className="board-wrapper" id="board-wrapper">
        <div className="board" aria-label="Connect Four board">
          {[...board].reverse().map((row, rowIndex) => (
            <div className="board-row" key={rowIndex}>
              {row.map((cell, columnIndex) => {
                const backendRow = board.length - 1 - rowIndex;

                const isLastMove =
                  lastMove != null &&
                  backendRow === lastMove.row &&
                  columnIndex === lastMove.column;

                return (
                  <button
                    style={{ "--drop-steps": rowIndex + 1 }}
                    className={`board-cell board-cell-${cellColor(cell)}${
                      isLastMove ? " piece-drop" : ""
                    }`}
                    disabled={cantClick || cell != EMPTY}
                    onClick={() => onColumnClick(columnIndex)}
                    key={`${rowIndex}-${columnIndex}`}
                    type="button"
                    aria-label={`Row ${rowIndex + 1}, column ${columnIndex + 1}: ${
                      cell === EMPTY ? "Empty" : playerName(cell)
                    }`}
                  />
                );
              })}
            </div>
          ))}
        </div>
        {resultMessage && (
          <div className="result-overlay">
            <div className="result-content">
              <h2>{resultMessage}</h2>
            </div>
          </div>
        )}
      </div>

      <div className="board-footer">
        <span>6 rows × 7 columns</span>
        <span>Connect four to win</span>
      </div>
    </div>
  );
}

function App() {
  const [screen, setScreen] = useState("welcome");
  const [gameId, setGameId] = useState(null);
  const [connectionStatus, setConnectionStatus] = useState(null);
  const [receivedGameData, setReceivedGameData] = useState(null);
  const [joinGameId, setJoinGameId] = useState("");
  const [cantPlay, setCantPlay] = useState(true);
  const websocket = useRef(null);

  // Websocket Connection
  useEffect(() => {
    if (gameId != null) {
      
      const WS_URL =  import.meta.env.VITE_WS_BASE_URL ?? "ws://localhost:5173"
      const socket = new WebSocket(WS_URL + "/ws/games/" + gameId);
      websocket.current = socket;

      socket.onopen = () => {
        setConnectionStatus("Connected");
        console.log("Connection Opened");
      };

      socket.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data["type"] === "game_state") {
          console.log("Recieved: ", data);
          setReceivedGameData(data);

          // If not the current player, no move can be made
          if (
            (data["assigned_player"] === RED ||
              data["assigned_player"] === YELLOW) &&
            data["assigned_player"] === data["current_player"] &&
            data["status"] === "active" &&
            data["players_connected"] == 2
          ) {
            setCantPlay(false);
          } else {
            setCantPlay(true);
          }
          setScreen("game");
        }
      };

      socket.onclose = () => {
        setConnectionStatus("Disconnected");
      };
      // Function saved for cleanup
      return () => {
        socket.close();
      };
    }
  }, [gameId]);
  
  // Create Game Button
  async function handleCreateGame() {
    setScreen("creating");
    const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "";
    // Create game via API POST request
    try {
      const response = await fetch(baseUrl + "/games", {
        method: "POST",
      });
      if (!response.ok) {
        throw new Error("Network response was not ok");
      }
      const json = await response.json();
      setGameId(json["game_id"]);
      setTimeout(() => setScreen("game"), 500);
    } catch (error) {
      console.error("Fetch Error: ", error);
      setTimeout(() => setScreen("welcome"), 500);
    }
  }

  function handleJoinGame() {
    const text = joinGameId.replace(/\s/g, "");

    if (joinGameId != "") {
      setGameId(text);
    }
  }
  function handleResetGame() {
    const socket = websocket.current;

    if (!socket || socket.readyState !== WebSocket.OPEN) {
      return;
    }

    socket.send(JSON.stringify({ type: "reset" }));
  }

  function columnClickHandler(columnIndex) {
    if (websocket.current?.readyState === WebSocket.OPEN) {
      const move = {
        type: "move",
        column: columnIndex,
      };
      websocket.current.send(JSON.stringify(move));
    }
  }
  let message = null;

  if (receivedGameData?.status === "win") {
    if (receivedGameData["winner"] === receivedGameData["assigned_player"]) {
      message = "YOU WON! :)";
    } else {
      message = "YOU LOST! :(";
    }
  } else if (receivedGameData?.status === "draw") {
    message = "IT WAS A DRAW!";
  }

  return (
    <div className="app-shell">
      <header className="site-header">
        <a className="brand" href="./" aria-label="Connect Four home">
          <span className="brand-mark" aria-hidden="true">
            <span />
            <span />
            <span />
            <span />
          </span>
          <span>Connect Four</span>
        </a>

        <span className="preview-badge">
          <span className="preview-dot" aria-hidden="true" />
          Connected
        </span>
      </header>

      {screen === "welcome" ? (
        <main className="game-layout">
          <section className="play-area" aria-labelledby="welcome-title">
            <div className="game-heading">
              <p className="eyebrow">A little strategy. A good rivalry.</p>
              <h1 id="welcome-title">Your next rivalry starts here.</h1>
              <p className="heading-description">
                Challenge a friend. Take turns dropping pieces. Connect four
                before they do.
              </p>
            </div>

            <section
              className="rules-card"
              aria-labelledby="welcome-rules-title"
              style={{ marginTop: "28px" }}
            >
              <h2 id="welcome-rules-title">
                Simple to learn. Worth another round.
              </h2>
              <p>
                Connect four of your pieces horizontally, vertically, or
                diagonally. Every piece falls to the lowest open space.
              </p>

              <div className="winning-line" aria-hidden="true">
                <span />
                <span />
                <span />
                <span />
              </div>
            </section>
          </section>

          <section className="sidebar-card" aria-labelledby="setup-title">
            <p className="eyebrow">Bring a friend</p>
            <h2 id="setup-title" className="setup-title">
              Let’s play.
            </h2>
            <p className="card-description">
              Create a game and share its ID, or join a game your friend
              created.
            </p>

            <button
              className="create-game-button"
              type="button"
              onClick={() => {
                handleCreateGame();
              }}
            >
              Create game
              <span aria-hidden="true">↗</span>
            </button>

            <div className="divider">
              <span>or join an existing game</span>
            </div>

            <label className="input-label" htmlFor="game-id">
              Game ID
            </label>
            <input
              id="game-id"
              className="game-input"
              type="text"
              placeholder="Enter a game ID"
              value={joinGameId}
              onChange={(event) => {
                setJoinGameId(event.target.value);
              }}
            />

            <button
              className="join-game-button"
              type="button"
              onClick={() => {
                handleJoinGame();
              }}
            >
              Join game
            </button>
          </section>
        </main>
      ) : screen === "game" ? (
        <main className="game-layout">
          <section className="play-area" aria-labelledby="game-title">
            <div className="game-heading">
              <p className="eyebrow">Head to Head</p>
              <h1 id="game-title">Make your next move.</h1>
              <p className="heading-description">
                Two players. Seven columns. One winning connection.
              </p>
            </div>

            <div className="turn-panel">
              <div className="turn-copy">
                <span
                  className={`turn-indicator turn-indicator-${receivedGameData["current_player"]}`}
                  aria-hidden="true"
                />
                <div>
                  <h2>{turnMessage(receivedGameData)}</h2>
                  <p>
                    {receivedGameData["status"] === "active"
                      ? "Choose a column to drop your piece."
                      : "This game is complete."}
                  </p>
                </div>
              </div>

              <span className="sample-label">Sample position</span>
            </div>

            <Board
              board={receivedGameData["board"]}
              onColumnClick={columnClickHandler}
              cantClick={cantPlay}
              lastMove={receivedGameData?.last_move ?? null}
              resultMessage={message}
            />
            {(receivedGameData?.status === "win" ||
              receivedGameData?.status === "draw") && (
              <button
                type="button"
                className="reset-game-button"
                onClick={handleResetGame}
              >
                Play again
              </button>
            )}

            <p className="preview-note">
              Good Luck Player {playerName(receivedGameData["current_player"])}
            </p>
          </section>

          <aside className="sidebar" aria-label="Game details">
            <section className="sidebar-card" aria-labelledby="players-title">
              <div className="card-heading">
                <h2 id="players-title">Players</h2>
                <span className="subtle-label">Sample roles</span>
              </div>

              <div className="player-list">
                <PlayerCard
                  player={RED}
                  assignedPlayer={receivedGameData["assigned_player"]}
                  currentPlayer={receivedGameData["current_player"]}
                  isActive={receivedGameData["status"]}
                />
                <PlayerCard
                  player={YELLOW}
                  assignedPlayer={receivedGameData["assigned_player"]}
                  currentPlayer={receivedGameData["current_player"]}
                  isActive={receivedGameData["status"]}
                />
              </div>

              <div className="game-facts">
                <div>
                  <span>Your color:</span>
                  <span>{playerName(receivedGameData["assigned_player"])}</span>
                </div>
                <div>
                  <span>Game status:</span>
                  <span className="status-value">
                    {receivedGameData["status"]}
                  </span>
                </div>
                <div>
                  <span>Game Id:</span>
                  <span className="status-value">{gameId}</span>
                </div>
                <div>
                  <span>Connection:</span>
                  <span>{connectionStatus}</span>
                </div>
              </div>
            </section>

            <button
              className="join-game-button"
              type="button"
              onClick={() => setScreen("welcome")}
            >
              Back to welcome
            </button>
          </aside>
        </main>
      ) : screen === "creating" ? (
        <div>
          <h1 className="transition-title">Creating...</h1>
        </div>
      ) : null}

      <footer className="site-footer">
        <span>Built for a good game.</span>
        <span>React client · FastAPI backend</span>
      </footer>
    </div>
  );
}

export default App;
