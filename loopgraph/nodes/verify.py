"""
VerifyNode for LoopGraph.
Adversarial/Independent Verifier: 'Yapan notlandıramaz' (The maker cannot grade itself).
Executes in a clean context with read-only tools and tests every acceptance criterion.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from loopgraph.core.graph import BaseNode
from loopgraph.core.state import ProjectState, Task
from loopgraph.llm.client import LLMClient
from loopgraph.safety.guardrails import Guardrails
from loopgraph.tools.base import ToolRegistry


class VerifyNode(BaseNode):
    def __init__(
        self,
        llm: LLMClient,
        verify_tools: ToolRegistry,
        guardrails: Guardrails,
        max_iters: int = 8,
        verify_model: Optional[str] = None,
        name: str = "verify",
    ):
        super().__init__(name=name)
        self.llm = llm
        self.verify_tools = verify_tools
        self.guardrails = guardrails
        self.max_iters = max_iters
        self.verify_model = verify_model

    def run(self, state: ProjectState) -> Optional[str]:
        task = state.current_task
        if not task:
            return "NO_TASK"

        system_prompt = (
            "Sen bağımsız, tarafsız ve tavizsiz bir Yazılım Kalite Denetçisisin (Software Verifier).\n"
            "Görevin: Verilen görevin kabul kriterlerini, proje dosyalarını ve test araçlarını kullanarak "
            "sıfırdan ve titizlikle doğrulamaktır.\n\n"
            "DENETİM KURALLARI (Yapan Notlandıramaz İlkesi):\n"
            "1. Uygulayıcının iddiasına asla güvenme. Araçları kullanarak (run_command ile test/kod çalıştırma, read_file ile inceleme) kendin kanıtla.\n"
            "2. Sadece kabul kriterleri sağlandıysa ve testler başarılıysa PASS ver.\n"
            "3. Hata, eksiklik veya sözdizimi/çalışma sorunu varsa kesinlikle FAIL ver.\n"
            "4. Kararını yanıtının sonunda kesin bir formatla belirt:\n"
            "   'VERDICT: PASS'\n"
            "   veya\n"
            "   'VERDICT: FAIL — Gerekçe ve tespit edilen eksiklikler'"
        )

        user_prompt_lines = [
            f"# DENETLENECEK GÖREV [{task.id}]: {task.title}",
            f"**Gerekçe:** {task.why}",
            "\n# KABUL KRİTERLERİ (Rubrik):",
        ]
        for c in task.acceptance:
            user_prompt_lines.append(f"- {c}")

        user_prompt_lines.append(
            f"\n# Proje Kökü: {self.guardrails.project_path}\n"
            "Lütfen araçları kullanarak her kabul kriterini tek tek test et ve kesin hükmünü bildir."
        )

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "\n".join(user_prompt_lines)},
        ]

        tool_schemas = self.verify_tools.to_openai_schemas()
        passed = False
        feedback_notes = ""

        for iteration in range(1, self.max_iters + 1):
            resp = self.llm.chat(
                messages=messages,
                tools=tool_schemas,
                model_override=self.verify_model,
            )

            if resp.tool_calls:
                messages.append({
                    "role": "assistant",
                    "content": resp.content or "",
                    "tool_calls": resp.tool_calls,
                })

                for tc in resp.tool_calls:
                    fn_name = tc["function"]["name"]
                    args_raw = tc["function"]["arguments"]
                    tool_res = self.verify_tools.execute(fn_name, args_raw)

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": tool_res.output,
                    })
            else:
                text = resp.content or ""
                messages.append({"role": "assistant", "content": text})

                if re.search(r"VERDICT:\s*PASS", text, re.IGNORECASE):
                    passed = True
                    feedback_notes = text
                    break
                elif re.search(r"VERDICT:\s*FAIL", text, re.IGNORECASE):
                    passed = False
                    feedback_notes = text
                    break
                else:
                    messages.append({
                        "role": "user",
                        "content": "Lütfen incelemeni tamamlayıp kararını 'VERDICT: PASS' veya 'VERDICT: FAIL — gerekçe' şeklinde bildir.",
                    })

        state.metadata["last_verify_result"] = {
            "passed": passed,
            "feedback": feedback_notes or "Denetçi açık bir karar üretmedi (varsayılan FAIL).",
        }

        return "VERIFY_PASS" if passed else "VERIFY_FAIL"
