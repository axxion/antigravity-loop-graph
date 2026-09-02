"""
Regressions for BOARD.md parsing. The board is hand-editable, so malformed rows are
expected — the defect was that seven distinct corruption classes were absorbed without
a single warning, so a task could vanish, change priority, or be re-run as TODO while
the tool reported success.
"""

import tempfile
from pathlib import Path

from loopgraph.core.state import TaskStatus
from loopgraph.memory.board import BoardManager

HEADER = (
    "# Gelistirme Panosu\n\n"
    "| ID | Gorev | Kabul Kriterleri | Oncelik | Bagimliliklar | Durum |\n"
    "|----|-------|------------------|---------|---------------|-------|\n"
)


def _board(rows):
    tmpdir = tempfile.mkdtemp()
    path = Path(tmpdir)
    (path / "BOARD.md").write_text(HEADER + rows, encoding="utf-8")
    mgr = BoardManager(path)
    return mgr, mgr.parse()


def test_row_whose_title_contains_dashes_is_not_dropped():
    """The separator-row check used to match any line containing '---', silently
    deleting real tasks whose text happened to contain a dash run."""
    mgr, tasks = _board("| T1 | Fix the --- separator bug | · kriter | 1 | - | todo |\n")
    assert [t.id for t in tasks] == ["T1"], "task with '---' in its title was dropped"
    assert mgr.warnings == []


def test_separator_row_is_still_skipped():
    mgr, tasks = _board("|----|----|----|----|----|----|\n| T1 | Gorev | · k | 1 | - | todo |\n")
    assert [t.id for t in tasks] == ["T1"]


def test_short_row_is_reported_not_silently_dropped():
    mgr, tasks = _board("| T9 | Eksik sutun |\n")
    assert tasks == []
    assert any("T9" in w and "sütun" in w for w in mgr.warnings), mgr.warnings


def test_non_integer_priority_is_reported():
    mgr, tasks = _board("| T1 | Gorev | · k | 1.5 | - | todo |\n")
    assert tasks[0].priority == 99, "non-integer priority must not be coerced silently"
    assert any("1.5" in w for w in mgr.warnings), mgr.warnings


def test_unknown_status_is_reported():
    mgr, tasks = _board("| T1 | Gorev | · k | 1 | - | ARCHIVED |\n")
    assert tasks[0].status == TaskStatus.TODO
    assert any("ARCHIVED" in w for w in mgr.warnings), mgr.warnings


def test_duplicate_task_id_is_reported():
    mgr, tasks = _board(
        "| T1 | Birinci | · k | 1 | - | todo |\n| T1 | Ikinci | · k | 2 | - | todo |\n"
    )
    assert len(tasks) == 2
    assert any("kimli" in w.lower() for w in mgr.warnings), mgr.warnings


def test_clean_board_produces_no_warnings():
    mgr, tasks = _board(
        "| T1 | Birinci | · k | 1 | - | done |\n"
        "| T2 | Ikinci | · k1<br>· k2 | 2 | T1 | todo |\n"
    )
    assert len(tasks) == 2
    assert mgr.warnings == [], f"false positives on a clean board: {mgr.warnings}"
    assert tasks[1].depends_on == ["T1"]
    assert tasks[1].acceptance == ["k1", "k2"]


def test_warnings_reset_between_parses():
    mgr, _ = _board("| T1 | Gorev | · k | 1.5 | - | todo |\n")
    assert mgr.warnings
    (mgr.file_path).write_text(HEADER + "| T1 | Gorev | · k | 1 | - | todo |\n", encoding="utf-8")
    mgr.parse()
    assert mgr.warnings == [], "stale warnings carried over from the previous parse"
