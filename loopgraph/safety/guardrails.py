"""
LoopGraph Safety & Guardrails Module.
Provides sandbox path containment and command execution safety inspection.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List, Optional, Tuple, Union

DEFAULT_BLOCKED_PATTERNS: List[str] = [
    # Destructive directory / file removal
    r"\brm\s+(-\w*\s+)*-?[rf]{1,2}\b.*\s/[^\s]*",   # rm -rf /...
    r"\brd\s+/s",                                   # Windows cmd rd /s
    r"\bdel\s+/[sqf]",                              # Windows cmd del /s /q /f
    r"Remove-Item\b.*-(Recurse|Force)",             # PowerShell recursive/forced delete
    r"\brmdir\s+/s\b",
    r"\bcmd(\.exe)?\s+/c\s+del\b",                  # cmd /c del ... (single-file delete escape)

    # System modifications / destruction
    r"\bformat\s+[a-zA-Z]:",
    r"\bformat\s+",
    r"\bshutdown\b",
    r"\bmkfs\b",
    r"\bdd\s+if=",
    r">\s*/dev/sd[a-z]",
    r"\bmv\b\s+\S+\s+/dev/",
    r"\btaskkill\b",
    r"\breg\s+(add|delete)\b",
    r"\bchpasswd\b",
    r"\bnet\s+user\b",
    r"\bsudo\b",

    # Code execution bypassing / network piping / shell piping
    r"\b(curl|wget)\b.*\|\s*(ba)?sh",
    r"\|\s*(ba)?sh\b",
    r"\|\s*powershell(\.exe)?\b",
    r"\|\s*pwsh(\.exe)?\b",
    r"\bInvoke-Expression\b",
    r"\biwr\b.*\|\s*iex",
    r"powershell(\.exe)?\s+-[eE](ncodedCommand)?\s+",
    # Download-then-execute chained with &&, ; or || (not just piped)
    r"\b(curl|wget|certutil|bitsadmin|Invoke-WebRequest|iwr)\b[^&;|\n]*(&&|;|\|\|)\s*\S*(sh|bash|python|python3|node|powershell|pwsh|cmd)(\.exe)?\b",
    r"\bcertutil\b.*-urlcache",
    r"\bbitsadmin\b.*\/transfer",
    r"powershell(\.exe)?\s+-File\b",                # execute a downloaded/arbitrary .ps1 script
    # Remote-download exfiltration via curl/wget upload flags
    r"\bcurl\b.*(-F\b|--form\b|-T\b|--upload-file\b|--data-binary\s+@)",
    r"\bwget\b.*--post-(file|data)\b",
    # Arbitrary code execution via inline interpreter one-liners
    r"\bpython3?\s+-c\b.*(os\.system|subprocess\.|popen\(|exec\(|eval\()",
    r"\bnode\s+-e\b.*(child_process|require\(['\"]child_process['\"]\))",
    r"\b(perl|ruby)\s+-e\b.*(system\(|exec\(|`)",

    # Irreversible git mutations
    r"\bgit\s+push\b",
    r"\bgit\s+reset\s+--hard\b",
    r"\bgit\s+clean\s+-[fF]",
    r"\bgit\s+branch\s+-D\b",
]

DEFAULT_EXCLUDE_DIRS: List[str] = [
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    ".next",
    ".cache",
    ".loopgraph",
    ".pytest_cache",
    ".mypy_cache",
    ".tox",
]


class Guardrails:
    def __init__(
        self,
        project_path: Path,
        blocked_patterns: Optional[List[str]] = None,
        exclude_dirs: Optional[List[str]] = None,
    ):
        self.project_path = Path(project_path).resolve()
        self.blocked_patterns = (
            blocked_patterns if blocked_patterns is not None else DEFAULT_BLOCKED_PATTERNS
        )
        self.exclude_dirs = (
            exclude_dirs if exclude_dirs is not None else DEFAULT_EXCLUDE_DIRS
        )
        self.compiled_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.blocked_patterns
        ]

    def is_path_safe(self, path: Union[str, Path]) -> Tuple[bool, Path, Optional[str]]:
        """
        Validates that target path is within project root directory.
        Returns: (is_safe, resolved_path, error_message)
        """
        try:
            target = Path(path)
            if not target.is_absolute():
                target = (self.project_path / target).resolve()
            else:
                target = target.resolve()

            proj_str = str(self.project_path.resolve())
            target_str = str(target)

            # Robust cross-platform containment check
            # Handles Windows drive case differences (e.g., d:\ vs D:\)
            norm_proj = os.path.normcase(os.path.abspath(proj_str))
            norm_target = os.path.normcase(os.path.abspath(target_str))

            try:
                common = os.path.commonpath([norm_proj, norm_target])
                if common == norm_proj:
                    return True, target, None
                else:
                    return (
                        False,
                        target,
                        f"Güvenlik ihlali: '{path}' hedefi proje sınırları dışındadır ({self.project_path}).",
                    )
            except ValueError:
                # Different drives on Windows (e.g. C: vs D:)
                return (
                    False,
                    target,
                    f"Güvenlik ihlali: '{path}' hedefi farklı bir sürücüdedir ({self.project_path}).",
                )
        except Exception as e:
            return False, Path(path), f"Geçersiz yol formatı: {e}"

    def is_command_safe(self, command: str) -> Tuple[bool, Optional[str]]:
        """
        Inspects command string against precompiled blocked patterns.
        Returns: (is_safe, reason_if_blocked)
        """
        clean_cmd = command.strip()
        if not clean_cmd:
            return False, "Boş komut."

        for pattern_regex, raw_pattern in zip(self.compiled_patterns, self.blocked_patterns):
            if pattern_regex.search(clean_cmd):
                return (
                    False,
                    f"Engellendi (İnsan Kapısı): '{raw_pattern}' güvenlik kuralı ihlali tespit edildi.",
                )

        return True, None

    def is_dir_excluded(self, dir_name: str) -> bool:
        """Returns True if the directory should be excluded from scans."""
        return dir_name in self.exclude_dirs or dir_name.startswith(".git")
