# Gebeta Game Rules: Complete End-to-End Specification

## Purpose

This document defines the authoritative gameplay rules for the Gebeta MCP Server prototype. It specifies the board setup, pit indexing, seed distribution, sowing continuation, capture mechanics, turn management, game termination, scoring, state validation, and MCP integration requirements.

The Python game engine must enforce these rules deterministically and independently of any AI client. AI agents may observe the game state and choose moves, but they must not independently execute or redefine game rules.

## 1. Game Board and Initial Setup

1. The game is played by two players: Player 1 and Player 2.
2. The board consists of 12 pits arranged in two rows of six pits each.
3. Each pit has a unique index from `0` to `11`.
4. Each pit initially contains four seeds.
5. The total number of seeds at the beginning of the game is 48.
6. Player 1 controls pits `6–11`.
7. Player 2 controls pits `0–5`.
8. The game engine must maintain the seed count of every pit and the number of seeds collected by each player.
9. A new game starts with all pits containing four seeds, both players having collected zero seeds, and a designated starting player.
10. Unless another starting-player selection mechanism is explicitly configured, Player 1 starts the game.

The initial board state is represented in Python as:

```python
board = [4] * 12
```

The board list index corresponds directly to the pit index.

## 2. Pit Ownership and Move Selection

1. On their turn, a player may select any non-empty pit belonging to their own side.
2. Player 1 may select only pits `6–11`.
3. Player 2 may select only pits `0–5`.
4. The player picks up all seeds from the selected pit.
5. The selected pit becomes empty before sowing begins.
6. The player distributes the seeds according to the sowing rules defined in this document.
7. A player cannot select an empty pit.
8. A player cannot select a pit belonging to the opponent.
9. A player cannot make a move after the game has ended.
10. Every invalid move must be rejected without modifying the board, collected-seed totals, current player, game status, or move history.
11. A player cannot select a pit whose move would enter a sowing cycle or exceed the seed-drop limit (Section 5.1). Such a move is illegal.

## 3. Fixed Pit Indexing and Sowing Order

The board uses a fixed circular traversal sequence:

`0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 0`

After pit `11`, sowing continues at pit `0`. This sequence repeats whenever the number of seeds being distributed requires additional circuits.

The next pit is calculated as follows:

```python
def next_pit(index: int) -> int:
    return (index + 1) % 12
```

The engine must use this sequence consistently for every sowing operation, including continuation sowing and moves involving more than 12 seeds.

The agreed circular index sequence is the implementation's source of truth for traversal. Its visual orientation should be represented consistently in any board display.

## 4. Sowing Seeds

When a player selects a valid pit:

1. The engine records the selected pit and its initial seed count.
2. The engine removes all seeds from that pit.
3. The selected pit becomes empty.
4. The player distributes the seeds one at a time, beginning with the next pit in the fixed circular sequence.
5. Each seed is placed into the next pit, incrementing its seed count by one.
6. The engine advances to the following pit after placing each seed.
7. If the sequence reaches pit `11`, the next pit is pit `0`.
8. Sowing continues until all seeds currently in hand have been distributed.
9. The engine records the pit in which the final seed was placed.
10. The engine evaluates the final landing pit according to the continuation and capture rules.

The selected pit is not skipped if sowing completes a full circuit. If the sequence returns to the selected pit, a seed is placed there according to the same traversal order.

The engine must not discard, duplicate, or create seeds during sowing.

## 5. Continuing Sowing from an Occupied Pit

After distributing all seeds currently in hand, the engine checks the final landing pit.

1. If the landing pit contains **more than one seed** after the final seed has been placed, the landing pit was occupied before that seed arrived. The player picks up all seeds from that pit.
2. The pit becomes empty.
3. The player continues sowing the collected seeds, beginning with the next pit in the circular sequence.
4. The player distributes these seeds one at a time.
5. After distributing all seeds from the newly collected hand, the engine checks the new final landing pit.
6. If the new landing pit contains more than one seed, the player repeats the continuation process.
7. If the landing pit contains **exactly one seed** after the final seed has been placed, the final seed landed in an empty pit. Sowing stops immediately.
8. The engine must not check for capture while continuation sowing is still required.

Throughout this document, "the final seed lands in an empty pit" means the landing pit was empty before the final seed was placed and contains exactly one seed afterwards. That final seed remains in the landing pit.

A landing pit that was occupied triggers continuation sowing, not capture.

### 5.1 Cycle Protection

