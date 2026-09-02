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

## 🛡️ Core Rules
1. **Maker/Checker Separation ("Yapan Notlandıramaz"):** Verification runs in an isolated context with read-only tools.
2. **Externalized Memory:** All status is stored on disk in `BOARD.md` and `LEDGER.md`.
3. **Anti-Thrashing:** Halts loops if 3 identical observations are produced consecutively.
