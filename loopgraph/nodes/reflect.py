"""
ReflectNode for LoopGraph.
Synthesizes verification feedback and routes task for retry or failure.
"""

from __future__ import annotations

from typing import Optional

from loopgraph.core.graph import BaseNode
from loopgraph.core.state import ProjectState, TaskStatus


class ReflectNode(BaseNode):
    def __init__(self, name: str = "reflect"):
        super().__init__(name=name)

    def run(self, state: ProjectState) -> Optional[str]:
        task = state.current_task
        if not task:
            return "NO_TASK"

        verify_res = state.metadata.get("last_verify_result", {})
        feedback = verify_res.get("feedback", "Doğrulama başarısız oldu.")
        
        task.retry_count += 1
        task.last_feedback = feedback

        if task.retry_count <= task.max_retries:
            return "RETRY_TASK"
        else:
            return "RETRIES_EXHAUSTED"