Continuation sowing is deterministic, so a move either stops in an empty pit or repeats a previous state indefinitely. The engine must detect repetition and must not loop.

1. Before each continuation pickup, the engine records the sowing state as the pair (board snapshot, landing pit index). The collected-seed totals cannot change during sowing, so this pair determines the rest of the move.
2. If a sowing state repeats within the same move, the move is a **looping move**. Looping moves are illegal: the engine excludes them from the legal-moves list and rejects them with a `sowing_cycle` error.
3. Loop detection is the primary safeguard. As a secondary safeguard, the engine enforces a configurable limit on the number of seeds placed during a single move, with a default of **10,000** seed drops. A move that would exceed the limit is illegal: the engine excludes it from the legal-moves list and rejects it with a `sowing_limit_exceeded` error. Some looping moves repeat only after many thousands of seed drops, so the limit also covers loops too long to detect.
4. The engine must compute every move against a working copy of the state and commit it only after the move completes successfully. When a move is rejected as looping or exceeds the limit, the board, collected-seed totals, current player, game status, result, and move history must remain exactly as they were before the move.
5. A rejected looping move or a limit error must not be treated as a capture, a turn change, a game ending, or any other game outcome.

## 6. Opposite-Pit Mapping

Each pit has one directly opposite pit located six positions away in the circular index arrangement.

The opposite pit is calculated as follows:

```python
def opposite_pit(index: int) -> int:
    return (index + 6) % 12
```

The opposite-pit pairs are:

| Pit | Opposite pit |
|---:|---:|
| 0 | 6 |
| 1 | 7 |
| 2 | 8 |
| 3 | 9 |
| 4 | 10 |
| 5 | 11 |
| 6 | 0 |
| 7 | 1 |
| 8 | 2 |
| 9 | 3 |
| 10 | 4 |
| 11 | 5 |

The mapping must be symmetrical. If pit A is opposite pit B, pit B must be opposite pit A.

The engine must use this mapping for every capture check, regardless of which player's side contains the final landing pit.

## 7. Successful Capture

Capture is evaluated only after the sowing and continuation process ends with the final seed landing in an empty pit.

If the opposite pit contains one or more seeds:

1. The engine identifies the pit opposite the final landing pit.
2. The engine removes all seeds from that opposite pit.
3. The captured seeds are added to the current player's collected-seed total.
4. The opposite pit becomes empty.
5. The final seed remains in the landing pit. It is not captured.
6. The engine records the capture in the move result and move history.
7. The next player is determined by the turn rules in Section 11.1. A successful capture lets the same player move again whenever that player still has a legal move.

The capture rule applies whether the empty landing pit is on the current player's side or the opponent's side.

A successful capture does not automatically transfer the turn to the opponent.

## 8. Unsuccessful Capture

If the final seed lands in an empty pit and the directly opposite pit is also empty:

1. No seeds are captured.
2. No collected-seed total changes as a result of capture.
3. The final seed remains in the landing pit.
4. The engine records that the capture check was unsuccessful.
5. The next player is determined by the turn rules in Section 11.1. Normally the turn passes to the opponent, but the current player continues if the opponent has no legal move.

The engine must not capture seeds from a different pit when the directly opposite pit is empty.

## 9. Complete Move Execution Flow

Every valid move must follow this sequence:

1. Confirm that the game is active.
2. Identify the current player.
3. Verify that the selected pit belongs to the current player and contains seeds.
4. Record the pre-move state required for validation and history, and perform all following steps on a working copy of the state.
5. Pick up all seeds from the selected pit, leaving it empty.
6. Sow the seeds one at a time using the fixed circular sequence.
7. Identify the final landing pit.
8. If the final landing pit contains more than one seed, record the sowing state for cycle detection, pick up all seeds from it, and continue sowing from the next pit.
9. Repeat continuation sowing until the final seed lands in an empty pit. If a sowing state repeats or the safety limit is exceeded, discard the working copy and return the corresponding engine error (Section 5.1).
10. Identify the pit directly opposite the final landing pit.
11. If the opposite pit contains seeds, capture all of them and add them to the current player's collected-seed total.
12. If the opposite pit is empty, do not capture any seeds.
13. Determine which players have legal moves on the resulting board.
14. If neither player has a legal move, or the no-capture limit is reached (Section 11.2), end the game: award each row's remaining seeds to its owner, finalize the game status, and determine the result (Sections 11.2 and 12).
15. Otherwise, determine the next player using the turn rules in Section 11.1.
16. Validate the resulting game state, including the seed-count invariant.
17. Commit the working copy, record the completed move, and return a structured move result.

