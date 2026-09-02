"""
Tests for StateGraph, GraphRunner, and ReAct LoopEngine with Mock LLM.
"""

import json
import tempfile
from pathlib import Path
from loopgraph.core.graph import BaseNode, END, START, StateGraph
from loopgraph.core.loop import LoopEngine
from loopgraph.core.state import ProjectState, Task, TaskStatus
from loopgraph.engine import EngineConfig, GraphEngine
from loopgraph.llm.client import LLMClient, LLMResponse
from loopgraph.tools import create_implement_registry


def test_basic_stategraph_transitions():
    class Step1(BaseNode):
        def run(self, state: ProjectState):
            state.metadata["step1"] = True
            return "NEXT"

    class Step2(BaseNode):
        def run(self, state: ProjectState):
            state.metadata["step2"] = True
            return "FINISH"

    with tempfile.TemporaryDirectory() as tmpdir:
        state = ProjectState(project_path=Path(tmpdir))

        g = StateGraph()
        g.add_node(Step1(name="step1"))
        g.add_node(Step2(name="step2"))
        g.set_entry_point("step1")
        g.add_edge("step1", "step2")
        g.add_edge("step2", END)

        runner = g.compile()
        runner.run(state)

        assert state.metadata.get("step1") is True
        assert state.metadata.get("step2") is True


def test_react_loop_anti_thrashing():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        guard = GuardrailsMock(root)
        tools = create_implement_registry(guard)

        # Mock LLM that repeats the exact same tool call indefinitely
        def repetitive_llm_handler(messages, tool_schemas):
            return LLMResponse(
                content="",
                tool_calls=[{
                    "id": "tc_1",
                    "type": "function",
                    "function": {
                        "name": "read_file",
                        "arguments": json.dumps({"path": "nonexistent.txt"}),
                    },
                }],
                tokens_used=10,
            )

        llm = LLMClient(mock_handler=repetitive_llm_handler)
        loop = LoopEngine(llm=llm, tool_registry=tools, max_iters=10)

        task = Task(id="T1", title="Loop test", acceptance=["test"])
        result = loop.run(task, project_context="")

        # Anti-thrashing should stop the infinite loop before reaching max_iters
        assert result.is_done is False
        assert "Anti-thrashing" in (result.error or "")
        assert result.iterations <= 4


class GuardrailsMock:
    def __init__(self, path):
        self.project_path = path

    def is_path_safe(self, p):
        return True, (self.project_path / p), None

    def is_command_safe(self, c):
        return True, None

    def is_dir_excluded(self, d):
        return False
