import "./App.css";
import { useEffect, useState, useRef } from "react";
import.meta.env.VITE_API__BASE_URL;
import.meta.env.VITE_WS_BASE__URL;

const EMPTY = 0;
const RED = 1;
const YELLOW = 2;

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
    : `${playerName(game.current_player)}'s turn`;
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
          {isYou ? "Your pieces" : "Other player's pieces"}
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

// display private council advice without applying a new move
// The backend is responsible for turn validation and council use
function CouncilPanel({
  game,
  connected,
  pending,
  remaining,
  advice,
  error,
  onRequest,
}) {
  const canRequest =
    connected &&
    game.status === "active" &&
    game.players_connected === 2 &&
    game.current_player === game.assigned_player &&
    remaining === 1 &&
    !pending;

  let hint = "One private recommendation per player, per round.";

  if (!connected) {
    hint = "Connect to the game to consult the council";
  } else if (pending) {
    hint = "The advisors are reviewing your position.";
  } else if (game.status !== "active") {
    hint = "A new round restores your council use.";
  } else if (remaining === 0) {
    hint = "You have used the council this round.";
  } else if (game.players_connected !== 2) {
    hint = "Wait for both players to connect.";
  } else if (game.current_player !== game.assigned_player) {
    hint = "You can only consult the council on your turn.";
  }

  return (
    <section
      className="sidebar-card council-card"
      aria-labelledby="council-title"
      aria-busy={pending}
    >
      <div className="council-heading">
        <div>
          <p className="eyebrow">Your strategic timeout</p>
          <h2 id="council-title">Ask the council</h2>
        </div>

        <span className={`council-credit ${remaining === 0 ? "is-spent" : ""}`}>
          {remaining} / 1
        </span>
      </div>

      <p className="card-description">
        An attacker, a defender, and a captain review your position. Local
        tactical checks guard the final recommendation.
      </p>

      <button
        className="council-button"
        type="button"
        disabled={!canRequest}
        onClick={onRequest}
      >
        {pending ? (
          <>
            <span className="council-spinner" aria-hidden="true" />
            Council is thinking…
          </>
        ) : remaining === 0 ? (
          "Used this round"
        ) : (
          "Get my recommendation"
        )}
      </button>

      <p className="council-hint">{hint}</p>

      <div aria-live="polite" aria-atomic="true">
        {advice && (
          <div className="council-result">
            <div className="council-result-heading">
              <span className="council-result-label">Recommended move</span>

              {/* Display columns as 1–7; backend columns remain 0–6. */}
              <span className="council-column">
                Column {advice.recommended_column + 1}
              </span>
            </div>

            <p>{advice.explanation}</p>

            <span className="council-source">
              {advice.source === "captain"
                ? "Captain recommendation · tactical check passed"
                : "Local tactical fallback"}
            </span>

            <p className="council-result-note">
              Advice only. Choose the column yourself to play.
            </p>
          </div>
        )}

        {error && <p className="council-error">{error}</p>}
      </div>
    </section>
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

  // private council display state and server reported availability
  const [councilPending, setCouncilPending] = useState(false);
  const [councilRemaining, setCouncilRemaining] = useState(1);
  const [councilAdvice, setCouncilAdvice] = useState(null);
  const [councilError, setCouncilError] = useState("");

  // refs keep callbacks current and block duplicate requests
  // immediately, before React finishes rendering update state
  const latestGame = useRef(null);
  const councilRequestInFlight = useRef(false);

  // Websocket Connection
  useEffect(() => {
    if (gameId != null) {
      //discared advice and availability from a previously selected game
      latestGame.current = null;
      councilRequestInFlight.current = false;
      setReceivedGameData(null);
      setCantPlay(true);
      setCouncilPending(false);
      setCouncilRemaining(1);
      setCouncilAdvice(null);
      setCouncilError("");

      // ignore callbacks from this socket after cleanup
      let disposed = false;

      const WS_URL = import.meta.env.VITE_WS_BASE_URL ?? "ws://localhost:5173";

      const socket = new WebSocket(WS_URL + "/ws/games/" + gameId);
      websocket.current = socket;

      socket.onopen = () => {
        if (disposed) return;

        setConnectionStatus("Connected");
        console.log("Connection Opened");
      };

      socket.onmessage = (event) => {
        if (disposed) return;

        const data = JSON.parse(event.data);

        if (data["type"] === "game_state") {
          console.log("Recieved: ", data);

          // advice is only available for the round and position it analyzed
          const previous = latestGame.current;

          if (
            previous &&
            (previous.round_id !== data.round_id ||
              previous.position_version !== data.position_version)
          ) {
            setCouncilAdvice(null);
            setCouncilError("");
          }

          latestGame.current = data;
          setReceivedGameData(data);

          // use server owned availability, including after reconnect/reset
          const pending = Boolean(data.council_pending);

          setCouncilRemaining(data.council_remaining ?? 1);
          setCouncilPending(pending);
          councilRequestInFlight.current = pending;

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
          return;
        }

        // handle private council messages separately from game state
        if (
          data.type === "council_pending" ||
          data.type === "council_result" ||
          data.type === "council_error" ||
          data.type === "council_status"
        ) {
          const game = latestGame.current;

          // Ignore messages belonging to a different game or round
          if (
            !game ||
            data.game_id !== game.game_id ||
            data.round_id !== game.round_id
          ) {
            return;
          }

          // Never display a recommendation for an outdated board position
          if (
            data.type === "council_result" &&
            data.position_version !== game.position_version
          ) {
            return;
          }

          const pending = Boolean(data.council_pending);

          councilRequestInFlight.current = pending;
          setCouncilPending(pending);
          setCouncilRemaining(data.council_remaining);

          if (data.type === "council_pending") {
            setCouncilAdvice(null);
            setCouncilError("");
          } else if (data.type === "council_result") {
            setCouncilAdvice(data);
            setCouncilError("");
          } else if (data.type === "council_error") {
            setCouncilError(data.message);
          }
        }
      };

      socket.onclose = () => {
        if (disposed) return;

        setConnectionStatus("Disconnected");

        // disconnected clients cant move or start council work
        setCantPlay(true);
        setCouncilPending(false);
        councilRequestInFlight.current = false;
      };

      // Function saved for cleanup
      return () => {
        disposed = true;

        if (websocket.current == socket) {
          websocket.current = null;
        }

        socket.close();
      };
    }
  }, [gameId]);

  // Create Game Button
  async function handleCreateGame() {
    setScreen("creating");
    const baseUrl = (import.meta.env.VITE_API_BASE_URL || "").replace(
      /\/$/,
      "",
    );
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

  // request advice only using message type
  // the server obtains the board and player identity from its own game state
  function handleCouncilRequest() {
    const socket = websocket.current;
    const game = latestGame.current;

    if (
      !socket ||
      socket.readyState !== WebSocket.OPEN ||
      !game ||
      councilRequestInFlight.current ||
      councilRemaining !== 1 ||
      game.status !== "active" ||
      game.players_connected !== 2 ||
      game.current_player !== game.assigned_player
    ) {
      return;
    }

    // block duplicate clicks while waiting for server confirmation
    councilRequestInFlight.current = true;
    setCouncilPending(true);
    setCouncilAdvice(null);
    setCouncilError("");

    try {
      socket.send(JSON.stringify({ type: "council_request" }));
    } catch {
      councilRequestInFlight.current = false;
      setCouncilPending(false);
      setCouncilError("Could not send the council request.");
    }
  }

  function columnClickHandler(columnIndex) {
    // avoid changing position while the client waits for advice
    if (councilRequestInFlight.current) return;

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
            {/*pause local board clicks while advice is being generated */}
            <Board
              board={receivedGameData["board"]}
              onColumnClick={columnClickHandler}
              cantClick={cantPlay || councilPending}
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
            {/*private recommendation and one-use-per-round availability. */}
            <CouncilPanel
              game={receivedGameData}
              connected={connectionStatus === "Connected"}
              pending={councilPending}
              remaining={councilRemaining}
              advice={councilAdvice}
              error={councilError}
              onRequest={handleCouncilRequest}
            />

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