The engine must not alternate turns blindly after every move. Turn management must follow the outcome of the capture check, each player's legal moves, and the game-ending rules.

## 10. Legal Moves and Invalid Move Handling

A legal move is a selection of a non-empty pit belonging to the current player, while the game is active, that neither loops nor exceeds the seed-drop limit (Section 5.1). The engine determines whether a move loops or exceeds the limit by simulating it on a working copy of the state.

The engine must reject a move if:

- The selected pit index is outside the range `0–11`.
- The selected pit is empty.
- The selected pit belongs to the opponent.
- The move is a looping move (`sowing_cycle`).
- The game has already ended.
- The move request refers to an unknown game.
- The request is malformed or inconsistent with the current game state.

The engine must also reject a move that exceeds the seed-drop limit (`sowing_limit_exceeded`, Section 5.1).

The engine must return a clear, structured error explaining why the move was rejected.

An invalid move, or a move that exceeds the safety limit, must not change any game state, including:

- Pit seed counts.
- Collected-seed totals.
- Current player.
- Game status or result.
- Move history.

The engine should provide a legal-moves operation that lists the current player's legal moves when the game is active.

## 11. Turn Order, Empty Rows, and Game Termination

A player has a legal move when at least one pit on their own side contains seeds and selecting it neither loops nor exceeds the seed-drop limit (Section 5.1).

### 11.1 Determining the Next Player

After each valid move, the engine determines which players have legal moves on the resulting board and selects the next player as follows:

1. If neither player has a legal move, the game ends (Section 11.2). There is no next player.
2. If a capture occurred and the current player has a legal move, the current player moves again.
3. Otherwise, if the opponent has a legal move, the turn passes to the opponent.
4. Otherwise, only the current player has a legal move, so the current player continues.

In short, a successful capture keeps the turn when the capturing player can still move, an unsuccessful capture passes the turn when the opponent can move, and whenever only one player has legal moves, that player continues.

If one player's entire row becomes empty while seeds remain in the opponent's row:

1. The player whose row still contains seeds continues playing.
2. That player may select only non-empty pits belonging to their own side.
3. The player continues under the normal sowing, continuation, and capture rules.
4. When seeds reach the empty row again, the turn order above applies normally.

A player whose row is empty cannot select pits from the opponent's side.

### 11.2 Game End

1. The game ends when neither player has a legal move. This includes the case where seeds remain on the board but every move available to either player is illegal.
2. The game also ends when 20 consecutive valid moves, counted across both players, have been made without a capture. The limit is configurable, with a default of 20. A capture resets the count.
3. When the game ends, the engine awards the seeds remaining in each player's row to that player: seeds in pits `6–11` are added to Player 1's collected-seed total, and seeds in pits `0–5` are added to Player 2's collected-seed total. Those pits are then emptied.
4. The engine then calculates the final scores and result (Section 12) and marks the game as `completed`.

The engine must check the game-ending condition before starting another move and after processing each valid move.

The engine must not invent a new rule, transfer seeds other than as defined in this section, or enter an infinite loop.

## 12. Scoring and Determining the Winner

1. Each player's score is the number of seeds they have collected through captures, plus the seeds remaining in their row that are awarded to them when the game ends (Section 11.2).
2. While the game is active, seeds remaining in pits do not count as collected seeds.
3. Captured seeds are removed from the board and credited to the capturing player.
4. The game ends as defined in Section 11.2.
5. At game completion, after remaining seeds are awarded, all pits are empty and Player 1's collected seeds plus Player 2's collected seeds must equal 48.
6. The player with the greater collected-seed total wins.
7. If both players have the same collected-seed total, the game is a draw.

The engine must expose the final scores and result through the game status.

The engine must not declare a winner while the game is active.

## 13. Game State and Seed-Count Invariant

The engine must maintain a complete, authoritative game state containing at least:

- Game ID.
- Board state, with 12 pit seed counts.
- Current player.
- Collected-seed total for each player.
- Game status: `active` or `completed`.
- Winner or draw result when applicable.
- Move history.
- Any additional metadata required to validate and reproduce the game.

After every valid move, the following invariant must hold:

**Sum of all pit seeds + Player 1's collected seeds + Player 2's collected seeds = 48.**

In Python:

