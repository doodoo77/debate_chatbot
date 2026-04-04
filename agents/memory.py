from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from langchain_core.prompts import ChatPromptTemplate

from config import get_settings
from prompts import SUMMARY_PROMPT
from services.llm import get_chat_model
from services.telemetry import build_metric, now


class MemoryAgent:
    _executor = ThreadPoolExecutor(max_workers=2)

    def __init__(self) -> None:
        self.settings = get_settings()

    @staticmethod
    def _serialize_messages(messages: List[Dict[str, str]]) -> str:
        lines = []
        for msg in messages[-24:]:
            role = "학생" if msg["role"] == "user" else "챗봇"
            lines.append(f"{role}: {msg['content']}")
        return "\n".join(lines)

    @staticmethod
    def _approx_tokens(messages: List[Dict[str, str]]) -> int:
        return sum(len(message["content"].split()) for message in messages)

    def should_refresh_summary(
        self,
        messages: List[Dict[str, str]],
        previous_phase: str,
        current_phase: str,
        existing_summary: str,
    ) -> bool:
        if self._approx_tokens(messages) >= self.settings.summary_token_threshold:
            return True

        if previous_phase and current_phase and previous_phase != current_phase:
            phase_family_changed = previous_phase.split("_")[0] != current_phase.split("_")[0]
            if phase_family_changed:
                return True

        if not existing_summary and len(messages) >= 8:
            return True

        return False

    def summarize(self, messages: List[Dict[str, str]], topic: str, previous_summary: str) -> Dict[str, Any]:
        prompt = ChatPromptTemplate.from_messages([("system", SUMMARY_PROMPT)])
        model = get_chat_model(self.settings.model_easy, temperature=0.1)
        prompt_messages = prompt.format_messages(
            topic=topic,
            previous_summary=previous_summary or "없음",
            conversation=self._serialize_messages(messages),
        )
        started_at = now()
        response = model.invoke(prompt_messages)
        summary_text = response.content if isinstance(response.content, str) else str(response.content)
        metric = build_metric(
            step="memory_summary",
            started_at=started_at,
            model_name=self.settings.model_easy,
            input_payload=prompt_messages,
            output_payload=summary_text,
            response_metadata=getattr(response, "response_metadata", None),
        )
        return {"summary": summary_text, "metric": metric}

    def schedule_summary(self, messages: List[Dict[str, str]], topic: str, previous_summary: str) -> Future:
        snapshot = list(messages)
        return self._executor.submit(self.summarize, snapshot, topic, previous_summary)

    @staticmethod
    def collect_ready_summary(future: Optional[Future]) -> Optional[Dict[str, Any]]:
        if future is None or not future.done():
            return None
        try:
            result = future.result()
            if isinstance(result, dict):
                return result
            return {"summary": str(result), "metric": None}
        except Exception:
            return None
