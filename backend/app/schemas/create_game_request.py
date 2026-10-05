from typing import Literal

from pydantic import BaseModel


class CreateGameRequest(BaseModel):
    mode: Literal["human_vs_human", "human_vs_bot"] = "human_vs_human"