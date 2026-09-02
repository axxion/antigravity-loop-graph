# Antigravity LoopGraph

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Antigravity](https://img.shields.io/badge/Google%20Antigravity-IDE%20%7C%20CLI%20%7C%202.0-blueviolet.svg)]()
[![Tests: Passing](https://img.shields.io/badge/tests-passing-brightgreen.svg)]()

> **Autonomous Loop & Graph Engineering Engine for Google Antigravity & AI Coding Agents.**  
> Transforms unstructured LLM prompting into predictable, self-correcting, verifiable state machine graphs.

---

## Overview

**Antigravity LoopGraph** unifies two foundational agent design disciplines:
1. **Loop Engineering:** Sustained, self-correcting ReAct execution loops (`Sense -> Think -> Act -> Verify`) with mathematical convergence guarantees, anti-thrashing circuit breakers, and adversarial maker/checker verification.
2. **Graph Engineering:** Explicit workflow orchestration modeled as a **StateGraph** (DAG / cyclic state machine) with topological dependency sorting, failure feedback routing, and persistent disk memory.

```
[START]
   |
   v
[1. ANALYZE NODE]  ------> Scan project vision (VISION.md) & codebase tree
   |
   v
[2. PRIORITIZE NODE] ----> Topologically sort dependencies & select highest-priority task
   |
   v
[3. IMPLEMENT NODE]  ----> ReAct Loop: Surgical file edits, search, execution & tests
   |
   v
[4. VERIFY NODE]     ----> Independent Adversarial Verifier: "Maker cannot grade itself"
   |
   +---> [PASS] ----------> [5. RECORD NODE] ----> Update BOARD.md & append to LEDGER.md (DONE)
   |                                                    |
   +---> [FAIL] ----------> [4b. REFLECT NODE]          v
                                 |               [Route to Next Task]
                                 +---> (Retries < 3) ----> Re-inject failure feedback to IMPLEMENT
                                 +---> (Retries >= 3) ---> Mark BLOCKED & advance
```

---

## Core Engineering Principles

### 1. Maker/Checker Separation ("Adversarial Verification")
The implementing agent is never permitted to evaluate its own work. Verification executes in a **clean, isolated LLM session** with zero prior conversation bias, evaluated against a strict acceptance rubric with **read-only tools** (`read_file`, `view_file`, `grep_search`, `run_command`). The verifier has zero file modification privileges.

### 2. Anti-Thrashing Circuit Breaker
If the agent repeats the identical tool action or receives duplicate observations 3 consecutive times, LoopGraph detects the behavioral trap and halts the loop cleanly to prevent runaway context consumption and infinite loops.

### 3. Externalized Memory Outside Context
Session state is preserved in immutable filesystem artifacts rather than fragile context windows:
*   **`VISION.md`** -- Project architecture constraints, high-level requirements, and quality standards.
*   **`BOARD.md`** -- Live development board tracking tasks, acceptance rubrics, priority, dependencies, and state (`TODO`, `IN_PROGRESS`, `DONE`, `BLOCKED`, `FAILED`).
*   **`LEDGER.md`** -- Immutable append-only audit trail logging timestamps, test outcomes, attempt counts, and token consumption.

### 4. Sandbox Path Containment & Security Gates
Destructive operations such as recursive deletion (`rm -rf /`, `rd /s`), system alteration (`format`, `shutdown`), Git mutations (`git push`, `git reset --hard`), and uninspected piping to shells are permanently blocked. All file operations are sandboxed strictly within the project root directory.

---

## Installation

```bash
# Clone the repository
git clone https://github.com/axxion/antigravity-loop-graph.git
cd antigravity-loop-graph

# Install in editable mode
pip install -e .
```

---

## Command Line Interface (CLI)

### 1. Initialize Workspace Memory
Scaffold `VISION.md`, `BOARD.md`, and `LEDGER.md` in any project:
```bash
loopgraph init /path/to/project
```

### 2. Autonomous Task Planning
Analyze project structure and populate `BOARD.md` with verifiable tasks without writing code:
```bash
loopgraph plan /path/to/project
```

### 3. Run Autonomous Graph Execution
Execute the full state machine across tasks with automated verification:
```bash
# Autonomously complete 3 tasks
loopgraph run /path/to/project --tasks 3

# Run with custom token budget and stop-on-fail
loopgraph run /path/to/project --tasks 5 --budget-tokens 1500000 --stop-on-fail

# Specify custom OpenAI-compatible models
loopgraph run /path/to/project --model glm-5.3-flash --verify-model gpt-4o
```

### 4. Inspect Live Board Status
```bash
loopgraph status /path/to/project
```

---

## Python Library API

Use LoopGraph programmatically in custom AI agent workflows, backend services, or CI/CD pipelines:

```python
from loopgraph import GraphEngine, EngineConfig

# Configure the engine
config = EngineConfig(
    model="glm-5.3-flash",          # Implementer LLM
    verify_model="gpt-4o",          # Independent verifier LLM
    budget_tokens=2_000_000,
    max_loop_iters=25,
    stop_on_fail=False
)

# Initialize engine
engine = GraphEngine(
    project_path="./my_project",
    config=config
)

# Run graph execution
report = engine.run(max_tasks=3)

print(f"Total Tasks: {report.total_tasks}")
print(f"Completed:   {report.completed_tasks}")
print(f"Blocked:     {report.blocked_tasks}")
print(f"Tokens Used: {report.tokens_used:,}")
```

### Custom StateGraph Construction:
```python
from loopgraph import StateGraph, BaseNode, ProjectState, END

class CustomAuditNode(BaseNode):
    def run(self, state: ProjectState):
        print("Executing custom audit...")
        return "AUDIT_OK"

graph = StateGraph()
graph.add_node(CustomAuditNode(name="audit"))
graph.set_entry_point("audit")
graph.add_edge("audit", END)

runner = graph.compile()
runner.run(ProjectState(project_path="."))
```

## Execution Modes: Antigravity Native vs. Standalone CLI

LoopGraph supports two seamless operational workflows:

### Mode 1: Antigravity IDE Native (Recommended - Zero API Key Required)
When working inside Google Antigravity IDE, LoopGraph operates natively using Antigravity's built-in intelligence. No external API keys or environment variables are required.
- Initialize memory: `loopgraph init .`
- Directly in Antigravity Chat: *"Use LoopGraph to plan tasks from VISION.md and execute them on BOARD.md"*
- Antigravity automatically activates `.agents/skills/loopgraph/SKILL.md` and coordinates the graph state machine.

### Mode 2: Standalone CLI / CI/CD (External API Key)
For headless servers, CI/CD runners, or standalone terminal execution without an IDE:
- Set your preferred API key: `export ZAI_API_KEY="your-key"` (Supports `OPENAI_API_KEY`, `DEEPSEEK_API_KEY`, `GROQ_API_KEY`)
- Run commands: `loopgraph plan .` and `loopgraph run . --tasks 3`

---

## Google Antigravity Integration

LoopGraph includes native Google Antigravity workspace customizations:

*   **`.agents/skills/loopgraph/SKILL.md`** -- Antigravity skill for interactive loop and graph engineering workflows.
*   **`.agents/rules/loopgraph.md`** -- Workspace rules enforcing surgical edits and self-verification.
*   **`.agents/plugins/loopgraph/`** -- Distributable Antigravity plugin package.

---

## Test Verification

Run the test suite to verify graph transitions, ReAct loops, safety containment, and memory managers:

```bash
python -m tests.run_loopgraph_tests
```

---

## License

This project is licensed under the [MIT License](LICENSE).  
Author: **axxion** ([GitHub: @axxion](https://github.com/axxion))
