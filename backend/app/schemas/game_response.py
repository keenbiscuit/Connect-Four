from pydantic import BaseModel


class GameResponse(BaseModel):
    game_id: str
    board: list[list[int]]
    status: str
    current_player: int
    winner: int | None
