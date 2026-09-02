"""
LoopGraph Base Tool Architecture and Registry.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


@dataclass
class ToolResult:
    output: str
    is_terminal: bool = False  # If True, indicates the loop should finish (e.g. task_done)
    success: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.output


class BaseTool(ABC):
    name: str
    description: str
    parameters: Dict[str, Any]

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given keyword arguments."""
        pass

    def to_openai_schema(self) -> Dict[str, Any]:
        """Converts tool definition to OpenAI tool format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_tools(self) -> List[BaseTool]:
        return list(self._tools.values())

    def to_openai_schemas(self) -> List[Dict[str, Any]]:
        return [tool.to_openai_schema() for tool in self._tools.values()]

    def execute(self, name: str, args_json: Union[str, Dict[str, Any]]) -> ToolResult:
        tool = self.get(name)
        if not tool:
            return ToolResult(
                output=f"Hata: '{name}' adında bir araç bulunamadı.",
                is_terminal=False,
                success=False,
            )

        if isinstance(args_json, str):
            try:
                args = json.loads(args_json or "{}")
            except json.JSONDecodeError as e:
                return ToolResult(
                    output=f"Hata: Geçersiz JSON argümanı ({e}): {args_json}",
                    is_terminal=False,
                    success=False,
                )
        else:
            args = args_json or {}

        try:
            return tool.execute(**args)
        except Exception as e:
            return ToolResult(
                output=f"Araç çalıştırma hatası ({name}): {str(e)}",
                is_terminal=False,
                success=False,
            )
