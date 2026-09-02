"""
LoopGraph Tools Package.
"""

from loopgraph.safety.guardrails import Guardrails
from loopgraph.tools.base import BaseTool, ToolRegistry, ToolResult
from loopgraph.tools.exec_tools import RunCommandTool
from loopgraph.tools.file_tools import (
    ReadFileTool,
    ReplaceContentTool,
    ViewFileTool,
    WriteFileTool,
)
from loopgraph.tools.search_tools import FindFilesTool, GrepSearchTool, ListDirTool
from loopgraph.tools.task_tools import TaskDoneTool


def create_implement_registry(guardrails: Guardrails) -> ToolRegistry:
    """Creates the full tool registry for implementation agents."""
    reg = ToolRegistry()
    reg.register(ReadFileTool(guardrails))
    reg.register(WriteFileTool(guardrails))
    reg.register(ReplaceContentTool(guardrails))
    reg.register(ViewFileTool(guardrails))
    reg.register(RunCommandTool(guardrails))
    reg.register(GrepSearchTool(guardrails))
    reg.register(FindFilesTool(guardrails))
    reg.register(ListDirTool(guardrails))
    reg.register(TaskDoneTool())
    return reg


def create_verify_registry(guardrails: Guardrails) -> ToolRegistry:
    """
    Creates read-only/audit tool registry for independent verifiers.
    Note: write_file, replace_content, task_done are EXCLUDED to prevent self-grading/tampering.
    """
    reg = ToolRegistry()
    reg.register(ReadFileTool(guardrails))
    reg.register(ViewFileTool(guardrails))
    reg.register(RunCommandTool(guardrails))
    reg.register(GrepSearchTool(guardrails))
    reg.register(FindFilesTool(guardrails))
    reg.register(ListDirTool(guardrails))
    return reg


__all__ = [
    "BaseTool",
    "ToolRegistry",
    "ToolResult",
    "ReadFileTool",
    "WriteFileTool",
    "ReplaceContentTool",
    "ViewFileTool",
    "RunCommandTool",
    "GrepSearchTool",
    "FindFilesTool",
    "ListDirTool",
    "TaskDoneTool",
    "create_implement_registry",
    "create_verify_registry",
]