```python
assert (
    sum(board)
    + collected[1]
    + collected[2]
    == 48
)
```

The invariant must also hold at initialization, after the end-of-game award of remaining seeds, and after any completed game. A move rejected with a cycle or limit error leaves the previous state, which already satisfies the invariant, unchanged.

The engine must validate state changes so seeds cannot be duplicated, lost, or created during sowing, continuation, capture, or the end-of-game award.

## 14. Move Results and History

The engine must maintain a history of valid moves sufficient to understand and reproduce the progression of a game.

Each move-history entry should include:

- Move number.
- Player who made the move.
- Selected pit.
- Number of seeds initially picked up.
- Sowing sequence or sufficient details to reconstruct it.
- Each continuation pickup, where applicable.
- Final landing pit.
- Opposite pit checked for capture.
- Number of seeds captured.
- Remaining seeds awarded to each player, if the move ended the game.
- Resulting collected-seed totals.
- Current player after the move.
- Game status after the move.

The move result returned by the engine should indicate:

- Whether the move succeeded.
- Which pit was selected.
- How sowing and continuation proceeded.
- The final landing pit.
- Whether a capture occurred.
- The number of seeds captured.
- Whether the same player retains the turn or the turn changes, and why.
- The resulting board and collected-seed totals.
- Whether the game ended and, if so, the remaining seeds awarded to each player and the result.

Invalid moves and moves rejected with a cycle or limit error must not be added to the valid move history or change the game state.

## 15. Deterministic Python Engine Requirements

The game engine must implement the rules in deterministic Python code and remain independent of the MCP interface and AI model.

The engine is responsible for:

- Initializing the board.
- Validating player moves.
- Tracking pit indices and ownership.
- Distributing seeds.
- Detecting occupied landing pits.
- Executing continuation sowing.
- Detecting sowing cycles and enforcing the sowing safety limit.
- Identifying opposite pits.
- Applying captures.
- Managing turns.
- Checking game-ending conditions and awarding remaining seeds.
- Maintaining collected-seed totals.
- Validating the seed-count invariant.
- Recording move history.
- Determining the final result.

The engine must not delegate rule execution to an AI model.

For the same valid game state and move, the engine must produce the same result.

The fixed traversal functions are:

```python
def next_pit(index: int) -> int:
    return (index + 1) % 12


def opposite_pit(index: int) -> int:
    return (index + 6) % 12
```

The implementation must validate pit indices before calling these functions.

## 16. MCP Server Requirements

The MCP server exposes the engine's capabilities to compatible AI clients. It must not independently implement a competing version of the game rules.

The server should provide tools for:

- Creating a new game.
- Retrieving the board and current game state.
- Listing legal moves.
- Executing a move.
- Retrieving game status and scores.
- Retrieving move history.

The server should expose the gameplay rules through an MCP resource, such as `gebeta://rules`.

Tool requests must be validated, and responses must provide structured results or meaningful errors for invalid moves, malformed requests, unknown game IDs, completed games, and sowing cycle or safety-limit errors.

The engine remains the single source of truth for game state and rule enforcement.

## 17. AI Agent Interaction

Two AI agents may play against each other using the same MCP server and the same game engine.

1. The controller identifies the player whose turn it is.
2. The corresponding agent retrieves the current game state and legal moves.
3. The agent selects a pit.
4. The agent submits its move through the MCP server.
5. The server delegates move execution to the deterministic engine.
6. The engine validates the move, applies the rules, and returns the result.
7. The controller checks the resulting turn and game status.
8. The agent of whichever player the engine reports as the current player acts next. The controller must not decide turn order itself.
9. Agents should choose from the engine's legal-moves list, which already excludes looping and over-limit moves. If a move is rejected, the game state is unchanged and the same agent must select a different move or the controller must report the error.
10. The process continues until the game is completed.

AI agents must not modify the board directly, bypass move validation, or determine captures and scores independently.

## 18. Testing and Acceptance Criteria

The engine is ready for MCP integration when automated tests verify all of the following:

