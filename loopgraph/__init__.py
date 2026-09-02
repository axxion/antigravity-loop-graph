"""
LoopGraph: Autonomous Loop & Graph Engineering Engine.
"""

from loopgraph.core.graph import END, START, BaseNode, ConditionalEdge, Edge, GraphRunner, StateGraph
from loopgraph.core.loop import LoopEngine, LoopResult
from loopgraph.core.state import ProjectState, Task, TaskStatus
from loopgraph.engine import EngineConfig, ExecutionReport, GraphEngine
from loopgraph.llm.client import LLMClient, LLMResponse
from loopgraph.memory.board import BoardManager
from loopgraph.memory.ledger import LedgerManager
from loopgraph.memory.vision import VisionManager
from loopgraph.safety.guardrails import Guardrails
from loopgraph.tools.base import BaseTool, ToolRegistry, ToolResult

__version__ = "0.2.0"

__all__ = [
    "GraphEngine",
    "EngineConfig",
    "ExecutionReport",
    "LoopEngine",
    "LoopResult",
    "StateGraph",
    "GraphRunner",
    "BaseNode",
    "ProjectState",
    "Task",
    "TaskStatus",
    "LLMClient",
    "LLMResponse",
    "Guardrails",
    "ToolRegistry",
    "BaseTool",
    "ToolResult",
    "BoardManager",
    "LedgerManager",
    "VisionManager",
    "START",
    "END",
]
