"""
LoopGraph LLM Client Interface.
Provides unified OpenAI-compatible client access with token accounting and multiple provider support.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


@dataclass
class LLMResponse:
    content: Optional[str]
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    raw_message: Any = None
    tokens_used: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0


class LLMClient:
    def __init__(
        self,
        model: str = "glm-5.3-flash",
        base_url: str = "https://api.z.ai/api/paas/v4/",
        api_key: Optional[str] = None,
        api_key_env: str = "ZAI_API_KEY",
        temperature: float = 0.3,
        mock_handler: Optional[Callable[[List[Dict[str, Any]], Optional[List[Dict[str, Any]]]], LLMResponse]] = None,
    ):
        self.model = model
        self.base_url = base_url
        self.temperature = temperature
        self.mock_handler = mock_handler
        self.total_tokens_used = 0

        # Auto detect API key from environment if not explicitly provided
        key = api_key or os.environ.get(api_key_env)
        if not key:
            for env_name in ("ZAI_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY", "GROQ_API_KEY"):
                val = os.environ.get(env_name)
                if val:
                    key = val
                    if env_name == "OPENAI_API_KEY" and "z.ai" in base_url:
                        self.base_url = "https://api.openai.com/v1"
                        self.model = "gpt-4o"
                    elif env_name == "DEEPSEEK_API_KEY":
                        self.base_url = "https://api.deepseek.com"
                        self.model = "deepseek-chat"
                    break

        self.api_key = key
        self._client = None
        if OpenAI is not None and self.api_key and not self.mock_handler:
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    @property
    def is_configured(self) -> bool:
        return self.mock_handler is not None or (self._client is not None and bool(self.api_key))

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        model_override: Optional[str] = None,
        temperature_override: Optional[float] = None,
    ) -> LLMResponse:
        """Sends chat request to LLM and returns structured LLMResponse."""
        if self.mock_handler:
            resp = self.mock_handler(messages, tools)
            self.total_tokens_used += resp.tokens_used
            return resp

        if not self._client:
            raise RuntimeError(
                "LLM İstemcisi yapılandırılmamış. Lütfen geçerli bir API anahtarı sağlayın "
                "(örn: ZAI_API_KEY veya OPENAI_API_KEY)."
            )

        kwargs: Dict[str, Any] = {
            "model": model_override or self.model,
            "messages": messages,
            "temperature": (
                temperature_override
                if temperature_override is not None
                else self.temperature
            ),
        }
        if tools:
            kwargs["tools"] = tools

        resp = self._client.chat.completions.create(**kwargs)
        choice = resp.choices[0]
        msg = choice.message

        t_used = 0
        p_tokens = 0
        c_tokens = 0
        if resp.usage:
            t_used = getattr(resp.usage, "total_tokens", 0) or 0
            p_tokens = getattr(resp.usage, "prompt_tokens", 0) or 0
            c_tokens = getattr(resp.usage, "completion_tokens", 0) or 0
            self.total_tokens_used += t_used

        tool_calls = []
        if getattr(msg, "tool_calls", None):
            for tc in msg.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                })

        return LLMResponse(
            content=msg.content,
            tool_calls=tool_calls,
            raw_message=msg,
            tokens_used=t_used,
            prompt_tokens=p_tokens,
            completion_tokens=c_tokens,
        )
