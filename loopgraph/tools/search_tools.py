"""
Search and discovery tools for LoopGraph.
"""

from __future__ import annotations

import fnmatch
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from loopgraph.safety.guardrails import Guardrails
from loopgraph.tools.base import BaseTool, ToolResult


class GrepSearchTool(BaseTool):
    name = "grep_search"
    description = (
        "Proje dosyaları içinde bir kelime öbeği veya regex deseni arar. "
        "Eşleşen dosya adları, satır numaraları ve ilgili kod satırları listelenir."
    )
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Aranacak metin veya regex deseni.",
            },
            "path": {
                "type": "string",
                "description": "Opsiyonel: Aramanın daraltılacağı alt klasör veya dosya yolu.",
            },
            "is_regex": {
                "type": "boolean",
                "description": "Opsiyonel: Desenin regex olarak işlenmesi (varsayılan: false).",
            },
            "case_sensitive": {
                "type": "boolean",
                "description": "Opsiyonel: Büyük/küçük harf duyarlılığı (varsayılan: false).",
            },
            "max_matches": {
                "type": "integer",
                "description": "Opsiyonel: Döndürülecek maksimum eşleşme sayısı (varsayılan: 40).",
            },
        },
        "required": ["pattern"],
    }

    def __init__(self, guardrails: Guardrails):
        self.guardrails = guardrails

    def execute(
        self,
        pattern: str,
        path: Optional[str] = None,
        is_regex: bool = False,
        case_sensitive: bool = False,
        max_matches: int = 40,
        **kwargs,
    ) -> ToolResult:
        search_root = self.guardrails.project_path
        if path:
            is_safe, resolved, err = self.guardrails.is_path_safe(path)
            if not is_safe:
                return ToolResult(output=f"HATA: {err}", success=False)
            search_root = resolved

        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            regex = re.compile(pattern if is_regex else re.escape(pattern), flags)
        except re.error as e:
            return ToolResult(output=f"HATA: Geçersiz regex deseni: {e}", success=False)

        matches: List[str] = []
        count = 0

        for root, dirs, files in os.walk(search_root):
            # Prune excluded directories
            dirs[:] = [d for d in dirs if not self.guardrails.is_dir_excluded(d)]

            for fname in files:
                file_path = Path(root) / fname
                try:
                    if file_path.stat().st_size > 500_000:  # Skip files larger than 500KB
                        continue
                    content = file_path.read_text(encoding="utf-8", errors="replace")
                    rel_path = file_path.relative_to(self.guardrails.project_path).as_posix()

                    for idx, line in enumerate(content.splitlines(), start=1):
                        if regex.search(line):
                            matches.append(f"{rel_path}:{idx}: {line.strip()[:150]}")
                            count += 1
                            if count >= max_matches:
                                break
                    if count >= max_matches:
                        break
                except Exception:
                    continue
            if count >= max_matches:
                break

        if not matches:
            return ToolResult(
                output=f"'{pattern}' deseni için eşleşme bulunamadı.", success=True
            )

        header = f"=== '{pattern}' için {len(matches)} eşleşme bulundu ===\n"
        return ToolResult(output=header + "\n".join(matches), success=True)


class FindFilesTool(BaseTool):
    name = "find_files"
    description = (
        "Proje içinde dosya adına veya dosya uzantısına göre arama yapar (örn: '*.py', 'test_*', 'package.json')."
    )
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Dosya adı eşleşme kalıbı (örn: '*.ts', '*config*').",
            },
            "path": {
                "type": "string",
                "description": "Opsiyonel: Aramanın yapılacağı alt klasör yolu.",
            },
        },
        "required": ["pattern"],
    }

    def __init__(self, guardrails: Guardrails):
        self.guardrails = guardrails

    def execute(self, pattern: str, path: Optional[str] = None, **kwargs) -> ToolResult:
        search_root = self.guardrails.project_path
        if path:
            is_safe, resolved, err = self.guardrails.is_path_safe(path)
            if not is_safe:
                return ToolResult(output=f"HATA: {err}", success=False)
            search_root = resolved

        found: List[str] = []
        for root, dirs, files in os.walk(search_root):
            dirs[:] = [d for d in dirs if not self.guardrails.is_dir_excluded(d)]
            for fname in files:
                if fnmatch.fnmatch(fname.lower(), pattern.lower()):
                    full_p = Path(root) / fname
                    rel_p = full_p.relative_to(self.guardrails.project_path).as_posix()
                    found.append(rel_p)
                if len(found) >= 100:
                    break
            if len(found) >= 100:
                break

        if not found:
            return ToolResult(
                output=f"'{pattern}' kalıbına uyan dosya bulunamadı.", success=True
            )

        return ToolResult(
            output=f"Bulunan {len(found)} dosya:\n" + "\n".join(found),
            success=True,
        )


class ListDirTool(BaseTool):
    name = "list_dir"
    description = (
        "Belirtilen klasörün içeriğini listeler. Klasörler [DIR], dosyalar [FILE] ve boyutlarıyla gösterilir."
    )
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Listelenecek klasör yolu (varsayılan: proje kökü '.').",
            },
        },
    }

    def __init__(self, guardrails: Guardrails):
        self.guardrails = guardrails

    def execute(self, path: Optional[str] = None, **kwargs) -> ToolResult:
        target_path = path or "."
        is_safe, resolved, err = self.guardrails.is_path_safe(target_path)
        if not is_safe:
            return ToolResult(output=f"HATA: {err}", success=False)

        if not resolved.is_dir():
            return ToolResult(output=f"HATA: Klasör bulunamadı: '{target_path}'", success=False)

        entries = []
        try:
            for item in sorted(resolved.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                if self.guardrails.is_dir_excluded(item.name):
                    continue
                if item.is_dir():
                    entries.append(f"[DIR]  {item.name}/")
                else:
                    size = item.stat().st_size
                    entries.append(f"[FILE] {item.name:<30} ({size:,} B)")

            rel = resolved.relative_to(self.guardrails.project_path).as_posix() or "."
            header = f"=== Dizin: {rel} ({len(entries)} öğe) ===\n"
            return ToolResult(output=header + "\n".join(entries), success=True)
        except Exception as e:
            return ToolResult(output=f"HATA: Dizin listelenemedi: {e}", success=False)
