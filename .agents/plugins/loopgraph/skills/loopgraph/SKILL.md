---
name: loopgraph
description: >-
  Autonomous Loop & Graph Engineering Suite for Google Antigravity. Use this skill when
  the user asks to autonomously develop, plan tasks, execute iterative ReAct loops,
  or perform multi-stage verification.
---

# Antigravity LoopGraph Skill

LoopGraph brings **Loop Engineering** (self-correcting, convergence-guaranteed ReAct loops) and **Graph Engineering** (explicit StateGraph orchestration & topological task decomposition) to Google Antigravity.

## Core Commands & Runbooks

### 1. Initialize Project Memory (always safe, no API key needed)
```bash
loopgraph init .
```
Scaffolds `VISION.md`, `BOARD.md`, `LEDGER.md`, `config.json`, and this `.agents/` integration.

### 2. Autonomous Task Planning (always safe, no API key needed)
```bash
loopgraph plan .
```
Scans the codebase and writes atomic, verifiable tasks to `BOARD.md`. Automatically falls back to a
local heuristic planner (no LLM call) when no API key is configured — this is the expected, supported
path in Antigravity Native Mode, not a degraded one.

### 3. Check Board & Development Status (always safe, no API key needed)
```bash
loopgraph status .
```

## Zero-API Native Mode — YOU are the execution engine

`loopgraph run` executes the IMPLEMENT -> VERIFY loop through an **external** LLM API and requires an
API key (`ZAI_API_KEY`/`OPENAI_API_KEY`/`DEEPSEEK_API_KEY`/`GROQ_API_KEY`). **Do not invoke `loopgraph run`
from Antigravity chat unless the user has explicitly configured one of these** — without a key it refuses
to run and prints a redirect message instead of crashing, but it will NOT perform the loop for you.

When no external key is configured (the default, recommended Antigravity setup), **you are the loop
engine**: read `BOARD.md` yourself, pick the next task, implement it with your own tools, verify it
yourself by actually running build/test commands, and update `BOARD.md`/`LEDGER.md` yourself. Use the
**exact formats below** so `loopgraph status` (and `loopgraph run`, if a key is added later) can still
parse your edits correctly — native-mode and CLI-mode share the same on-disk state.

### `BOARD.md` row format (must match exactly — pipe-delimited Markdown table)
```
| ID | Görev | Kabul Kriterleri | Öncelik | Bağımlılıklar | Durum |
|----|-------|------------------|---------|---------------|-------|
| T1 | Görev başlığı | · kriter 1<br>· kriter 2 | 1 | — | todo |
```
- `Durum` (status) must be exactly one of: `todo`, `in_progress`, `done`, `failed`, `blocked`.
- `Bağımlılıklar` (depends_on) is comma-separated task IDs, or `—` if none.
- `Kabul Kriterleri` (acceptance) entries are separated by `<br>`, each prefixed with `· `.
- Never start a task whose `depends_on` IDs are not all `done` — this is the topological-sort guarantee.

### `LEDGER.md` entry format (append-only, never edit past entries)
```
## [T1] Görev başlığı
- **Tarih & Saat:** 2026-09-02 12:00:00
- **Durum:** ✅ DONE
- **Öncelik:** 1 | **Efor:** M | **Deneme Sayısı:** 1
- **Kabul Kriterleri:**
  - [x] kriter 1
- **Uygulama Özeti:** ne değiştirildi (1-2 cümle)
- **Doğrulama Notu:** hangi komutla doğrulandı ve sonucu
```

## Antigravity `/goal` and Slash Command Integration

When the user types `/goal` or asks to autonomously complete a milestone in Antigravity:
1. **Load Active Board:** parse `BOARD.md` using the format above.
2. **Topological Task Execution Loop:**
   - Pick the highest priority unblocked `todo` task (all `depends_on` already `done`).
   - Set its status to `in_progress` in `BOARD.md`.
   - Execute a ReAct loop yourself: read target files, apply surgical edits, run tests.
   - Verify yourself: actually execute the build/test commands from the acceptance criteria —
     do not mark a task done on inspection alone ("Yapan notlandıramaz" — self-grading is not verification).
   - If verified: set status to `done` in `BOARD.md` and append a `LEDGER.md` entry with proof.
   - If it fails: leave status `in_progress`, note the failure, and retry (up to 3 attempts) before
     marking `blocked`.
3. **Loop Until Goal Convergence:** do NOT stop until every actionable task on `BOARD.md` is `done` or `blocked`.

## Core Rules
1. **Maker/Checker Separation ("Yapan Notlandıramaz"):** verification must be a real, independently-run check — not the same reasoning pass that wrote the code.
2. **Externalized Memory:** all status lives on disk in `BOARD.md` and `LEDGER.md`, not just in conversation context.
3. **Anti-Thrashing:** if you find yourself repeating the identical action with the identical result 3 times in a row, stop and mark the task `blocked` with a note — do not loop indefinitely.
