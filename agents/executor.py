from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.tools import TavilySearchResults

from config import get_settings
from prompts import DRAFT_PROMPT, EXECUTOR_PROMPT, VERIFIER_PROMPT
from schemas.planner import CompatibilityResult, PlannerOutput, VerificationResult
from services.llm import get_chat_model
from services.similarity import semantic_similarity
from services.telemetry import build_metric, now


class ExecuteAgent:
    def __init__(self) -> None:
        self.settings = get_settings()

    @staticmethod
    def _serialize_messages(messages: List[Dict[str, str]]) -> str:
        lines = []
        for msg in messages[-14:]:
            role = "학생" if msg["role"] == "user" else "챗봇"
            lines.append(f"{role}: {msg['content']}")
        return "\n".join(lines)

    @staticmethod
    def _text_from_response(response: Any) -> str:
        content = getattr(response, "content", response)
        return content if isinstance(content, str) else str(content)

    @staticmethod
    def _metadata_from_response(response: Any) -> Optional[Dict[str, Any]]:
        metadata = getattr(response, "response_metadata", None)
        return metadata if isinstance(metadata, dict) else None

    @staticmethod
    def _structured_invoke_with_metadata(
        model_name: str,
        temperature: float,
        schema: Any,
        messages,
    ) -> Tuple[Any, Optional[Dict[str, Any]]]:
        base_model = get_chat_model(model_name, temperature=temperature)
        try:
            structured_model = base_model.with_structured_output(schema, include_raw=True)
            result = structured_model.invoke(messages)
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

        structured_model = base_model.with_structured_output(schema)
        parsed = structured_model.invoke(messages)
        return parsed, None

    def generate_draft(
        self,
        messages: List[Dict[str, str]],
        topic: str,
        memory_summary: str,
        previous_phase: str,
        dialogue_state: Dict[str, Any],
        model_name: str,
    ) -> Dict[str, Any]:
        prompt = ChatPromptTemplate.from_messages([("system", DRAFT_PROMPT)])
        model = get_chat_model(model_name, temperature=0.4)
        prompt_messages = prompt.format_messages(
            topic=topic,
            previous_phase=previous_phase or "없음",
            dialogue_state=dialogue_state or {},
            memory_summary=memory_summary or "요약 없음",
            conversation=self._serialize_messages(messages),
        )
        response = model.invoke(prompt_messages)
        return {
            "text": self._text_from_response(response),
            "response_metadata": self._metadata_from_response(response),
        }

    def assess_draft_compatibility(
        self,
        draft: str,
        plan: PlannerOutput,
        topic: str,
    ) -> Dict[str, Any]:
        if not draft.strip():
            return {
                "result": {"compatible": False, "reason": "생성된 초기 응답이 없습니다."},
                "response_metadata": None,
            }

        payload = {
            "topic": topic,
            "phase": plan.phase,
            "target_action": plan.target_action,
            "draft": draft,
        }
        parsed, metadata = self._structured_invoke_with_metadata(
            self.settings.verifier_model,
            0.0,
            CompatibilityResult,
            [
                SystemMessage(
                    content=(
                        "너는 Planner 판단과 초안의 정합성을 검사한다. "
                        "초안이 현재 단계에 맞고 target_action을 크게 벗어나지 않으면 compatible=true로 답하라."
                    )
                ),
                HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
            ],
        )
        return {"result": parsed.model_dump(), "response_metadata": metadata}

    @staticmethod
    def should_assess_draft_compatibility(plan: PlannerOutput) -> bool:
        return plan.phase in {
            "counter_argument_round_1",
            "counter_argument_round_2",
            "student_argument_round_1",
            "student_argument_round_2",
            "student_rebuttal_round",
            "closing",
        }

    @staticmethod
    def _strip_emphasis(text: str) -> str:
        cleaned = text
        for token in ("**", "__", "*", "_", "`", "~~"):
            cleaned = cleaned.replace(token, "")
        return cleaned

    def _normalize_transition_phrase(self, candidate: str, plan: PlannerOutput) -> str:
        phase1_phrase = "자, 이제 반대 입장의 주장에 대한 반론 연습을 해보자."
        phase2_phrase = "이제 네가 준비한 근거를 바탕으로 반론 및 재반론 연습을 해보자."
        normalized = candidate.strip()

        active_intro = None
        if plan.transition_to_rebuttal and plan.phase == "counter_argument_round_1":
            active_intro = phase1_phrase
        elif plan.transition_to_rebuttal and plan.phase == "student_argument_round_1":
            active_intro = phase2_phrase
        else:
            return normalized

        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", normalized) if part.strip()]
        kept: List[str] = []
        for paragraph in paragraphs:
            plain = self._strip_emphasis(paragraph)
            if phase1_phrase in plain or phase2_phrase in plain:
                continue
            kept.append(paragraph)

        body = "\n\n".join(kept).strip()
        if body:
            return f"{active_intro}\n\n{body}"
        return active_intro

    @staticmethod
    def _format_search_results(results: Any) -> str:
        if not results:
            return "외부 검색 결과 없음"
        if isinstance(results, str):
            return results
        if not isinstance(results, list):
            return json.dumps(results, ensure_ascii=False)

        lines: List[str] = []
        for idx, item in enumerate(results, start=1):
            if not isinstance(item, dict):
                lines.append(f"[{idx}] {item}")
                continue
            title = item.get("title") or item.get("url") or f"result-{idx}"
            content = item.get("content", "")
            url = item.get("url", "")
            lines.append(f"[{idx}] {title}\n- 요약: {content}\n- 출처: {url}")
        return "\n\n".join(lines)

    def _tool_call_generation(
        self,
        model_name: str,
        prompt_messages,
        allow_tools: bool,
    ) -> Dict[str, Any]:
        if not allow_tools or not self.settings.tavily_api_key:
            model = get_chat_model(model_name, temperature=0.4)
            response = model.invoke(prompt_messages)
            return {
                "text": self._text_from_response(response),
                "response_metadatas": [self._metadata_from_response(response)],
                "llm_call_count": 1,
                "tool_calls": 0,
                "search_trace": {
                    "used": False,
                    "queries": [],
                    "results": "",
                    "metric": None,
                },
            }

        tool = TavilySearchResults(max_results=3)
        model = get_chat_model(model_name, temperature=0.4).bind_tools([tool])
        first_response = model.invoke(prompt_messages)
        metadata_list: List[Optional[Dict[str, Any]]] = [self._metadata_from_response(first_response)]

        if not getattr(first_response, "tool_calls", None):
            return {
                "text": self._text_from_response(first_response),
                "response_metadatas": metadata_list,
                "llm_call_count": 1,
                "tool_calls": 0,
                "search_trace": {
                    "used": False,
                    "queries": [],
                    "results": "",
                    "metric": None,
                },
            }

        search_started = now()
        queries: List[str] = []
        formatted_results: List[str] = []
        tool_messages = []
        for call in first_response.tool_calls:
            try:
                args = call.get("args", {})
                query = args.get("query") if isinstance(args, dict) else args
                query_text = str(query or "")
                queries.append(query_text)
                tool_result = tool.invoke(query)
            except Exception as exc:
                tool_result = f"search_error: {exc}"
                if not queries:
                    queries.append("")
            formatted_results.append(self._format_search_results(tool_result))
            tool_messages.append(
                ToolMessage(content=json.dumps(tool_result, ensure_ascii=False), tool_call_id=call["id"])
            )

        search_context = "\n\n".join(part for part in formatted_results if part).strip()
        search_metric = build_metric(
            step="external_documents",
            started_at=search_started,
            model_name="-",
            input_payload=queries,
            output_payload=search_context,
            status="used",
            extra={"tool_calls": len(tool_messages)},
        )

        final_response = model.invoke([*prompt_messages, first_response, *tool_messages])
        metadata_list.append(self._metadata_from_response(final_response))
        return {
            "text": self._text_from_response(final_response),
            "response_metadatas": metadata_list,
            "llm_call_count": 2,
            "tool_calls": len(tool_messages),
            "search_trace": {
                "used": True,
                "queries": queries,
                "results": search_context,
                "metric": search_metric,
            },
        }

    def verify(self, candidate: str, plan: PlannerOutput, search_context: str) -> Tuple[VerificationResult, Optional[Dict[str, Any]]]:
        prompt = ChatPromptTemplate.from_messages([("system", VERIFIER_PROMPT)])
        prompt_messages = prompt.format_messages(
            plan=plan.model_dump_json(indent=2),
            search_context=search_context or "없음",
            candidate=candidate,
        )
        return self._structured_invoke_with_metadata(
            self.settings.verifier_model,
            0.0,
            VerificationResult,
            prompt_messages,
        )

    def generate_with_verification(
        self,
        plan: PlannerOutput,
        messages: List[Dict[str, str]],
        topic: str,
        memory_summary: str,
        previous_phase: str,
        dialogue_state: Dict[str, Any],
        search_context: str,
        model_name: str,
        draft_response: str = "",
    ) -> Tuple[str, Dict[str, object]]:
        prompt = ChatPromptTemplate.from_messages([("system", EXECUTOR_PROMPT)])
        model_messages = prompt.format_messages(
            topic=topic,
            plan=plan.model_dump_json(indent=2),
            previous_phase=previous_phase or "없음",
            dialogue_state=dialogue_state or {},
            memory_summary=memory_summary or "요약 없음",
            conversation=self._serialize_messages(messages),
            search_context=search_context or "없음",
        )

        trace: Dict[str, object] = {
            "initial_candidate": "",
            "initial_candidate_source": "",
            "final_response": "",
            "grader_steps": [],
            "rewrite_steps": [],
            "metrics": [],
            "search_trace": {
                "used": False,
                "queries": [],
                "results": search_context or "",
                "metric": None,
            },
        }

        current_search_context = search_context or ""
        previous_candidate = draft_response.strip() if draft_response else ""
        if previous_candidate:
            candidate = self._normalize_transition_phrase(previous_candidate, plan)
            trace["initial_candidate_source"] = "draft"
        else:
            generate_started = now()
            generation = self._tool_call_generation(
                model_name=model_name,
                prompt_messages=model_messages,
                allow_tools=plan.need_external_grounding,
            )
            candidate = self._normalize_transition_phrase(generation["text"], plan)
            trace["initial_candidate_source"] = "executor"
            search_trace = generation.get("search_trace") or {}
            if search_trace.get("used"):
                current_search_context = search_trace.get("results", "") or current_search_context
                trace["search_trace"] = search_trace
                search_metric = search_trace.get("metric")
                if search_metric:
                    trace_metrics = list(trace.get("metrics", []))
                    trace_metrics.append(search_metric)
                    trace["metrics"] = trace_metrics
            trace_metrics = list(trace.get("metrics", []))
            trace_metrics.append(
                build_metric(
                    step="executor",
                    started_at=generate_started,
                    model_name=model_name,
                    input_payload=model_messages,
                    output_payload=candidate,
                    response_metadata=generation.get("response_metadatas"),
                    extra={
                        "llm_call_count": generation.get("llm_call_count", 1),
                        "tool_calls": generation.get("tool_calls", 0),
                    },
                )
            )
            trace["metrics"] = trace_metrics

        trace["initial_candidate"] = candidate

        for loop_index in range(self.settings.max_verification_loops):
            verify_started = now()
            verification, verification_metadata = self.verify(candidate, plan, current_search_context)
            grader_metric = build_metric(
                step=f"grader_{loop_index + 1}",
                started_at=verify_started,
                model_name=self.settings.verifier_model,
                input_payload={
                    "plan": plan.model_dump(),
                    "search_context": current_search_context,
                    "candidate": candidate,
                },
                output_payload=verification.model_dump(),
                response_metadata=verification_metadata,
            )

            grader_steps = list(trace.get("grader_steps", []))
            grader_steps.append(
                {
                    "candidate": candidate,
                    "verdict": verification.verdict,
                    "issues": verification.issues,
                    "revision_instruction": verification.revision_instruction,
                    "metric": grader_metric,
                }
            )
            trace["grader_steps"] = grader_steps

            trace_metrics = list(trace.get("metrics", []))
            trace_metrics.append(grader_metric)
            trace["metrics"] = trace_metrics

            if verification.verdict == "pass":
                trace["final_response"] = candidate
                return candidate, trace

            revised_instruction = verification.revision_instruction or verification.issues
            revision_prompt = [
                *model_messages,
                HumanMessage(content=f"이전 응답:\n{candidate}\n\n수정 지침:\n{revised_instruction}"),
            ]
            rewrite_started = now()
            revised_generation = self._tool_call_generation(
                model_name=model_name,
                prompt_messages=revision_prompt,
                allow_tools=False,
            )
            revised_candidate = self._normalize_transition_phrase(revised_generation["text"], plan)
            rewrite_metric = build_metric(
                step=f"rewrite_{loop_index + 1}",
                started_at=rewrite_started,
                model_name=model_name,
                input_payload=revision_prompt,
                output_payload=revised_candidate,
                response_metadata=revised_generation.get("response_metadatas"),
                extra={
                    "llm_call_count": revised_generation.get("llm_call_count", 1),
                    "tool_calls": revised_generation.get("tool_calls", 0),
                },
            )

            rewrite_steps = list(trace.get("rewrite_steps", []))
            rewrite_steps.append(
                {
                    "before": candidate,
                    "instruction": revised_instruction,
                    "after": revised_candidate,
                    "metric": rewrite_metric,
                }
            )
            trace["rewrite_steps"] = rewrite_steps

            trace_metrics = list(trace.get("metrics", []))
            trace_metrics.append(rewrite_metric)
            trace["metrics"] = trace_metrics

            if semantic_similarity(candidate, revised_candidate) >= self.settings.early_stop_similarity_threshold:
                trace["final_response"] = revised_candidate
                return revised_candidate, trace
            candidate = revised_candidate

        trace["final_response"] = candidate
        return candidate, trace
