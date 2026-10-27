# gebeta-mcp

An MCP server for the traditional Gebeta board game, featuring a deterministic Python game engine, rule-enforced gameplay, and AI agent integration. Enables MCP-compatible AI clients to inspect the board, retrieve legal moves, execute moves, and play against each other through a standardized interface.

## Documentation

- [Game rules](docs/spec/gebeta-rules.md): the authoritative specification the engine enforces.

## Status

The domain engine and application layer are complete and tested against the acceptance criteria in spec §18. The API, MCP server, agents, and UI come next.

| Module | Purpose | Criteria (spec §18) | Status |
|---|---|---|---|
| `domain/board.py` | Constants, pit validation, `next_pit`, `opposite_pit`, `pit_owner` | 1–7 | Done |
| `domain/errors.py` | `MoveError` and error codes | — | Done |
| `domain/models.py` | Frozen `GameState`, `MoveResult`, `MoveRecord`; seed-count invariant | 34 (partial) | Done |
| `domain/sowing.py` | Chained sowing, loop detection, 10,000-drop cap | 10–14, 27, 30 | Done |
| `domain/rules.py` | Legal moves, capture, next player, game end and award | 8, 15–26, 28–33 | Done |
| `domain/game.py` | `apply_move()` on a working copy; property tests | 9, 31, 34–36, 39 | Done |
| `application/` | `GameService` use cases, `GameRepository` port, per-game locks | — | Done |
| `infrastructure/` | `InMemoryGameRepository` | — | Done |

The game ends when neither player has a legal move or after 20 consecutive moves without a capture; moves that loop or exceed 10,000 seed drops are illegal (spec §5.1, §11.2, §20).

## Development

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync                          # install dependencies
uv run pytest                    # run tests
uv run ruff check src tests      # lint
uv run ruff format src tests     # format
uv run mypy                      # type-check (strict)
uv run lint-imports              # enforce layer dependency rules
```
