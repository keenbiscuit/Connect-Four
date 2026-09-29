from dataclasses import dataclass

@dataclass
class MoveResult:
    success : bool
    column : int
    player : int
    row : int | None
    reason : str | None
    status : str | None
    winner : str | None

    
