"""
PrioritizeNode for LoopGraph.
Picks the next actionable task based on priority and dependency satisfaction.
"""

from __future__ import annotations

from typing import Optional

from loopgraph.core.graph import BaseNode
from loopgraph.core.state import ProjectState, TaskStatus


class PrioritizeNode(BaseNode):
    def __init__(self, name: str = "prioritize"):
        super().__init__(name=name)

    def run(self, state: ProjectState) -> Optional[str]:
        pending_tasks = state.get_pending_tasks()
        if not pending_tasks:
            state.current_task = None
            return "NO_TASKS_LEFT"

        # Select highest priority task
        next_task = pending_tasks[0]
        next_task.status = TaskStatus.IN_PROGRESS
        state.current_task = next_task
        return "TASK_SELECTED"
