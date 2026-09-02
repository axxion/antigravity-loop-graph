"""
Tests for BoardManager, LedgerManager, and Task Models.
"""

import tempfile
from pathlib import Path
from loopgraph.core.state import Task, TaskStatus, ProjectState
from loopgraph.memory.board import BoardManager
from loopgraph.memory.ledger import LedgerManager
from loopgraph.memory.vision import VisionManager


def test_board_serialization_and_parsing():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir).resolve()
        mgr = BoardManager(root)

        tasks = [
            Task(
                id="T1",
                title="Veritabanı bağlantısını kur",
                acceptance=["db.py dosyası var", "connect_db() başarılı döner"],
                priority=1,
                effort="S",
                status=TaskStatus.DONE,
                depends_on=[],
            ),
            Task(
                id="T2",
                title="Kullanıcı kimlik doğrulama modülü",
                acceptance=["auth.py içinde hash kontrolü var", "test_auth geçer"],
                priority=2,
                effort="M",
                status=TaskStatus.TODO,
                depends_on=["T1"],
            ),
        ]

        # Save to markdown board
        mgr.save(tasks)
        assert mgr.file_path.exists()

        # Parse back from markdown
        parsed_tasks = mgr.parse()
        assert len(parsed_tasks) == 2
        assert parsed_tasks[0].id == "T1"
        assert parsed_tasks[0].status == TaskStatus.DONE
        assert len(parsed_tasks[0].acceptance) == 2
        assert parsed_tasks[1].id == "T2"
        assert parsed_tasks[1].depends_on == ["T1"]
        assert parsed_tasks[1].status == TaskStatus.TODO


def test_project_state_dependency_resolution():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir).resolve()
        state = ProjectState(project_path=root)

        t1 = Task(id="T1", title="Base setup", status=TaskStatus.DONE)
        t2 = Task(id="T2", title="Dependent task", depends_on=["T1"], status=TaskStatus.TODO, priority=2)
        t3 = Task(id="T3", title="Blocked task", depends_on=["T4"], status=TaskStatus.TODO, priority=1)
        t4 = Task(id="T4", title="Unfinished base", status=TaskStatus.TODO, priority=3)

        state.tasks = [t1, t2, t3, t4]

        pending = state.get_pending_tasks()
        # t1 is DONE -> excluded
        # t2's dep t1 is DONE -> included!
        # t3's dep t4 is not done -> excluded
        # t4 has no deps -> included!
        pending_ids = [t.id for t in pending]
        assert "T2" in pending_ids
        assert "T4" in pending_ids
        assert "T3" not in pending_ids  # Cannot run T3 before T4 is done


def test_ledger_logging():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir).resolve()
        ledger = LedgerManager(root)

        task = Task(
            id="T1",
            title="Setup config",
            acceptance=["config.json oluşturuldu"],
            priority=1,
            retry_count=1,
        )

        ledger.record_entry(
            task=task,
            status=TaskStatus.DONE,
            implementation_summary="Dosya yazıldı ve doğrulandı.",
            verification_details="VERDICT: PASS - Testler geçti.",
            tokens_used=1500,
        )

        content = ledger.file_path.read_text(encoding="utf-8")
        assert "## [T1] Setup config" in content
        assert "DONE" in content
        assert "1,500" in content
