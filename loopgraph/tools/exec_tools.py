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

    # Provider credentials this process may hold. They are for talking to the model
    # API and are never needed by a build or test command, so they are withheld from
    # anything the agent runs: an inherited key is readable by any command the model
    # chooses to execute (`env`, `printenv`, a postinstall script) and would be
    # exfiltrated along with the command's output.
    SENSITIVE_ENV_VARS = (
        "ZAI_API_KEY",
        "OPENAI_API_KEY",
        "DEEPSEEK_API_KEY",
        "GROQ_API_KEY",
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "AZURE_OPENAI_API_KEY",
        "MISTRAL_API_KEY",
        "TOGETHER_API_KEY",
        "OPENROUTER_API_KEY",
        "HF_TOKEN",
    )

    def _child_env(self) -> dict:
        """Environment for a child process: this process's env minus model credentials."""
        env = os.environ.copy()
        for name in self.SENSITIVE_ENV_VARS:
            env.pop(name, None)
        # Catch provider keys not listed above without dropping legitimate variables
        # such as SSH_AUTH_SOCK or npm_config_registry.
        for name in list(env):
            upper = name.upper()
            if upper.endswith(("_API_KEY", "_SECRET_KEY")) or upper.startswith("OPENAI_"):
                env.pop(name, None)
        return env

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
                env=self._child_env(),
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
