"""
File manipulation tools for LoopGraph.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

from loopgraph.safety.guardrails import Guardrails
from loopgraph.tools.base import BaseTool, ToolResult


class ReadFileTool(BaseTool):
    name = "read_file"
    description = (
        "Belirtilen dosyanın içeriğini veya belirli satır aralığını okur. "
        "Dosya yolu proje köküne göre verilmelidir."
    )
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Okunacak dosyanın göreli veya tam yolu.",
            },
            "start_line": {
                "type": "integer",
                "description": "Opsiyonel: Başlangıç satır numarası (1 tabanlı).",
            },
            "end_line": {
                "type": "integer",
                "description": "Opsiyonel: Bitiş satır numarası (dahil, 1 tabanlı).",
            },
            "max_chars": {
                "type": "integer",
                "description": "Opsiyonel: Okunacak maksimum karakter sayısı (varsayılan: 8000).",
            },
        },
        "required": ["path"],
    }

    def __init__(self, guardrails: Guardrails, max_chars_limit: int = 12000):
        self.guardrails = guardrails
        self.max_chars_limit = max_chars_limit

    def execute(
        self,
        path: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        max_chars: Optional[int] = None,
        **kwargs,
    ) -> ToolResult:
        is_safe, resolved_path, err = self.guardrails.is_path_safe(path)
        if not is_safe:
            return ToolResult(output=f"HATA: {err}", success=False)

        if not resolved_path.is_file():
            return ToolResult(
                output=f"HATA: Dosya bulunamadı: '{path}'", success=False
            )

        try:
            content = resolved_path.read_text(encoding="utf-8", errors="replace")
            lines = content.splitlines(keepends=True)
            total_lines = len(lines)

            if start_line is not None or end_line is not None:
                s = max(1, start_line or 1) - 1
                e = min(total_lines, end_line or total_lines)
                selected_lines = lines[s:e]
                output = "".join(selected_lines)
                header = f"[{path} Satır {s+1}-{e} / Toplam {total_lines}]\n"
            else:
                output = content
                header = f"[{path} Toplam {total_lines} satır]\n"

            limit = min(max_chars or 8000, self.max_chars_limit)
            if len(output) > limit:
                output = output[:limit] + f"\n... [Karakter sınırı nedeniyle kesildi ({limit}/{len(content)})]"

            return ToolResult(output=header + output, success=True)
        except Exception as e:
            return ToolResult(output=f"HATA: Dosya okunamadı: {e}", success=False)


class WriteFileTool(BaseTool):
    name = "write_file"
    description = (
        "Belirtilen dosyayı YENİDEN oluşturur veya ÜZERİNE YAZAR. "
        "Ebeveyn dizinler otomatik oluşturulur. Mevcut bir dosyada küçük bir değişiklik yapacaksanız "
        "replace_content aracını tercih edin."
    )
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Yazılacak dosyanın proje içi yolu.",
            },
            "content": {
                "type": "string",
                "description": "Dosyaya yazılacak tam metin içeriği.",
            },
        },
        "required": ["path", "content"],
    }

    def __init__(self, guardrails: Guardrails):
        self.guardrails = guardrails

    def execute(self, path: str, content: str, **kwargs) -> ToolResult:
        is_safe, resolved_path, err = self.guardrails.is_path_safe(path)
        if not is_safe:
            return ToolResult(output=f"HATA: {err}", success=False)

        try:
            resolved_path.parent.mkdir(parents=True, exist_ok=True)
            resolved_path.write_text(content, encoding="utf-8")
            line_count = len(content.splitlines())
            return ToolResult(
                output=f"BAŞARILI: '{path}' dosyası yazıldı ({len(content)} karakter, {line_count} satır).",
                success=True,
            )
        except Exception as e:
            return ToolResult(output=f"HATA: Dosya yazılamadı: {e}", success=False)


class ReplaceContentTool(BaseTool):
    name = "replace_content"
    description = (
        "Bir dosya içindeki belirli bir metin bloğunu yenisiyle cerrahi olarak değiştirir. "
        "Tüm dosyayı baştan yazmak yerine sadece değişmesi gereken hedef bloğu değiştirmek için kullanılır."
    )
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Değişiklik yapılacak dosya yolu.",
            },
            "target_content": {
                "type": "string",
                "description": "Değiştirilecek mevcut metin bloğu (birebir eşleşmeli).",
            },
            "replacement_content": {
                "type": "string",
                "description": "Hedef bloğun yerine geçecek yeni metin bloğu.",
            },
            "allow_multiple": {
                "type": "boolean",
                "description": "Birden fazla eşleşme varsa hepsini değiştir (varsayılan: false).",
            },
        },
        "required": ["path", "target_content", "replacement_content"],
    }

    def __init__(self, guardrails: Guardrails):
        self.guardrails = guardrails

    def execute(
        self,
        path: str,
        target_content: str,
        replacement_content: str,
        allow_multiple: bool = False,
        **kwargs,
    ) -> ToolResult:
        is_safe, resolved_path, err = self.guardrails.is_path_safe(path)
        if not is_safe:
            return ToolResult(output=f"HATA: {err}", success=False)

        if not resolved_path.is_file():
            return ToolResult(
                output=f"HATA: Hedef dosya bulunamadı: '{path}'", success=False
            )

        try:
            content = resolved_path.read_text(encoding="utf-8", errors="replace")
            count = content.count(target_content)

            if count == 0:
                return ToolResult(
                    output=(
                        f"HATA: target_content metni '{path}' dosyasında bulunamadı. "
                        "Lütfen read_file veya view_file ile dosyanın güncel içeriğini kontrol edin."
                    ),
                    success=False,
                )

            if count > 1 and not allow_multiple:
                return ToolResult(
                    output=(
                        f"HATA: target_content metni dosyada {count} kez bulundu. "
                        "Belirsizliği önlemek için daha geniş bir bağlam içeren hedef blok verin "
                        "veya allow_multiple=True parametresi geçin."
                    ),
                    success=False,
                )

            if allow_multiple:
                new_content = content.replace(target_content, replacement_content)
            else:
                new_content = content.replace(target_content, replacement_content, 1)

            resolved_path.write_text(new_content, encoding="utf-8")
            return ToolResult(
                output=f"BAŞARILI: '{path}' dosyasındaki {count} adet eşleşme güncellendi.",
                success=True,
            )
        except Exception as e:
            return ToolResult(
                output=f"HATA: İçerik değiştirme başarısız oldu: {e}", success=False
            )


class ViewFileTool(BaseTool):
    name = "view_file"
    description = (
        "Dosyayı satır numaralarıyla birlikte görüntüler. "
        "Düzenleme yapmadan önce kesin satırları ve bağlamı görmek için idealdir."
    )
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Görüntülenecek dosya yolu."},
            "start_line": {"type": "integer", "description": "Başlangıç satırı (1 tabanlı)."},
            "end_line": {"type": "integer", "description": "Bitiş satırı (1 tabanlı)."},
        },
        "required": ["path"],
    }

    def __init__(self, guardrails: Guardrails, max_lines: int = 200):
        self.guardrails = guardrails
        self.max_lines = max_lines

    def execute(
        self,
        path: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        **kwargs,
    ) -> ToolResult:
        is_safe, resolved_path, err = self.guardrails.is_path_safe(path)
        if not is_safe:
            return ToolResult(output=f"HATA: {err}", success=False)

        if not resolved_path.is_file():
            return ToolResult(output=f"HATA: Dosya bulunamadı: '{path}'", success=False)

        try:
            lines = resolved_path.read_text(encoding="utf-8", errors="replace").splitlines()
            total = len(lines)
            s = max(1, start_line or 1)
            e = min(total, end_line or min(total, s + self.max_lines - 1))

            formatted = []
            for idx in range(s, e + 1):
                formatted.append(f"{idx:4d} | {lines[idx-1]}")

            header = f"=== {path} (Satır {s}-{e} / Toplam {total}) ===\n"
            return ToolResult(output=header + "\n".join(formatted), success=True)
        except Exception as e:
            return ToolResult(output=f"HATA: Dosya görüntülenemedi: {e}", success=False)
