from pydantic import BaseModel


class MoveRequest(BaseModel):
    column: int
