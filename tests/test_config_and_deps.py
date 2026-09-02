"""
Regressions for three silent-wrongness bugs found during the 2026-09-02 standalone audit:

1. Values in config.json were overwritten on every run by argparse's own defaults, so
   half of the file `loopgraph init` writes had no effect at all.
2. A `--config` path that does not exist was swallowed, and the agent ran with a
   different model and token ceiling than the user asked for, reporting success.
3. A dependency cycle or a reference to a task id absent from the board removed those
   tasks from scheduling permanently, which is indistinguishable from "nothing to do".

Plus one security regression: model API keys were inherited by every command the agent
executed, making them readable by any `env`-style command and exfiltratable with output.
"""

import json
import os
import tempfile
from pathlib import Path

from loopgraph.core.state import ProjectState, Task
from loopgraph.engine import EngineConfig
from loopgraph.safety.guardrails import Guardrails
from loopgraph.tools.exec_tools import RunCommandTool


def assert_raises(exc_type, func, *args, **kwargs):
    """Minimal stand-in for pytest.raises.

    These tests must also run under `python -m tests.run_loopgraph_tests`, the command
    the README documents, which has to work on a bare clone with no test framework
    installed. Importing pytest at module scope would make that command crash.
    """
    try:
        func(*args, **kwargs)
    except exc_type:
        return
    except Exception as exc:  # noqa: BLE001 - report what actually happened
        raise AssertionError(f"expected {exc_type.__name__}, got {type(exc).__name__}: {exc}")
    raise AssertionError(f"expected {exc_type.__name__}, but no exception was raised")


# --- config.json is actually honoured -------------------------------------------------

def test_config_file_values_are_loaded():
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_path = Path(tmpdir) / "config.json"
        cfg_path.write_text(
            json.dumps(
                {
                    "model": "custom-model",
                    "budget_tokens": 999,
                    "max_loop_iters": 7,
                    "stop_on_fail": True,
                }
            ),
            encoding="utf-8",
        )
        cfg = EngineConfig.from_file_or_defaults(cfg_path)

        assert cfg.model == "custom-model"
        assert cfg.budget_tokens == 999, "config.json budget_tokens was ignored"
        assert cfg.max_loop_iters == 7
        assert cfg.stop_on_fail is True


def test_missing_config_path_raises_instead_of_silently_defaulting():
    with tempfile.TemporaryDirectory() as tmpdir:
        missing = Path(tmpdir) / "does-not-exist.json"
        assert_raises(FileNotFoundError, EngineConfig.from_file_or_defaults, missing)


def test_no_config_path_still_returns_defaults():
    cfg = EngineConfig.from_file_or_defaults(None)
    assert cfg.budget_tokens == 2_000_000


def test_config_must_be_a_json_object():
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_path = Path(tmpdir) / "config.json"
        cfg_path.write_text("[1, 2, 3]", encoding="utf-8")
        assert_raises(ValueError, EngineConfig.from_file_or_defaults, cfg_path)


# --- dependency problems are detected rather than silently deadlocking ----------------

def _state_with(pairs):
    state = ProjectState(project_path=Path("."))
    state.tasks = [Task(id=tid, title=tid, depends_on=deps) for tid, deps in pairs]
    return state


def test_dependency_cycle_is_detected():
    state = _state_with([("T1", ["T2"]), ("T2", ["T1"])])
    assert state.get_pending_tasks() == [], "precondition: a cycle blocks all scheduling"

    cycles, dangling = state.find_dependency_problems()
    assert dangling == {}
    assert cycles, "cycle T1 -> T2 -> T1 not detected"
    assert set(cycles[0]) == {"T1", "T2"}


def test_self_dependency_is_detected():
    cycles, _ = _state_with([("T1", ["T1"])]).find_dependency_problems()
    assert cycles == [["T1", "T1"]]


def test_longer_cycle_is_detected():
    cycles, _ = _state_with(
        [("T1", ["T2"]), ("T2", ["T3"]), ("T3", ["T1"])]
    ).find_dependency_problems()
    assert cycles and set(cycles[0]) == {"T1", "T2", "T3"}


def test_dangling_dependency_is_detected():
    cycles, dangling = _state_with([("T1", ["T99"]), ("T2", [])]).find_dependency_problems()
    assert cycles == []
    assert dangling == {"T1": ["T99"]}
    # The healthy task must still be schedulable.
    assert [t.id for t in _state_with([("T1", ["T99"]), ("T2", [])]).get_pending_tasks()] == ["T2"]


def test_healthy_dependency_chain_reports_no_problem():
    cycles, dangling = _state_with(
        [("T1", []), ("T2", ["T1"]), ("T3", ["T1", "T2"])]
    ).find_dependency_problems()
    assert cycles == [] and dangling == {}, "false positive on a valid dependency chain"


# --- model credentials are withheld from executed commands ---------------------------

def test_api_keys_are_not_inherited_by_executed_commands():
    canaries = {
        "ZAI_API_KEY": "CANARY-ZAI",
        "OPENAI_API_KEY": "CANARY-OPENAI",
        "MY_VENDOR_API_KEY": "CANARY-VENDOR",
        "LOOPGRAPH_NORMAL_VAR": "keep-me",
    }
    saved = {name: os.environ.get(name) for name in canaries}
    os.environ.update(canaries)
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = RunCommandTool(Guardrails(project_path=Path(tmpdir)))
            result = tool.execute(
                'python -c "import os,json;print(json.dumps(dict(os.environ)))"'
            )

            for canary in ("CANARY-ZAI", "CANARY-OPENAI", "CANARY-VENDOR"):
                assert canary not in result.output, f"credential leaked to subprocess: {canary}"
            assert "keep-me" in result.output, "scrubbing removed an unrelated variable"
    finally:
        for name, previous in saved.items():
            if previous is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = previous


def test_child_env_keeps_path():
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = RunCommandTool(Guardrails(project_path=Path(tmpdir)))
        env = tool._child_env()
        assert "PATH" in env or "Path" in env, "PATH must survive scrubbing"
        assert os.environ.get("PATH") == env.get("PATH", env.get("Path"))
