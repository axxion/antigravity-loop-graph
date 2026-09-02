"""
Execution tools for LoopGraph.
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Any, Dict, Optional

from loopgraph.safety.guardrails import Guardrails
from loopgraph.tools.base import BaseTool, ToolResult


class RunCommandTool(BaseTool):
    name = "run_command"
    description = (
        "Proje kök dizininde bir kabuk komutu çalıştırır (test, derleme, bağımlılık kontrolü, "
        "git diff, pytest vb.). Güvenlik sınırları dışındaki tehlikeli komutlar otomatik reddedilir."
    )
    parameters = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Çalıştırılacak kabuk komutu.",
            },
            "timeout": {
                "type": "integer",
                "description": "Opsiyonel: Komut zaman aşımı süresi saniye cinsinden (varsayılan: 120).",
            },
        },
        "required": ["command"],
    }

    def __init__(
        self,
        guardrails: Guardrails,
        default_timeout: int = 120,
        max_output_chars: int = 6000,
    ):
        self.guardrails = guardrails
        self.default_timeout = default_timeout
        self.max_output_chars = max_output_chars

    def execute(
        self, command: str, timeout: Optional[int] = None, **kwargs
    ) -> ToolResult:
        is_safe, reason = self.guardrails.is_command_safe(command)
        if not is_safe:
            return ToolResult(
                output=f"REDDEDİLDİ (İnsan Kapısı): {reason}",
                success=False,
                metadata={"blocked": True},
            )

        timeout_sec = timeout or self.default_timeout
        try:
            # Use appropriate shell
            proc = subprocess.run(
                command,
                shell=True,
                cwd=self.guardrails.project_path,
                capture_output=True,
                text=False,  # capture bytes to handle encoding robustly
                timeout=timeout_sec,
            )

            # Decode stdout and stderr with fallback
            def decode_bytes(b: bytes) -> str:
                if not b:
                    return ""
                for enc in ("utf-8", "cp1254", "cp1252", "latin-1"):
                    try:
                        return b.decode(enc)
                    except UnicodeDecodeError:
                        continue
                return b.decode("utf-8", errors="replace")

            stdout = decode_bytes(proc.stdout)
            stderr = decode_bytes(proc.stderr)

            output_lines = [f"[Çıkış Kodu: {proc.returncode}]"]
            if stdout.strip():
                output_lines.append("--- STDOUT ---")
                output_lines.append(stdout)
            if stderr.strip():
                output_lines.append("--- STDERR ---")
                output_lines.append(stderr)

            combined = "\n".join(output_lines)
            if len(combined) > self.max_output_chars:
                combined = (
                    combined[: self.max_output_chars]
                    + f"\n... [Çıktı {self.max_output_chars} karakter sınırında kesildi]"
                )

            return ToolResult(
                output=combined,
                success=(proc.returncode == 0),
                metadata={"returncode": proc.returncode},
            )

        except subprocess.TimeoutExpired:
            return ToolResult(
                output=f"HATA: Komut zaman aşımına uğradı ({timeout_sec} saniye).",
                success=False,
                metadata={"timeout": True},
            )
        except Exception as e:
            return ToolResult(
                output=f"HATA: Komut çalıştırılamadı: {e}",
                success=False,
            )
