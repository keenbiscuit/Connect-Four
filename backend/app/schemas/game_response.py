from pydantic import BaseModel


class GameResponse(BaseModel):
    game_id: str
    board: list[list[int]]
    status: str
    current_player: int  # game turn state
    winner: int | None
    mode: str | None # can be "human_vs_human" or "human_vs_bot"
    bot_player: int | None  # can be RED or YELLOW if playing against a bot
