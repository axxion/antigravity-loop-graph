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
        # Populated by parse(): human-readable notes about rows that were dropped or
        # coerced. BOARD.md is hand-editable, so a malformed row is expected — but it
        # must never disappear without the user being told, or work silently vanishes.
        self.warnings: List[str] = []

    def ensure_exists(self) -> Path:
        if not self.file_path.exists():
            self.file_path.write_text(BOARD_HEADER, encoding="utf-8")
        return self.file_path

    def parse(self) -> List[Task]:
        if not self.file_path.exists():
            return []

        content = self.file_path.read_text(encoding="utf-8", errors="replace")
        tasks: List[Task] = []
        self.warnings = []
        seen_ids = {}

        for line_no, line in enumerate(content.splitlines(), start=1):
            line_str = line.strip()
            if not line_str.startswith("|"):
                continue

            # The separator row under the header is `|----|----|`; skip it, but do not
            # skip a real task row that merely contains "---" somewhere in its text.
            if re.fullmatch(r"\|[\s:\-|]+\|?", line_str):
                continue

            cells = [c.strip() for c in line_str.strip("|").split("|")]

            task_id = cells[0] if cells else ""
            looks_like_task = bool(
                re.match(r"^T\d+", task_id, re.IGNORECASE) or task_id.upper().startswith("TASK")
            )

            if len(cells) < 4:
                if looks_like_task:
                    self.warnings.append(
                        f"satır {line_no}: [{task_id}] {len(cells)} sütun bulundu, en az 4 gerekli "
                        f"— görev yok sayıldı (metinde kaçırılmamış '|' olabilir)"
                    )
                continue

            if not looks_like_task:
                continue  # header row or free-form table, not a task

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

            # Clean priority. Stripping non-digits would silently turn "1.5" into 15 and
            # "-1" into 1, so anything that is not a plain integer is reported instead.
            priority_text = raw_priority.strip()
            if re.fullmatch(r"\d+", priority_text):
                priority = int(priority_text)
            else:
                priority = 99
                if priority_text and priority_text != "—":
                    self.warnings.append(
                        f"satır {line_no}: [{task_id}] öncelik '{raw_priority}' bir tam sayı değil "
                        f"— {priority} kabul edildi"
                    )

            # Clean dependencies
            deps: List[str] = []
            if raw_deps and raw_deps != "—":
                for d in re.split(r"[,;\s]+", raw_deps):
                    clean_d = d.strip()
                    if clean_d:
                        deps.append(clean_d)

            # Parse status. An unrecognised value silently becoming TODO can re-run work
            # that was already finished, so it is reported.
            status_val = raw_status.lower().strip()
            try:
                status = TaskStatus(status_val)
            except ValueError:
                status = TaskStatus.TODO
                if status_val and status_val != "—":
                    valid = ", ".join(s.value for s in TaskStatus)
                    self.warnings.append(
                        f"satır {line_no}: [{task_id}] durum '{raw_status}' tanınmadı "
                        f"— 'todo' kabul edildi (geçerli: {valid})"
                    )

            if task_id in seen_ids:
                self.warnings.append(
                    f"satır {line_no}: [{task_id}] görev kimliği {seen_ids[task_id]}. satırda da "
                    f"kullanılmış — bağımlılıklar belirsiz hale gelir"
                )
            else:
                seen_ids[task_id] = line_no

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
