"""
Unit tests for Heuristic / Zero-API Vision Planner.
"""

import tempfile
from pathlib import Path

from loopgraph.nodes.heuristic_planner import HeuristicPlanner
from loopgraph.engine import GraphEngine, EngineConfig


def test_heuristic_planner_from_vision():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "package.json").write_text('{"name": "test-app"}', encoding="utf-8")

        vision_sample = """# Proje Vizyonu

- **Hedef 1: Kimlik Doğrulama**: JWT tabanlı güvenli kullanıcı oturumu.
- **Hedef 2: Veritabanı Modelleri**: SQLite / PostgreSQL şemaları oluşturulmalı.
- **Hedef 3: API Endpointleri**: REST servisleri ve OpenAPI şeması yazılmalı.
"""
        tasks = HeuristicPlanner.generate_plan(root, vision_sample)
        assert len(tasks) >= 4
        assert tasks[0].id == "T1"
        assert "Setup" in tasks[0].title
        assert "Kimlik Doğrulama" in tasks[1].title
        assert "Veritabanı Modelleri" in tasks[2].title


def test_plan_without_api_key():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "VISION.md").write_text(
            "# Vizyon\n- **Modül A: Kullanıcı Paneli**: React tabanlı arayüz.\n- **Modül B: Bildirimler**: Push servisleri.",
            encoding="utf-8",
        )

        # Initialize engine without API key
        engine = GraphEngine(project_path=root, config=EngineConfig())
        tasks = engine.plan_only()

        assert len(tasks) >= 2
        assert (root / "BOARD.md").exists()
        board_content = (root / "BOARD.md").read_text(encoding="utf-8")
        assert "Kullanıcı Paneli" in board_content
