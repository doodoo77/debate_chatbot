from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from langchain_core.prompts import ChatPromptTemplate

from config import get_settings
from prompts import DEBATE_WORKFLOW, PLANNER_PROMPT
from schemas.planner import PlannerOutput
from services.llm import get_chat_model


class PlannerAgent:
    def __init__(self) -> None:
        self.settings = get_settings()

    @staticmethod
    def _serialize_messages(messages: List[Dict[str, str]]) -> str:
        lines = []
        for msg in messages[-14:]:
            role = "학생" if msg["role"] == "user" else "챗봇"
            lines.append(f"{role}: {msg['content']}")
        return "\n".join(lines)

    def _invoke_structured_with_metadata(
        self,
        *,
        prompt_messages,
    ) -> Tuple[PlannerOutput, Optional[Dict[str, Any]]]:
        base_model = get_chat_model(self.settings.planner_model, temperature=0.1)
        try:
            structured_model = base_model.with_structured_output(PlannerOutput, include_raw=True)
            result = structured_model.invoke(prompt_messages)
            if isinstance(result, dict):
                parsed = result.get("parsed")
                raw = result.get("raw")
                if parsed is not None:
                    metadata = getattr(raw, "response_metadata", None)
                    return parsed, metadata if isinstance(metadata, dict) else None
        except TypeError:
            pass
        except Exception:
            pass

        structured_model = base_model.with_structured_output(PlannerOutput)
        parsed = structured_model.invoke(prompt_messages)
        return parsed, None

    def plan(
        self,
        messages: List[Dict[str, str]],
        topic: str,
        memory_summary: str,
        previous_phase: str,
        dialogue_state: Dict[str, Any],
    ) -> Tuple[PlannerOutput, Optional[Dict[str, Any]]]:
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", PLANNER_PROMPT),
            ]
        )
        prompt_messages = prompt.format_messages(
            topic=topic,
            workflow=DEBATE_WORKFLOW,
            previous_phase=previous_phase or "없음",
            dialogue_state=dialogue_state or {},
            memory_summary=memory_summary or "요약 없음",
            conversation=self._serialize_messages(messages),
        )
        return self._invoke_structured_with_metadata(prompt_messages=prompt_messages)
