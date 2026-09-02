"""
SummaryNode for LoopGraph.
Aggregates run statistics and outputs final development status.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from loopgraph.core.graph import BaseNode
from loopgraph.core.state import ProjectState, TaskStatus


class SummaryNode(BaseNode):
    def __init__(self, name: str = "summary"):
        super().__init__(name=name)

    def run(self, state: ProjectState) -> Optional[str]:
        done_count = sum(1 for t in state.tasks if t.status == TaskStatus.DONE)
        blocked_count = sum(1 for t in state.tasks if t.status == TaskStatus.BLOCKED)
        failed_count = sum(1 for t in state.tasks if t.status == TaskStatus.FAILED)
        todo_count = sum(1 for t in state.tasks if t.status == TaskStatus.TODO)
        total = len(state.tasks)

        summary_data = {
            "total_tasks": total,
            "done": done_count,
            "blocked": blocked_count,
            "failed": failed_count,
            "todo": todo_count,
            "tokens_used": state.tokens_used,
        }
        state.metadata["summary"] = summary_data
        return "SUMMARY_COMPLETE"
