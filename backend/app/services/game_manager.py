# contains the GameManager class responsible for creating and managing multiple game instances

import uuid
from backend.app.game_state import RED, YELLOW, GameState


class GameManager:
    def __init__(self) -> None:
        self.games: dict[str, GameState] = {}
        self.next_starting_player = RED

    # creates a unique game ID and returns ID & safe game state
    def create_game(self) -> tuple[str, GameState]:
        # Generate a unique game ID
        unique_game_id = uuid.uuid4()
        game_id = str(unique_game_id)

        # Determine the starting player for the new game
        starting_player = self.next_starting_player
        game = GameState(starting_player=starting_player)
        
        # Store the newly created game in the games dictionary
        self.games[game_id] = game

        # Update the next starting player for the subsequent game
        self.next_starting_player = (YELLOW if self.next_starting_player == RED else RED)

        # Return the game ID and the newly created game state
        return game_id, game

    # retrieves the game state for a given game ID, or None if not found
    def get_game(self, game_id: str) -> GameState | None:
        return self.games.get(game_id)