# Loop & Graph Engineering Rules for Antigravity

> [!NOTE]
> These rules govern autonomous loop execution and multi-stage graph state transitions.

## 1. Loop Engineering Disciplines
- **Self-Correcting ReAct Loops:** Every implementation step must follow `Sense -> Think -> Act -> Verify`.
- **Surgical Code Modifications:** Never overwrite entire files. Always use targeted replacements (`replace_content`) to prevent hallucinated code regressions.
- **Self-Verification Before Done:** The implementer must execute test/build commands to prove acceptance criteria before calling `task_done`.

## 2. Graph Engineering & State Machine
- **State Decomposition:** Large goals must be decomposed into atomic tasks with explicit acceptance criteria.
- **Topological Sorting:** Tasks with prerequisites (`depends_on`) must never run until their dependencies are marked `DONE`.
- **Maker/Checker Separation:** Independent verification runs with zero conversation bias and read-only tools.
- **Externalized Persistence:** All state lives on disk (`VISION.md`, `BOARD.md`, `LEDGER.md`).
