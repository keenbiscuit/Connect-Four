

import uuid
from backend.app.game_state import GameState


class GameManager:
    def __init__(self) -> None:
        self.games: dict[str, GameState] = {}

    # creates a unique game ID and returns ID & safe game state
    def create_game(self) -> tuple[str, GameState]:
        unique_game_id = uuid.uuid4()
        game_id = str(unique_game_id)
        game = GameState()
        self.games[game_id] = game
        return game_id, game

    # retrieves the game state for a given game ID, or None if not found
    def get_game(self, game_id: str) -> GameState | None:
        return self.games.get(game_id)