---
name: loopgraph
description: >-
  Autonomous Loop & Graph Engineering Suite for Google Antigravity. Use this skill when
  the user asks to autonomously develop, plan tasks, execute iterative ReAct loops,
  or perform multi-stage verification.
---

# Antigravity LoopGraph Skill

LoopGraph brings **Loop Engineering** (self-correcting, convergence-guaranteed ReAct loops) and **Graph Engineering** (explicit StateGraph orchestration & topological task decomposition) to Google Antigravity.

## 🔄 Core Commands & Runbooks

### 1. Initialize Project Memory
Scaffold `VISION.md`, `BOARD.md`, and `LEDGER.md` in the workspace:
```bash
loopgraph init .
```

### 2. Autonomous Task Planning
Scan the codebase and generate actionable, atomic, verifiable tasks:
```bash
loopgraph plan .
```

### 3. Run Autonomous Loop & Graph Execution
Execute tasks through the full `ANALYZE -> PRIORITIZE -> IMPLEMENT -> VERIFY -> RECORD` state machine:
```bash
# Autonomously complete 3 tasks with adversarial verification
loopgraph run . --tasks 3

# Run with custom budget and stop-on-fail
loopgraph run . --tasks 5 --budget-tokens 1000000 --stop-on-fail
```

### 4. Check Board & Development Status
```bash
loopgraph status .
```

## Antigravity `/goal` and Slash Command Integration

When the user types `/goal` or asks to autonomously complete a milestone in Antigravity:
1. **Load Active Board:** LoopGraph automatically parses `BOARD.md`.
2. **Topological Task Execution Loop:**
   - Picks the highest priority unblocked `TODO` task.
   - Sets status to `IN_PROGRESS` in `BOARD.md`.
   - Executes ReAct loop: Reads target files, applies surgical edits, runs tests.
   - Runs verification: Executes build/test commands.
   - If tests pass: Updates `BOARD.md` to `[x] DONE` and appends proof to `LEDGER.md`.
   - If tests fail: Re-injects error feedback into next iteration (up to 3 retries).
3. **Loop Until Goal Convergence:** The agent does NOT stop until all actionable tasks on `BOARD.md` are marked `DONE` or blocked.

## Core Rules
1. **Maker/Checker Separation ("Yapan Notlandıramaz"):** Verification runs in an isolated context with read-only tools.
2. **Externalized Memory:** All status is stored on disk in `BOARD.md` and `LEDGER.md`.
3. **Anti-Thrashing:** Halts loops if 3 identical observations are produced consecutively.
