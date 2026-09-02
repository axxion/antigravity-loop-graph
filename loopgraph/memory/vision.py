"""
VISION.md memory manager for LoopGraph.
"""

from __future__ import annotations

from pathlib import Path

VISION_TEMPLATE = """# Proje Vizyonu

<!-- Bu projenin nihai amacını, temel gereksinimlerini ve başarı kriterlerini 3-5 cümleyle tanımlayın.
Motor, tüm analiz ve görev planlamasını bu vizyon belgesine göre şekillendirir. -->

- **Amaç:** 
- **Hedef Kitle & Kullanım:** 
- **Temel Mimari & Tercihler:** 
- **Başarı Kriterleri (Definition of Done):** 
"""


class VisionManager:
    def __init__(self, project_path: Path):
        self.project_path = Path(project_path).resolve()
        self.file_path = self.project_path / "VISION.md"

    def ensure_exists(self) -> Path:
        if not self.file_path.exists():
            self.file_path.write_text(VISION_TEMPLATE, encoding="utf-8")
        return self.file_path

    def read(self) -> str:
        self.ensure_exists()
        return self.file_path.read_text(encoding="utf-8", errors="replace")

    def write(self, content: str) -> None:
        self.file_path.write_text(content, encoding="utf-8")
