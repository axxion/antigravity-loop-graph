"""
Task status signaling tools for LoopGraph.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from loopgraph.tools.base import BaseTool, ToolResult


class TaskDoneTool(BaseTool):
    name = "task_done"
    description = (
        "Görevin başarıyla tamamlandığını ve tüm kabul kriterlerinin uygulandığını bildirir. "
        "Bu aracı çağırmadan önce kabul kriterlerini run_command veya testlerle mutlaka KENDİNİZ doğrulamış olmalısınız."
    )
    parameters = {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "Yapılan değişikliklerin ve doğrulama kanıtlarının kısa özeti.",
            },
            "verified_criteria": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Doğrulandığı kanıtlanan kabul kriterleri listesi.",
            },
        },
        "required": ["summary"],
    }

    def execute(
        self,
        summary: str,
        verified_criteria: Optional[List[str]] = None,
        **kwargs,
    ) -> ToolResult:
        crit_text = ""
        if verified_criteria:
            crit_text = "\nDoğrulanan kriterler:\n" + "\n".join(f"- {c}" for c in verified_criteria)
        
        return ToolResult(
            output=f"Görev tamamlandı olarak işaretlendi.\nÖzet: {summary}{crit_text}",
            is_terminal=True,
            success=True,
            metadata={"summary": summary, "verified_criteria": verified_criteria or []},
        )
