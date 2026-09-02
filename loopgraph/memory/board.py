"""
BOARD.md memory manager for LoopGraph.
Handles parsing and serializing tasks in the project development board.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional

from loopgraph.core.state import Task, TaskStatus

BOARD_HEADER = """# Geliştirme Panosu (BOARD.md)

<!-- Bu dosya LoopGraph motoru tarafından otomatik yönetilir. Manuel eklemeler için tablo formatını koruyun. -->

| ID | Görev | Kabul Kriterleri | Öncelik | Bağımlılıklar | Durum |
|----|-------|------------------|---------|---------------|-------|
"""


class BoardManager:
    def __init__(self, project_path: Path):
        self.project_path = Path(project_path).resolve()
        self.file_path = self.project_path / "BOARD.md"

    def ensure_exists(self) -> Path:
        if not self.file_path.exists():
            self.file_path.write_text(BOARD_HEADER, encoding="utf-8")
        return self.file_path

    def parse(self) -> List[Task]:
        if not self.file_path.exists():
            return []

        content = self.file_path.read_text(encoding="utf-8", errors="replace")
        tasks: List[Task] = []

        for line in content.splitlines():
            line_str = line.strip()
            if not line_str.startswith("|") or "---" in line_str:
                continue

            cells = [c.strip() for c in line_str.strip("|").split("|")]
            if len(cells) < 4:
                continue

            task_id = cells[0]
            if not re.match(r"^T\d+", task_id, re.IGNORECASE) and not task_id.startswith("TASK"):
                continue  # Skip header or invalid rows

            title = cells[1]
            raw_criteria = cells[2] if len(cells) > 2 else ""
            raw_priority = cells[3] if len(cells) > 3 else "99"
            raw_deps = cells[4] if len(cells) > 4 else "—"
            raw_status = cells[5] if len(cells) > 5 else "todo"

            # Clean acceptance criteria
            criteria: List[str] = []
            for item in re.split(r"<br\s*/?>|[\n\r]+", raw_criteria):
                clean_item = re.sub(r"^[·\-\*\s]+", "", item).strip()
                if clean_item and clean_item != "—":
                    criteria.append(clean_item)

            # Clean priority
            try:
                priority = int(re.sub(r"\D", "", raw_priority) or 99)
            except ValueError:
                priority = 99

            # Clean dependencies
            deps: List[str] = []
            if raw_deps and raw_deps != "—":
                for d in re.split(r"[,;\s]+", raw_deps):
                    clean_d = d.strip()
                    if clean_d:
                        deps.append(clean_d)

            # Parse status
            status_val = raw_status.lower().strip()
            try:
                status = TaskStatus(status_val)
            except ValueError:
                status = TaskStatus.TODO

            tasks.append(
                Task(
                    id=task_id,
                    title=title,
                    acceptance=criteria,
                    priority=priority,
                    depends_on=deps,
                    status=status,
                )
            )

        return tasks

    def save(self, tasks: List[Task]) -> None:
        lines = [
            "# Geliştirme Panosu (BOARD.md)",
            "",
            "<!-- Bu dosya LoopGraph motoru tarafından otomatik yönetilir. -->",
            "",
            "| ID | Görev | Kabul Kriterleri | Öncelik | Bağımlılıklar | Durum |",
            "|----|-------|------------------|---------|---------------|-------|",
        ]

        for t in tasks:
            crit_str = "<br>".join(f"· {c}" for c in t.acceptance) if t.acceptance else "—"
            deps_str = ", ".join(t.depends_on) if t.depends_on else "—"
            status_str = t.status.value if isinstance(t.status, TaskStatus) else str(t.status)
            lines.append(
                f"| {t.id} | {t.title} | {crit_str} | {t.priority} | {deps_str} | {status_str} |"
            )

        self.file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
