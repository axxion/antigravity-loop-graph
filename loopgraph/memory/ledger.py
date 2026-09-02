"""
LEDGER.md memory manager for LoopGraph.
Provides immutable audit trail for completed, failed, and blocked tasks.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from loopgraph.core.state import Task, TaskStatus

LEDGER_HEADER = """# İş Defteri (LEDGER.md)

<!-- Bu dosya tamamlanan ve denetlenen her görevin kesin kayıt günlüğüdür (Audit Trail). -->
"""


class LedgerManager:
    def __init__(self, project_path: Path):
        self.project_path = Path(project_path).resolve()
        self.file_path = self.project_path / "LEDGER.md"

    def ensure_exists(self) -> Path:
        if not self.file_path.exists():
            self.file_path.write_text(LEDGER_HEADER, encoding="utf-8")
        return self.file_path

    def record_entry(
        self,
        task: Task,
        status: TaskStatus,
        implementation_summary: str = "",
        verification_details: str = "",
        tokens_used: int = 0,
    ) -> None:
        self.ensure_exists()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        status_emoji = {
            TaskStatus.DONE: "✅ DONE",
            TaskStatus.BLOCKED: "⚠️ BLOCKED",
            TaskStatus.FAILED: "❌ FAILED",
        }.get(status, str(status.value).upper())

        entry_lines = [
            f"\n## [{task.id}] {task.title}",
            f"- **Tarih & Saat:** {timestamp}",
            f"- **Durum:** {status_emoji}",
            f"- **Öncelik:** {task.priority} | **Efor:** {task.effort} | **Deneme Sayısı:** {task.retry_count}",
        ]

        if task.acceptance:
            entry_lines.append("- **Kabul Kriterleri:**")
            for c in task.acceptance:
                entry_lines.append(f"  - [x] {c}")

        if implementation_summary:
            entry_lines.append(f"- **Uygulama Özeti:** {implementation_summary}")

        if verification_details:
            entry_lines.append(f"- **Doğrulama Notu:** {verification_details}")

        if tokens_used > 0:
            entry_lines.append(f"- **Harcanan Token:** {tokens_used:,}")

        entry_lines.append("")

        with self.file_path.open("a", encoding="utf-8") as f:
            f.write("\n".join(entry_lines) + "\n")
