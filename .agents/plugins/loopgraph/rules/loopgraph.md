# Loop & Graph Engineering Rules for Antigravity

> [!NOTE]
> These rules govern autonomous loop execution and multi-stage graph state transitions.

## 1. Loop Engineering Disciplines
- **Self-Correcting ReAct Loops:** Every implementation step must follow `Sense -> Think -> Act -> Verify`.
- **Surgical Code Modifications:** Never overwrite entire files. Always use targeted replacements (`replace_content`) to prevent hallucinated code regressions.
- **Self-Verification Before Done:** The implementer must execute test/build commands to prove acceptance criteria before calling `task_done` or marking a `BOARD.md` row `done`.

## 2. Graph Engineering & State Machine
- **State Decomposition:** Large goals must be decomposed into atomic tasks with explicit acceptance criteria.
- **Topological Sorting:** Tasks with prerequisites (`depends_on`) must never run until their dependencies are marked `done`.
- **Maker/Checker Separation:** Independent verification runs with zero conversation bias and read-only tools/behavior.
- **Externalized Persistence:** All state lives on disk (`VISION.md`, `BOARD.md`, `LEDGER.md`) — never only in conversation history, so a `/compact` or new session can resume exactly where the last one left off.

## 3. Native-Mode / CLI-Mode Interop
- `BOARD.md` and `LEDGER.md` are a shared on-disk contract between Antigravity-native execution and the `loopgraph` CLI. When editing them yourself, follow the exact table/entry format documented in `.agents/skills/loopgraph/SKILL.md` so a later `loopgraph status` or `loopgraph run` still parses your work correctly.