1. A new game initializes 12 pits with four seeds each.
2. The initial total is 48 seeds.
3. Player ownership is correct for pits `0–11`.
4. Valid pit indices are restricted to `0–11`.
5. The next-pit function follows the fixed circular sequence.
6. Pit `11` wraps to pit `0`.
7. Opposite-pit pairs are correct and symmetrical.
8. A player can select any non-empty pit on their own side.
9. Empty pits and opponent-owned pits are rejected.
10. Sowing distributes every seed exactly once.
11. Sowing works when a hand contains more than 12 seeds.
12. Continuation occurs when the final landing pit contains more than one seed after the final seed is placed.
13. Continuation begins from the next pit after picking up the occupied landing pit.
14. Sowing stops when the final landing pit contains exactly one seed after the final seed is placed.
15. Capture checks occur only after sowing ends in an empty pit.
16. Captures work when the empty landing pit is on either side of the board.
17. All seeds in the opposite pit are captured when it contains seeds.
18. No capture occurs when the opposite pit is empty.
19. The final seed remains in the landing pit after a successful or unsuccessful capture.
20. A successful capture retains the current player's turn when that player still has a legal move.
21. A successful capture passes the turn to the opponent when the capturing player has no legal move but the opponent does.
22. An unsuccessful capture passes the turn to the opponent when the opponent has a legal move.
23. An unsuccessful capture keeps the turn with the current player when only the current player has a legal move.
24. A player whose row is empty cannot select pits on the opponent's side.
25. The game ends when neither player has a legal move.
26. At game end, the seeds remaining in each row are awarded to that row's owner, all pits are empty, and the collected totals sum to 48.
27. A repeated sowing state is detected, and the move is rejected with a `sowing_cycle` error.
28. Looping moves are excluded from the legal-moves list.
29. When every remaining move for both players is a looping move, the game ends and remaining seeds are awarded.
30. Exceeding the seed-drop safety limit (default 10,000, configurable) is reported as a `sowing_limit_exceeded` error, and such moves are excluded from the legal-moves list.
31. Rejected looping moves and limit errors leave all game state and history unchanged and do not produce a game outcome.
32. The winner is determined from collected-seed totals.
33. Ties are reported as draws.
34. The seed-count invariant holds after every valid move and after the end-of-game award.
35. Invalid moves leave all game state and history unchanged.
36. Move results and history accurately reflect the executed moves.
37. MCP tools expose the engine correctly and return meaningful errors.
38. Two agents can complete a match through the MCP interface without bypassing the engine.
39. The game ends after 20 consecutive moves without a capture (configurable), and remaining seeds are awarded.

## 19. Scope and Rule Consistency

This specification defines the agreed rules for the Gebeta MCP Server prototype. It does not claim that every traditional Gebeta variant uses the same rules.

The following decisions are fixed for this implementation:

- Two players and 12 pits.
- Four initial seeds per pit, for 48 total seeds.
- Pit indices `0–11`.
- Player 1 owns pits `6–11`.
- Player 2 owns pits `0–5`.
- Circular sowing order `0 → 1 → 2 → … → 11 → 0`.
- Opposite pits are six positions apart.
- Sowing continues when the final landing pit contains more than one seed after the final seed is placed.
- Sowing stops when the final seed lands in an empty pit, and that seed remains there.
- Capture is checked only when the final landing pit was empty.
- A successful capture allows the same player to continue when that player has a legal move.
- An unsuccessful capture passes the turn to the opponent when the opponent has a legal move.
- When only one player has legal moves, that player continues.
- The game ends when neither player has a legal move or after 20 consecutive moves without a capture (configurable), and each row's remaining seeds are awarded to its owner.
- Moves that enter a sowing cycle are illegal, are excluded from legal moves, and are rejected without changing the game state.
- Moves exceeding a configurable limit of 10,000 seed drops (default) are illegal and are rejected without changing the game state.
- The winner is determined by collected-seed totals.
- The Python engine is the authoritative source of truth.

The implementation must not introduce additional gameplay rules without explicit approval. Any state that cannot be resolved under these rules must be reported clearly rather than handled through an invented rule.

The objective is to deliver a deterministic, testable Gebeta game engine, expose it through MCP, and enable AI clients to play the game through a reliable, standardized interface.

## 20. Resolved Issues

1. **Game termination.** Every valid move leaves its final seed on the board, so without an extra rule the game almost never ends: a simulation of 2,000 random games produced no completed game. The no-capture limit in Section 11.2 resolves this. In 300 simulated random games it ended every game, with a median length of 58 moves.
2. **Long loops reported as limit errors.** Detecting a cycle can take far more than 10,000 seed drops (up to millions in simulation), so many looping moves hit the limit first. Treating over-limit moves as illegal (Section 5.1) keeps them out of the legal-moves list and lets the game-end check in Section 11.2 account for them.
