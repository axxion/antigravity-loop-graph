"""
Regression test: `loopgraph init` must scaffold Antigravity IDE Native Mode
integration files (.agents/skills/loopgraph/SKILL.md, .agents/rules/loopgraph.md)
into the TARGET project, not just exist inside this repository. Without this,
README's "Antigravity IDE Native (Zero API Key)" claim did not hold for any
project other than this repo itself.
"""

import tempfile
from pathlib import Path

from loopgraph.antigravity_scaffold import scaffold_antigravity_integration


def test_scaffold_writes_skill_and_rules_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        proj = Path(tmpdir)
        written = scaffold_antigravity_integration(proj)

        skill_file = proj / ".agents" / "skills" / "loopgraph" / "SKILL.md"
        rules_file = proj / ".agents" / "rules" / "loopgraph.md"

        assert skill_file.exists()
        assert rules_file.exists()
        assert skill_file in written and rules_file in written

        skill_content = skill_file.read_text(encoding="utf-8")
        assert "name: loopgraph" in skill_content
        assert "| ID | Görev | Kabul Kriterleri | Öncelik | Bağımlılıklar | Durum |" in skill_content
        assert "todo`, `in_progress`, `done`, `failed`, `blocked`" in skill_content


def test_scaffold_is_idempotent_and_preserves_edits():
    with tempfile.TemporaryDirectory() as tmpdir:
        proj = Path(tmpdir)
        scaffold_antigravity_integration(proj)

        skill_file = proj / ".agents" / "skills" / "loopgraph" / "SKILL.md"
        skill_file.write_text("# user-customized skill", encoding="utf-8")

        written_again = scaffold_antigravity_integration(proj)

        assert written_again == []
        assert skill_file.read_text(encoding="utf-8") == "# user-customized skill"
