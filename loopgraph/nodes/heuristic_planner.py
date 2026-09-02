"""
Heuristic / Static Project Vision and Task Planner for LoopGraph.
Extracts actionable, structured tasks directly from VISION.md and project files
WITHOUT requiring an external LLM API key.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List

from loopgraph.core.state import Task, TaskStatus


class HeuristicPlanner:
    """
    Parses VISION.md, package.json, requirements.txt, and project structure
    to deterministically construct structured development tasks.
    """

    @staticmethod
    def parse_vision_sections(vision_text: str) -> List[dict]:
        """Extracts bullet points, numbered items, or headers from VISION.md."""
        tasks_raw = []
        lines = vision_text.splitlines()

        current_category = "General"
        for line in lines:
            line_str = line.strip()
            if not line_str or line_str.startswith("<!--"):
                continue

            # Header category
            if line_str.startswith("#"):
                clean_h = line_str.lstrip("#").strip()
                if clean_h and not any(k in clean_h.lower() for k in ("vizyon", "vision", "tanım", "hedef")):
                    current_category = clean_h
                continue

            # Bullet points or numbered lists
            m = re.match(r"^[-*•\d\.]+\s+(.+)$", line_str)
            if m:
                content = m.group(1).strip()
                # Skip template headers
                if content.startswith("**") and content.endswith("**"):
                    continue
                if len(content) > 10:
                    tasks_raw.append({"text": content, "category": current_category})

        return tasks_raw

    @classmethod
    def generate_plan(cls, project_path: Path, vision_text: str) -> List[Task]:
        """Generates structured Task objects without needing an external API key."""
        proj = Path(project_path).resolve()
        raw_items = cls.parse_vision_sections(vision_text)

        tasks: List[Task] = []
        idx = 1

        # Check existing project files to identify initial sanity task
        has_package_json = (proj / "package.json").exists()
        has_pyproject = (proj / "pyproject.toml").exists() or (proj / "requirements.txt").exists()

        if has_package_json:
            tasks.append(
                Task(
                    id=f"T{idx}",
                    title="[Setup & Sanity] Proje Bağımlılıkları ve Build Doğrulaması",
                    why="Geliştirmeye başlamadan önce derleme ve paket bütünlüğünü garantiye almak.",
                    acceptance=["npm run build veya test komutu hatasız çalışmalıdır."],
                    priority=1,
                    effort="S",
                    depends_on=[],
                )
            )
            idx += 1
        elif has_pyproject:
            tasks.append(
                Task(
                    id=f"T{idx}",
                    title="[Setup & Sanity] Python Bağımlılık ve Test Doğrulaması",
                    why="Temel test paketinin ve ortamın çalıştığını doğrulamak.",
                    acceptance=["pytest veya derleme komutu hatasız çalışmalıdır."],
                    priority=1,
                    effort="S",
                    depends_on=[],
                )
            )
            idx += 1

        # Convert vision items into structured tasks
        for item in raw_items:
            t_text = item["text"]
            cat = item["category"]

            # Clean bold markers
            clean_title = re.sub(r"\*\*([^*]+)\*\*", r"\1", t_text)
            if ":" in clean_title:
                parts = clean_title.split(":", 1)
                title = f"[{cat}] {parts[0].strip()}: {parts[1].strip()[:80]}"
                why = parts[1].strip()
            else:
                title = f"[{cat}] {clean_title[:90]}"
                why = clean_title

            prev_id = [f"T{idx-1}"] if idx > 1 else []
            tasks.append(
                Task(
                    id=f"T{idx}",
                    title=title,
                    why=why,
                    acceptance=[
                        f"İlgili modül kodlanmalı ve tip/lint hataları giderilmelidir.",
                        f"Birim testi veya kabul kriteri başarıyla doğrulanmalıdır.",
                    ],
                    priority=min(5, max(1, (idx // 2) + 1)),
                    effort="M",
                    depends_on=prev_id,
                )
            )
            idx += 1

        # If vision had no parsable bullet points, create default baseline tasks
        if len(tasks) <= 1:
            tasks.append(
                Task(
                    id=f"T{idx}",
                    title="[Core Module] Çekirdek Modül ve Mimari Kurulumu",
                    why="VISION.md belgesinde tanımlanan birincil sistem bileşenini inşa etmek.",
                    acceptance=["Temel veri modelleri ve servis katmanı kodlanmalıdır."],
                    priority=2,
                    effort="M",
                    depends_on=[f"T{idx-1}"] if idx > 1 else [],
                )
            )

        return tasks
