from backend.app.services.game_manager import GameManager
from backend.app.game_state import EMPTY, RED, ROWS, COLUMNS
import uuid



def test_create_and_get_game():
    # Test creating a new game and retrieving it by ID
    game_manager = GameManager()
    game_id, game = game_manager.create_game()
    retrieved_game = game_manager.get_game(game_id)
    assert retrieved_game is not None
    assert retrieved_game == game

# Test that a newly retrieved game has an empty board and active status
def test_new_game_has_empty_board_and_active_status():
    game_manager = GameManager()
    _, game = game_manager.create_game()
    assert game.board == [[EMPTY for _ in range(COLUMNS)] for _ in range(ROWS)]
    assert game.status == "active"

# Test that an unknown ID returns none
def test_unknown_game_id_returns_none():
    game_manager = GameManager()
    assert game_manager.get_game("non_existent_id") is None
    
    # Test that the game_id is a valid UUID string and has the correct format
def test_game_id_is_valid_uuid():
    game_manager = GameManager()
    game_id, _ = game_manager.create_game()
    assert isinstance(game_id, str)
    assert uuid.UUID(game_id).version == 4  # The UUID should be version 4
    assert uuid.UUID(game_id).hex == game_id.replace("-", "")  # The hexadecimal representation should match the UUID without hyphens
    

# Test that two created games have different IDs and independent states
def test_two_created_games_have_different_ids_and_independent_states():
    game_manager = GameManager()
    game_id, game = game_manager.create_game()
    game_id_2, game_2 = game_manager.create_game()
    assert game_id != game_id_2
    assert game != game_2
    assert game_2.board == [[EMPTY for _ in range(COLUMNS)] for _ in range(ROWS)]
    assert game_2.status == "active"


# Test that modifying one game's board does not affect the other game
def test_modifying_one_game_does_not_affect_the_other():
    game_manager = GameManager()
    _, game = game_manager.create_game()
    _, game_2 = game_manager.create_game()
    game.board[0][0] = RED
    assert game.board[0][0] == RED
    assert game_2.board[0][0] == EMPTY
