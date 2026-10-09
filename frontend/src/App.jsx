import './App.css'

const EMPTY = 0
const RED = 1
const YELLOW = 2

const sampleGame = {
  board: [
    [0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 2, 0, 0, 0],
    [0, 0, 0, 1, 0, 0, 0],
  ],
  current_player: RED,
  assigned_player: RED,
  status: 'active',
  winner: null,
}

function playerName(player) {
  if (player === RED) return 'Red'
  if (player === YELLOW) return 'Yellow'
  return 'Unassigned'
}

function cellColor(cell) {
  if (cell === RED) return 'red'
  if (cell === YELLOW) return 'yellow'
  return 'empty'
}

function turnMessage(game) {
  if (game.winner !== null) {
    return `${playerName(game.winner)} wins`
  }

  if (game.status !== 'active') {
    return 'Game finished'
  }

  return game.current_player === game.assigned_player
    ? 'Your turn'
    : `${playerName(game.current_player)}’s turn`
}

function PlayerCard({ player, assignedPlayer, currentPlayer, isActive }) {
  const color = cellColor(player)
  const isYou = player === assignedPlayer
  const hasTurn = isActive && player === currentPlayer

  return (
    <div className={`player-card ${hasTurn ? 'player-card-active' : ''}`}>
      <span className={`player-piece player-piece-${color}`} aria-hidden="true" />

      <div className="player-details">
        <span className="player-name">{playerName(player)}</span>
        <span className="player-description">
          {isYou ? 'Your pieces' : 'Other player’s pieces'}
        </span>
      </div>

      {hasTurn && <span className="turn-badge">Turn</span>}
    </div>
  )
}

function Board({ board }) {
  return (
    <div className="board-panel">
      <div className="column-controls" aria-label="Column controls">
        {board[0].map((_, columnIndex) => (
          <button
            key={columnIndex}
            className="column-button"
            type="button"
            disabled
            aria-label={`Drop a piece in column ${columnIndex + 1}; unavailable in preview`}
          >
            <span>{columnIndex + 1}</span>
            <span className="column-arrow" aria-hidden="true">↓</span>
          </button>
        ))}
      </div>

      <div className="board" aria-label="Connect Four board">
        {board.map((row, rowIndex) => (
          <div className="board-row" key={rowIndex}>
            {row.map((cell, columnIndex) => (
              <div
                className={`board-cell board-cell-${cellColor(cell)}`}
                key={columnIndex}
                role="img"
                aria-label={`Row ${rowIndex + 1}, column ${columnIndex + 1}: ${
                  cell === EMPTY ? 'Empty' : playerName(cell)
                }`}
              />
            ))}
          </div>
        ))}
      </div>

      <div className="board-footer">
        <span>6 rows × 7 columns</span>
        <span>Connect four to win</span>
      </div>
    </div>
  )
}

function App() {
  const game = sampleGame
  const isActive = game.status === 'active'
  const currentColor = cellColor(game.current_player)

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
          UI preview
        </span>
      </header>

      <main className="game-layout">
        <section className="play-area" aria-labelledby="game-title">
          <div className="game-heading">
            <div>
              <p className="eyebrow">A little strategy. A good rivalry.</p>
              <h1 id="game-title">Make your next move.</h1>
              <p className="heading-description">
                Two players. Seven columns. One winning connection.
              </p>
            </div>
          </div>

          <div className="turn-panel">
            <div className="turn-copy">
              <span
                className={`turn-indicator turn-indicator-${currentColor}`}
                aria-hidden="true"
              />
              <div>
                <h2>{turnMessage(game)}</h2>
                <p>
                  {isActive
                    ? 'Choose a column when the live game is connected.'
                    : 'This game is complete.'}
                </p>
              </div>
            </div>

            <span className="sample-label">Sample position</span>
          </div>

          <Board board={game.board} />

          <p className="preview-note">
            Presentation preview only. Column controls will become available
            after backend integration.
          </p>
        </section>

        <aside className="sidebar" aria-label="Game details and setup">
          <section className="sidebar-card" aria-labelledby="players-title">
            <div className="card-heading">
              <h2 id="players-title">Players</h2>
              <span className="subtle-label">Sample roles</span>
            </div>

            <div className="player-list">
              <PlayerCard
                player={RED}
                assignedPlayer={game.assigned_player}
                currentPlayer={game.current_player}
                isActive={isActive}
              />
              <PlayerCard
                player={YELLOW}
                assignedPlayer={game.assigned_player}
                currentPlayer={game.current_player}
                isActive={isActive}
              />
            </div>

            <div className="game-facts">
              <div>
                <span>Your color</span>
                <span>{playerName(game.assigned_player)}</span>
              </div>
              <div>
                <span>Game status</span>
                <span className="status-value">{game.status}</span>
              </div>
              <div>
                <span>Connection</span>
                <span>Not connected</span>
              </div>
            </div>
          </section>

          <section className="sidebar-card" aria-labelledby="play-title">
            <p className="eyebrow">Bring a friend</p>
            <h2 id="play-title" className="setup-title">Start a rivalry.</h2>
            <p className="card-description">
              Create a game and share its ID, or join a game your friend created.
            </p>

            <button className="primary-button" type="button" disabled>
              Create game
              <span aria-hidden="true">↗</span>
            </button>

            <div className="divider">
              <span>or join an existing game</span>
            </div>

            <label className="input-label" htmlFor="game-id">Game ID</label>
            <input
              id="game-id"
              className="game-input"
              type="text"
              placeholder="Enter a game ID"
              disabled
            />

            <button className="secondary-button" type="button" disabled>
              Join game
            </button>

            <p className="setup-note">
              Create and join controls are unavailable in this preview.
            </p>
          </section>

          <section className="rules-card" aria-labelledby="rules-title">
            <h2 id="rules-title">Four in a row.</h2>
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
        </aside>
      </main>

      <footer className="site-footer">
        <span>Built for a good game.</span>
        <span>React client · FastAPI backend</span>
      </footer>
    </div>
  )
}

export default App