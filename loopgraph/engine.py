"""
LoopGraph High-Level Engine Facade.
Assembles the complete state machine graph and coordinates execution.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from loopgraph.core.graph import END, START, GraphRunner, StateGraph
from loopgraph.core.loop import LoopEngine
from loopgraph.core.state import ProjectState, Task, TaskStatus
from loopgraph.llm.client import LLMClient
from loopgraph.memory.board import BoardManager
from loopgraph.memory.ledger import LedgerManager
from loopgraph.memory.vision import VisionManager
from loopgraph.nodes.analyze import AnalyzeNode
from loopgraph.nodes.implement import ImplementNode
from loopgraph.nodes.prioritize import PrioritizeNode
from loopgraph.nodes.record import RecordNode
from loopgraph.nodes.reflect import ReflectNode
from loopgraph.nodes.summary import SummaryNode
from loopgraph.nodes.verify import VerifyNode
from loopgraph.safety.guardrails import Guardrails
from loopgraph.tools import create_implement_registry, create_verify_registry


@dataclass
class EngineConfig:
    model: str = "glm-5.3-flash"
    base_url: str = "https://api.z.ai/api/paas/v4/"
    api_key_env: str = "ZAI_API_KEY"
    api_key: Optional[str] = None
    verify_model: Optional[str] = None
    command_timeout: int = 120
    max_output_chars: int = 6000
    max_loop_iters: int = 25
    max_verify_iters: int = 8
    budget_tokens: int = 2_000_000
    stop_on_fail: bool = False
    blocked_patterns: Optional[List[str]] = None
    exclude_dirs: Optional[List[str]] = None

    @classmethod
    def from_file_or_defaults(cls, config_path: Optional[Union[str, Path]] = None) -> EngineConfig:
        """Loads configuration from `config_path`, or returns built-in defaults.

        Raises FileNotFoundError when an explicit path was given but does not exist.
        Silently falling back to defaults there would run the agent with a different
        model and a different token ceiling than the user asked for, with no indication
        that their file was never read.
        """
        if config_path is None:
            return cls()

        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"config dosyası bulunamadı: {path}")

        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(
                f"config dosyası bir JSON nesnesi olmalı, {type(data).__name__} bulundu: {path}"
            )

        known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        unknown = sorted(set(data) - set(known))
        if unknown:
            # Surfaced rather than dropped: a typo'd key would otherwise look applied.
            print(f"  [!] config.json içinde tanınmayan anahtar(lar) yok sayıldı: {', '.join(unknown)}")
        return cls(**known)


@dataclass
class ExecutionReport:
    total_tasks: int
    completed_tasks: int
    blocked_tasks: int
    failed_tasks: int
    tokens_used: int
    state: ProjectState


class GraphEngine:
    def __init__(
        self,
        project_path: Union[str, Path],
        config: Optional[EngineConfig] = None,
        on_step: Optional[Callable[[str, Any], None]] = None,
    ):
        self.project_path = Path(project_path).resolve()
        self.config = config or EngineConfig()
        self.on_step = on_step

        # 1. Safety & Guardrails
        self.guardrails = Guardrails(
            project_path=self.project_path,
            blocked_patterns=self.config.blocked_patterns,
            exclude_dirs=self.config.exclude_dirs,
        )

        # 2. Memory managers
        self.vision_mgr = VisionManager(self.project_path)
        self.board_mgr = BoardManager(self.project_path)
        self.ledger_mgr = LedgerManager(self.project_path)

        # 3. LLM Client
        self.llm = LLMClient(
            model=self.config.model,
            base_url=self.config.base_url,
            api_key=self.config.api_key,
            api_key_env=self.config.api_key_env,
        )

        # 4. Tool Registries
        self.implement_tools = create_implement_registry(self.guardrails)
        self.verify_tools = create_verify_registry(self.guardrails)

        # 5. ReAct Loop Engine
        def _step_callback(it: int, fn: str, preview: str):
            if self.on_step:
                self.on_step("loop_step", {"iteration": it, "tool": fn, "preview": preview})

        self.loop_engine = LoopEngine(
            llm=self.llm,
            tool_registry=self.implement_tools,
            max_iters=self.config.max_loop_iters,
            budget_tokens=self.config.budget_tokens,
            on_step_callback=_step_callback,
        )

        # 6. State
        self.state = ProjectState(project_path=self.project_path)
        self.completed_tasks_count = 0
        self.max_tasks_to_run = 3

        # 7. Build Graph
        self.graph = self._build_graph()
        self.runner = self.graph.compile()

    def _build_graph(self) -> StateGraph:
        g = StateGraph()

        # Nodes
        analyze_node = AnalyzeNode(
            llm=self.llm,
            guardrails=self.guardrails,
            vision_mgr=self.vision_mgr,
            board_mgr=self.board_mgr,
        )
        prioritize_node = PrioritizeNode()
        implement_node = ImplementNode(
            loop_engine=self.loop_engine, guardrails=self.guardrails
        )
        verify_node = VerifyNode(
            llm=self.llm,
            verify_tools=self.verify_tools,
            guardrails=self.guardrails,
            max_iters=self.config.max_verify_iters,
            verify_model=self.config.verify_model,
        )
        reflect_node = ReflectNode()
        record_node = RecordNode(board_mgr=self.board_mgr, ledger_mgr=self.ledger_mgr)
        summary_node = SummaryNode()

        g.add_node(analyze_node)
        g.add_node(prioritize_node)
        g.add_node(implement_node)
        g.add_node(verify_node)
        g.add_node(reflect_node)
        g.add_node(record_node)
        g.add_node(summary_node)

        # Entry
        g.set_entry_point("analyze")

        # Static Edges
        g.add_edge("analyze", "prioritize")

        # Conditional Edge from Prioritize
        def route_prioritize(state: ProjectState, signal: Optional[str]) -> str:
            if signal == "TASK_SELECTED":
                return "implement"
            return "summary"

        g.add_conditional_edge("prioritize", route_prioritize)

        # Conditional Edge from Implement
        def route_implement(state: ProjectState, signal: Optional[str]) -> str:
            if signal == "IMPLEMENT_DONE":
                return "verify"
            return "reflect"

        g.add_conditional_edge("implement", route_implement)

        # Conditional Edge from Verify
        def route_verify(state: ProjectState, signal: Optional[str]) -> str:
            if signal == "VERIFY_PASS":
                return "record"
            return "reflect"

        g.add_conditional_edge("verify", route_verify)

        # Conditional Edge from Reflect
        def route_reflect(state: ProjectState, signal: Optional[str]) -> str:
            if signal == "RETRY_TASK":
                return "implement"
            return "record"

        g.add_conditional_edge("reflect", route_reflect)

        # Conditional Edge from Record
        def route_record(state: ProjectState, signal: Optional[str]) -> str:
            # Check if task passed
            last_verify = state.metadata.get("last_verify_result", {})
            passed = last_verify.get("passed", False)
            if passed:
                self.completed_tasks_count += 1
            elif self.config.stop_on_fail:
                return "summary"

            if self.completed_tasks_count >= self.max_tasks_to_run:
                return "summary"

            if self.llm.total_tokens_used >= self.config.budget_tokens:
                return "summary"

            return "prioritize"

        g.add_conditional_edge("record", route_record)

        # Static Edge from Summary to End
        g.add_edge("summary", END)

        return g

    def plan_only(self) -> List[Task]:
        """Runs analysis and updates BOARD.md without implementing code."""
        self.vision_mgr.ensure_exists()
        analyze_node = AnalyzeNode(
            llm=self.llm,
            guardrails=self.guardrails,
            vision_mgr=self.vision_mgr,
            board_mgr=self.board_mgr,
        )
        analyze_node.run(self.state)
        return self.state.tasks

    def run(
        self,
        max_tasks: int = 3,
        stop_on_fail: Optional[bool] = None,
        plan_only: bool = False,
    ) -> ExecutionReport:
        if plan_only:
            tasks = self.plan_only()
            return ExecutionReport(
                total_tasks=len(tasks),
                completed_tasks=0,
                blocked_tasks=0,
                failed_tasks=0,
                tokens_used=self.llm.total_tokens_used,
                state=self.state,
            )

        self.max_tasks_to_run = max_tasks
        if stop_on_fail is not None:
            self.config.stop_on_fail = stop_on_fail

        def on_node_start(node_name: str, state: ProjectState):
            if self.on_step:
                self.on_step("node_start", {"node": node_name, "task": state.current_task})

        def on_node_finish(node_name: str, signal: Optional[str], state: ProjectState):
            if self.on_step:
                self.on_step("node_finish", {"node": node_name, "signal": signal})

        self.runner.run(
            self.state,
            max_steps=200,
            on_node_start=on_node_start,
            on_node_finish=on_node_finish,
        )

        done = sum(1 for t in self.state.tasks if t.status == TaskStatus.DONE)
        blocked = sum(1 for t in self.state.tasks if t.status == TaskStatus.BLOCKED)
        failed = sum(1 for t in self.state.tasks if t.status == TaskStatus.FAILED)

        return ExecutionReport(
            total_tasks=len(self.state.tasks),
            completed_tasks=done,
            blocked_tasks=blocked,
            failed_tasks=failed,
            tokens_used=self.llm.total_tokens_used,
            state=self.state,
        )
