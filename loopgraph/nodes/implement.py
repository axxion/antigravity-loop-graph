"""
ImplementNode for LoopGraph.
Runs the ReAct LoopEngine on the currently selected task.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List, Optional

from loopgraph.core.graph import BaseNode
from loopgraph.core.loop import LoopEngine, LoopResult
from loopgraph.core.state import ProjectState, TaskStatus
from loopgraph.safety.guardrails import Guardrails


class ImplementNode(BaseNode):
    def __init__(
        self,
        loop_engine: LoopEngine,
        guardrails: Guardrails,
        name: str = "implement",
    ):
        super().__init__(name=name)
        self.loop_engine = loop_engine
        self.guardrails = guardrails

    def _get_project_context(self, max_files: int = 15) -> str:
        root = self.guardrails.project_path
        files: List[str] = []
        for r, dirs, names in os.walk(root):
            dirs[:] = [d for d in dirs if not self.guardrails.is_dir_excluded(d)]
            for n in names:
                p = Path(r) / n
                try:
                    if p.stat().st_size < 300_000:
                        files.append(p.relative_to(root).as_posix())
                except OSError:
                    continue

        priority = [
            f
            for f in files
            if "/" not in f
            or re.search(r"(main|index|app|server|package\.json|requirements|pyproject)", f, re.I)
        ]

        snippets = []
        for rel in priority[:max_files]:
            try:
                content = (root / rel).read_text(encoding="utf-8", errors="replace")
                snippets.append(f"### {rel}\n```\n{content[:2000]}\n```")
            except OSError:
                continue

        return (
            f"Proje Dosyaları ({len(files)} dosya):\n"
            + "\n".join(files[:60])
            + "\n\nÖnemli Kod Parçaları:\n"
            + "\n\n".join(snippets)
        )

    def run(self, state: ProjectState) -> Optional[str]:
        task = state.current_task
        if not task:
            return "NO_TASK"

        project_ctx = self._get_project_context()
        feedback = task.last_feedback if task.retry_count > 0 else None

        result: LoopResult = self.loop_engine.run(
            task=task,
            project_context=project_ctx,
            feedback=feedback,
        )

        state.metadata["last_loop_result"] = {
            "is_done": result.is_done,
            "summary": result.summary,
            "iterations": result.iterations,
            "tokens_used": result.tokens_used,
            "error": result.error,
        }

        if result.is_done:
            return "IMPLEMENT_DONE"
        else:
            return "IMPLEMENT_FAILED"
