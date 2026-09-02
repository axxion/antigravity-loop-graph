"""
Tests for LoopGraph Tool Suite.
"""

import tempfile
from pathlib import Path
from loopgraph.safety.guardrails import Guardrails
from loopgraph.tools.file_tools import (
    ReadFileTool,
    WriteFileTool,
    ReplaceContentTool,
    ViewFileTool,
)
from loopgraph.tools.exec_tools import RunCommandTool
from loopgraph.tools.search_tools import GrepSearchTool, FindFilesTool, ListDirTool
from loopgraph.tools.task_tools import TaskDoneTool
from loopgraph.tools import create_implement_registry, create_verify_registry


def test_file_tools():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir).resolve()
        guard = Guardrails(project_path=root)

        # 1. Write file
        writer = WriteFileTool(guard)
        res = writer.execute(path="test.py", content="line1\nline2\nline3\n")
        assert res.success is True
        assert (root / "test.py").exists()

        # 2. Read file
        reader = ReadFileTool(guard)
        res = reader.execute(path="test.py", start_line=2, end_line=3)
        assert res.success is True
        assert "line2" in res.output
        assert "line3" in res.output
        assert "line1" not in res.output

        # 3. View file
        viewer = ViewFileTool(guard)
        res = viewer.execute(path="test.py")
        assert res.success is True
        assert "   1 | line1" in res.output

        # 4. Replace content (surgical)
        replacer = ReplaceContentTool(guard)
        res = replacer.execute(
            path="test.py",
            target_content="line2",
            replacement_content="line_modified",
        )
        assert res.success is True
        content = (root / "test.py").read_text(encoding="utf-8")
        assert "line_modified" in content
        assert "line2" not in content

        # Replace non-existent content should fail gracefully
        res = replacer.execute(
            path="test.py",
            target_content="nonexistent_string",
            replacement_content="xyz",
        )
        assert res.success is False
        assert "bulunamadı" in res.output


def test_search_and_discovery_tools():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir).resolve()
        guard = Guardrails(project_path=root)

        (root / "src").mkdir(parents=True)
        (root / "src" / "auth.py").write_text("def authenticate_user(token):\n    pass\n", encoding="utf-8")
        (root / "src" / "db.py").write_text("def connect_db():\n    pass\n", encoding="utf-8")

        # Grep search
        grep = GrepSearchTool(guard)
        res = grep.execute(pattern="authenticate_user")
        assert res.success is True
        assert "auth.py" in res.output
        assert "authenticate_user" in res.output

        # Find files
        finder = FindFilesTool(guard)
        res = finder.execute(pattern="*.py")
        assert res.success is True
        assert "auth.py" in res.output
        assert "db.py" in res.output

        # List dir
        lister = ListDirTool(guard)
        res = lister.execute()
        assert res.success is True
        assert "[DIR]  src/" in res.output


def test_command_execution():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir).resolve()
        guard = Guardrails(project_path=root)
        runner = RunCommandTool(guard)

        # Safe command (echo)
        res = runner.execute(command="python -c \"print('hello from python')\"")
        assert res.success is True
        assert "hello from python" in res.output

        # Blocked dangerous command
        res = runner.execute(command="git push origin main")
        assert res.success is False
        assert "REDDEDİLDİ" in res.output


def test_tool_registries():
    with tempfile.TemporaryDirectory() as tmpdir:
        guard = Guardrails(project_path=Path(tmpdir))
        imp_reg = create_implement_registry(guard)
        ver_reg = create_verify_registry(guard)

        # Implement registry has write and task_done
        assert imp_reg.get("write_file") is not None
        assert imp_reg.get("replace_content") is not None
        assert imp_reg.get("task_done") is not None

        # Verify registry MUST NOT have write_file or task_done (Yapan notlandıramaz)
        assert ver_reg.get("write_file") is None
        assert ver_reg.get("replace_content") is None
        assert ver_reg.get("task_done") is None
        assert ver_reg.get("read_file") is not None
        assert ver_reg.get("run_command") is not None
