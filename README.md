# Real-Time Connect Four

A portfolio project for learning Python, FastAPI, WebSockets, React, MongoDB, Redis, Docker, testing, and real-time backend design.

## Current milestone

Milestone 0: Python project setup and initial game-domain testing.

## Current progress

### Milestone 1 complete: Pure Python game engine

- Server-independent Connect Four rules engine
- Validates moves and full columns
- Alternates turns
- Detects horizontal, vertical, and diagonal wins
- Detects draws and rejects moves after completion
- Tested with pytest

## Known test gap

- Add a legal full-board draw fixture for `GameState`.
- Verify draw state, no winner, no turn switch on final move, and post-draw move rejection.