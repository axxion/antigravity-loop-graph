"""
AnalyzeNode for LoopGraph.
Scans project structure, reads VISION.md, and generates verifiable tasks via LLM.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from loopgraph.core.graph import BaseNode
from loopgraph.core.state import ProjectState, Task, TaskStatus
from loopgraph.llm.client import LLMClient
from loopgraph.memory.board import BoardManager
from loopgraph.memory.vision import VisionManager
from loopgraph.safety.guardrails import Guardrails

logger = logging.getLogger("loopgraph.analyze")


class AnalyzeNode(BaseNode):
    def __init__(
        self,
        llm: LLMClient,
        guardrails: Guardrails,
        vision_mgr: VisionManager,
        board_mgr: BoardManager,
        name: str = "analyze",
    ):
        super().__init__(name=name)
        self.llm = llm
        self.guardrails = guardrails
        self.vision_mgr = vision_mgr
        self.board_mgr = board_mgr

    def generate_project_snapshot(
        self, max_files: int = 30, chars_per_file: int = 2500
    ) -> str:
        """Collects file tree and key file headers for LLM context."""
        root = self.guardrails.project_path
        files: List[str] = []

        for r, dirs, names in os.walk(root):
            dirs[:] = [d for d in dirs if not self.guardrails.is_dir_excluded(d)]
            for n in names:
                p = Path(r) / n
                try:
                    if p.stat().st_size < 400_000:
                        rel = p.relative_to(root).as_posix()
                        files.append(rel)
                except OSError:
                    continue

        files.sort()
        tree_preview = "\n".join(files[:150])

        # Prioritize key config / entry files
        priority_files = [
            f
            for f in files
            if "/" not in f
            or re.search(
                r"(main|index|app|server|package\.json|requirements|pyproject\.toml|README)",
                f,
                re.IGNORECASE,
            )
        ]

        snippets = []
        for rel in priority_files[:max_files]:
            try:
                full_p = root / rel
                content = full_p.read_text(encoding="utf-8", errors="replace")
                head = content[:chars_per_file]
                snippets.append(f"### {rel}\n```\n{head}\n```")
            except OSError:
                continue

        return (
            f"## Dosya Ağacı ({len(files)} dosya):\n{tree_preview}\n\n"
            f"## Önemli Dosya İçerikleri:\n" + "\n\n".join(snippets)
        )

    def run(self, state: ProjectState) -> Optional[str]:
        vision = self.vision_mgr.read()
        existing_tasks = self.board_mgr.parse()
        board_text = (
            self.board_mgr.file_path.read_text(encoding="utf-8", errors="replace")
            if self.board_mgr.file_path.exists()
            else "Henüz pano yok."
        )

        snapshot = self.generate_project_snapshot()

        system_prompt = (
            "Sen uzman bir Graf ve Döngü Mühendisisin (Graph & Loop Engineer).\n"
            "Verilen projeyi, vizyonu ve mevcut panoyu inceleyerek doğrulanabilir, net yazılım geliştirme görevleri üretirsin.\n\n"
            "GÖREV ÜRETİM KURALLARI:\n"
            "1. Her görev küçük, atomik, bağımsız olarak test edilebilir ve geri alınabilir olmalıdır.\n"
            "2. Kabul kriterleri (acceptance) doğrudan çalıştırılabilir kontrol cümleleri olmalıdır (örn: 'pytest tests/test_auth.py geçer', 'npm run build hatasız tamamlanır', 'X fonksiyonu Y parametresi ile Z çıktısını verir').\n"
            "3. Öncelik Sırası: Önce mevcut hataları ve temel eksikleri onar, sonra yeni özellik ekle.\n"
            "4. Bağımlılıklar (depends_on): Bir görevin çalışması için önce bitmesi gereken görev ID'lerini listele (örn: ['T1']).\n"
            "5. SADECE geçerli JSON döndür, başka hiçbir açıklama veya markdown metni yazma.\n\n"
            "JSON Formatı:\n"
            "{\n"
            '  "tasks": [\n'
            '    {\n'
            '      "id": "T1",\n'
            '      "title": "Görev Başlığı",\n'
            '      "why": "Neden gerekli?",\n'
            '      "acceptance": ["kriter 1", "kriter 2"],\n'
            '      "priority": 1,\n'
            '      "effort": "S|M|L",\n'
            '      "depends_on": []\n'
            '    }\n'
            '  ]\n'
            "}"
        )

        user_prompt = (
            f"# Proje Vizyonu (VISION.md)\n{vision}\n\n"
            f"# Mevcut Geliştirme Panosu (BOARD.md)\n{board_text}\n\n"
            f"# Proje Dosya ve Kod Yapısı\n{snapshot}"
        )

        tasks_from_llm: List[Task] = []

        # If LLM is configured, request dynamic task plan
        if self.llm.is_configured:
            try:
                resp = self.llm.chat([
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ])
                if resp and resp.content:
                    # Extract JSON block
                    m = re.search(r"\{.*\}", resp.content, re.DOTALL)
                    if m:
                        try:
                            data = json.loads(m.group(0))
                            raw_tasks = data.get("tasks", [])
                            for t_dict in raw_tasks:
                                tasks_from_llm.append(Task.from_dict(t_dict))
                        except json.JSONDecodeError as e:
                            logger.warning("LLM plan yanıtı JSON olarak ayrıştırılamadı: %s", e)
            except Exception as e:
                logger.warning(
                    "LLM plan çağrısı başarısız oldu, heuristic planner'a düşülüyor: %s", e
                )

        # If LLM returned no tasks or is not configured, use HeuristicPlanner directly
        if not tasks_from_llm:
            from loopgraph.nodes.heuristic_planner import HeuristicPlanner
            tasks_from_llm = HeuristicPlanner.generate_plan(
                self.guardrails.project_path, vision
            )

        # Merge new tasks with existing tasks preserving status
        merged_tasks: List[Task] = []
        existing_by_id = {t.id: t for t in existing_tasks}

        # Add newly generated tasks (preserving existing ones if ID collision)
        for t in tasks_from_llm:
            if t.id in existing_by_id:
                old = existing_by_id[t.id]
                # Preserve done/in_progress status
                if old.status in (TaskStatus.DONE, TaskStatus.BLOCKED, TaskStatus.FAILED):
                    t.status = old.status
                merged_tasks.append(t)
            else:
                merged_tasks.append(t)

        # Add any old tasks that were not in LLM output but exist in board
        llm_ids = {t.id for t in tasks_from_llm}
        for old in existing_tasks:
            if old.id not in llm_ids and old.status != TaskStatus.DONE:
                merged_tasks.append(old)

        if not merged_tasks:
            # Fallback to existing or empty
            merged_tasks = existing_tasks

        state.tasks = merged_tasks
        self.board_mgr.save(state.tasks)
        return "ANALYSIS_COMPLETE"
