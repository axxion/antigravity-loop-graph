"""
RecordNode for LoopGraph.
Updates BOARD.md and writes immutable audit entries to LEDGER.md.
"""

from __future__ import annotations

from typing import Optional

from loopgraph.core.graph import BaseNode
from loopgraph.core.state import ProjectState, TaskStatus
from loopgraph.memory.board import BoardManager
from loopgraph.memory.ledger import LedgerManager


class RecordNode(BaseNode):
    def __init__(
        self,
        board_mgr: BoardManager,
        ledger_mgr: LedgerManager,
        name: str = "record",
    ):
        super().__init__(name=name)
        self.board_mgr = board_mgr
        self.ledger_mgr = ledger_mgr

    def run(self, state: ProjectState) -> Optional[str]:
        task = state.current_task
        if not task:
            return "NO_TASK"

        verify_res = state.metadata.get("last_verify_result", {})
        loop_res = state.metadata.get("last_loop_result", {})

        passed = verify_res.get("passed", False)
        summary = loop_res.get("summary", "")
        feedback = verify_res.get("feedback", "")
        tokens = loop_res.get("tokens_used", 0)

        if passed:
            task.status = TaskStatus.DONE
        elif task.retry_count > task.max_retries:
            task.status = TaskStatus.BLOCKED
        else:
            task.status = TaskStatus.FAILED

        # Update board
        self.board_mgr.save(state.tasks)

        # Append to audit ledger
        self.ledger_mgr.record_entry(
            task=task,
            status=task.status,
            implementation_summary=summary,
            verification_details=feedback,
            tokens_used=tokens,
        )

        state.current_task = None
        return "RECORDED"
