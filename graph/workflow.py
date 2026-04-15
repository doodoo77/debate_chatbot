from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from agents.executor import ExecuteAgent
from agents.memory import MemoryAgent
from agents.planner import PlannerAgent
from config import get_settings
from schemas.planner import PlannerOutput
from services.cache import SemanticRedisCache
from services.router import DynamicRouter
from services.telemetry import build_metric, now


class DebateState(TypedDict, total=False):
    messages: List[Dict[str, str]]
    topic: str
    memory_summary: str
    previous_phase: str
    dialogue_state: Dict[str, Any]
    routing: Dict[str, Any]
    raw_planner: Dict[str, Any]
    planner: Dict[str, Any]
    draft_response: str
    response: str
    latest_phase: str
    should_refresh_memory: bool
    cache_hit: Optional[Dict[str, Any]]
    used_cache: bool
    cache_scope: str
    search_context: str
    turn_trace: Dict[str, Any]


class DebateChatbotRuntime:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.router = DynamicRouter()
        self.planner = PlannerAgent()
        self.executor = ExecuteAgent()
        self.memory = MemoryAgent()
        self.cache = SemanticRedisCache()
        self.graph = self._build_graph()

    @staticmethod
    def default_dialogue_state() -> Dict[str, Any]:
        return {
            "turn_state": "awaiting_stance",
            "arguments_collected": 0,
            "phase1_intro_sent": False,
            "phase2_intro_sent": False,
            "phase1_round": 0,
            "phase2_round": 0,
            "student_stance": "unknown",
        }

    def _build_graph(self):
        graph = StateGraph(DebateState)
        graph.add_node("prepare_turn", self.prepare_turn)
        graph.add_node("cache_lookup", self.cache_lookup)
        graph.add_node("execute", self.execute)
        graph.add_node("memory_signal", self.memory_signal)

        graph.add_edge(START, "prepare_turn")
        graph.add_edge("prepare_turn", "cache_lookup")
        graph.add_conditional_edges(
            "cache_lookup",
            self.route_after_cache,
            {
                "execute": "execute",
                "memory_signal": "memory_signal",
            },
        )
        graph.add_edge("execute", "memory_signal")
        graph.add_edge("memory_signal", END)
        return graph.compile()

    @staticmethod
    def _last_user_text(messages: List[Dict[str, str]]) -> str:
        for message in reversed(messages):
            if message["role"] == "user":
                return message["content"]
        return ""

    @staticmethod
    def _plan_with_updates(plan: PlannerOutput, **updates: Any) -> PlannerOutput:
        return plan.model_copy(update=updates)

    @staticmethod
    def _build_cache_scope(plan: PlannerOutput, dialogue_state: Dict[str, Any]) -> str:
        payload = {
            "phase": plan.phase,
            "turn_state": dialogue_state.get("turn_state"),
            "arguments_collected": dialogue_state.get("arguments_collected"),
            "phase1_round": dialogue_state.get("phase1_round"),
            "phase2_round": dialogue_state.get("phase2_round"),
            "student_stance": plan.student_stance,
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)

    @staticmethod
    def _extend_trace(
        trace: Dict[str, Any],
        *,
        step_name: str | None = None,
        metric: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        next_trace = dict(trace)
        next_trace.setdefault("step_order", [])
        next_trace.setdefault("metrics", [])
        if step_name:
            next_trace["step_order"] = [*next_trace["step_order"], step_name]
        if metric:
            next_trace["metrics"] = [*next_trace["metrics"], metric]
        return next_trace

    def _normalize_plan(
        self,
        plan: PlannerOutput,
        dialogue_state: Optional[Dict[str, Any]],
    ) -> tuple[PlannerOutput, Dict[str, Any]]:
        current = self.default_dialogue_state()
        if dialogue_state:
            current.update(dialogue_state)
        next_state = dict(current)

        inferred_arguments = max(int(plan.completed_argument_count or 0), int(current.get("arguments_collected", 0)))
        next_state["student_stance"] = plan.student_stance

        turn_state = current.get("turn_state", "awaiting_stance")

        def ordinal(index: int) -> str:
            return {1: "첫 번째", 2: "두 번째", 3: "세 번째"}.get(index, f"{index}번째")

        def build_collect_target(index: int) -> str:
            label = ordinal(index)
            if plan.requires_specificity and plan.requires_example:
                return (
                    f"학생의 {label} 근거 방향을 짧게 인정한 뒤, "
                    "챗봇이 예시를 대신 설명하지 말고 학생이 직접 왜 그런지와 실제 사례를 말하도록 질문 1개를 한다. "
                    "마지막 문장은 반드시 질문형으로 끝낸다."
                )
            if plan.requires_specificity:
                return (
                    f"학생의 {label} 근거 방향을 짧게 인정한 뒤, "
                    "왜 그런지 학생이 직접 더 구체적으로 설명하도록 질문 1개를 한다. "
                    "챗봇이 이유를 대신 완성하지 말고 마지막 문장은 반드시 질문형으로 끝낸다."
                )
            if plan.requires_example:
                return (
                    f"학생의 {label} 근거 방향을 짧게 인정한 뒤, "
                    "챗봇이 예시를 대신 제시하지 말고 학생이 직접 실제 사례를 말하도록 질문 1개를 한다. "
                    "예를 들면 어떤 상황에서 그런지 학생에게 물어보고 마지막 문장은 반드시 질문형으로 끝낸다."
                )
            return (
                f"학생의 {label} 근거를 더 분명하게 말하도록 질문 1개를 한다. "
                "설명으로 끝내지 말고 마지막 문장은 반드시 질문형으로 끝낸다."
            )

        if turn_state == "awaiting_stance":
            if plan.student_stance == "unknown":
                return (
                    self._plan_with_updates(
                        plan,
                        phase="stance_selection",
                        completed_argument_count=0,
                        target_action="학생이 찬성인지 반대인지 한 문장으로 분명하게 정하도록 요청한다.",
                        transition_to_rebuttal=False,
                        should_end=False,
                    ),
                    next_state,
                )

            next_state.update({"turn_state": "awaiting_argument_1", "arguments_collected": 0})
            return (
                self._plan_with_updates(
                    plan,
                    phase="collect_argument_1",
                    completed_argument_count=0,
                    target_action="학생의 입장을 짧게 확인한 뒤, 그 입장을 지지하는 첫 번째 근거를 하나만 말해보게 한다.",
                    transition_to_rebuttal=False,
                    should_end=False,
                ),
                next_state,
            )

        if turn_state == "awaiting_argument_1":
            if inferred_arguments >= 1 and not plan.requires_specificity and not plan.requires_example:
                next_state.update({"turn_state": "awaiting_argument_2", "arguments_collected": 1})
                return (
                    self._plan_with_updates(
                        plan,
                        phase="collect_argument_2",
                        completed_argument_count=1,
                        target_action="첫 번째 근거를 짧게 인정하고, 두 번째 근거를 하나만 더 말해보게 한다.",
                        transition_to_rebuttal=False,
                        should_end=False,
                    ),
                    next_state,
                )

            next_state["arguments_collected"] = max(0, min(inferred_arguments, 1))
            return (
                self._plan_with_updates(
                    plan,
                    phase="collect_argument_1",
                    completed_argument_count=next_state["arguments_collected"],
                    target_action=build_collect_target(1),
                    transition_to_rebuttal=False,
                    should_end=False,
                ),
                next_state,
            )

        if turn_state == "awaiting_argument_2":
            if inferred_arguments >= 2 and not plan.requires_specificity and not plan.requires_example:
                next_state.update({"turn_state": "awaiting_argument_3", "arguments_collected": 2})
                return (
                    self._plan_with_updates(
                        plan,
                        phase="collect_argument_3",
                        completed_argument_count=2,
                        target_action="두 번째 근거를 짧게 인정하고, 세 번째 근거를 하나만 더 말해보게 한다.",
                        transition_to_rebuttal=False,
                        should_end=False,
                    ),
                    next_state,
                )

            next_state["arguments_collected"] = max(1, min(inferred_arguments, 2))
            return (
                self._plan_with_updates(
                    plan,
                    phase="collect_argument_2",
                    completed_argument_count=next_state["arguments_collected"],
                    target_action=build_collect_target(2),
                    transition_to_rebuttal=False,
                    should_end=False,
                ),
                next_state,
            )

        if turn_state == "awaiting_argument_3":
            if inferred_arguments >= 3 and not plan.requires_specificity and not plan.requires_example:
                next_state.update(
                    {
                        "turn_state": "phase1_wait_student_after_counter",
                        "arguments_collected": 3,
                        "phase1_intro_sent": True,
                        "phase1_round": 1,
                    }
                )
                return (
                    self._plan_with_updates(
                        plan,
                        phase="counter_argument_round_1",
                        completed_argument_count=3,
                        target_action=(
                            '정확히 "자, 이제 반대 입장의 주장에 대한 반론 연습을 해보자."라는 전환 문장을 이번 턴에 한 번만 포함하고, '
                            "학생과 반대 입장에서 새로운 근거 1개를 제시한 뒤 학생의 반론을 요청한다."
                        ),
                        transition_to_rebuttal=True,
                        should_end=False,
                    ),
                    next_state,
                )

            next_state["arguments_collected"] = max(2, min(inferred_arguments, 3))
            return (
                self._plan_with_updates(
                    plan,
                    phase="collect_argument_3",
                    completed_argument_count=next_state["arguments_collected"],
                    target_action=build_collect_target(3),
                    transition_to_rebuttal=False,
                    should_end=False,
                ),
                next_state,
            )

        if turn_state == "phase1_wait_student_after_counter":
            round_index = int(current.get("phase1_round", 1) or 1)
            next_state.update(
                {
                    "turn_state": "phase1_wait_student_after_recounter",
                    "arguments_collected": 3,
                    "phase1_round": round_index,
                }
            )
            return (
                self._plan_with_updates(
                    plan,
                    phase="counter_argument_round_2",
                    completed_argument_count=3,
                    target_action=(
                        f"반론 연습 1단계 {round_index}회차에서 학생 반론을 짧게 인정한 뒤, "
                        "챗봇의 재반론 1개를 제시하고 다시 학생의 답변을 요청한다."
                    ),
                    transition_to_rebuttal=False,
                    should_end=False,
                ),
                next_state,
            )

        if turn_state == "phase1_wait_student_after_recounter":
            round_index = int(current.get("phase1_round", 1) or 1)
            if round_index < 3:
                next_round = round_index + 1
                next_state.update(
                    {
                        "turn_state": "phase1_wait_student_after_counter",
                        "arguments_collected": 3,
                        "phase1_round": next_round,
                    }
                )
                return (
                    self._plan_with_updates(
                        plan,
                        phase="counter_argument_round_1",
                        completed_argument_count=3,
                        target_action=(
                            f"반론 연습 1단계 {next_round}회차로 넘어간다. "
                            "이전 회차를 길게 반복하지 말고 학생과 반대 입장에서 새로운 근거 1개를 제시한 뒤 학생의 반론을 요청한다."
                        ),
                        transition_to_rebuttal=False,
                        should_end=False,
                    ),
                    next_state,
                )

            next_state.update(
                {
                    "turn_state": "phase2_wait_student_after_counter",
                    "arguments_collected": 3,
                    "phase2_intro_sent": True,
                    "phase2_round": 1,
                }
            )
            return (
                self._plan_with_updates(
                    plan,
                    phase="student_argument_round_1",
                    completed_argument_count=3,
                    target_action=(
                        '정확히 "이제 네가 준비한 근거를 바탕으로 반론 및 재반론 연습을 해보자."라는 전환 문장을 이번 턴에 한 번만 포함하고, '
                        "학생의 첫 번째 근거를 먼저 짚은 뒤 그 근거에 대한 반론 1개를 제시하고 학생의 재반론을 요청한다."
                    ),
                    transition_to_rebuttal=True,
                    should_end=False,
                ),
                next_state,
            )

        if turn_state == "phase2_wait_student_after_counter":
            round_index = int(current.get("phase2_round", 1) or 1)
            next_state.update(
                {
                    "turn_state": "phase2_wait_student_after_recounter",
                    "arguments_collected": 3,
                    "phase2_round": round_index,
                }
            )
            return (
                self._plan_with_updates(
                    plan,
                    phase="student_argument_round_2",
                    completed_argument_count=3,
                    target_action=(
                        f"학생의 {ordinal(round_index)} 근거에 대한 학생 재반론을 짧게 인정한 뒤, "
                        "챗봇의 재반론 1개를 제시하고 다시 학생의 답변을 요청한다."
                    ),
                    transition_to_rebuttal=False,
                    should_end=False,
                ),
                next_state,
            )

        if turn_state == "phase2_wait_student_after_recounter":
            round_index = int(current.get("phase2_round", 1) or 1)
            if round_index < 3:
                next_round = round_index + 1
                next_state.update(
                    {
                        "turn_state": "phase2_wait_student_after_counter",
                        "arguments_collected": 3,
                        "phase2_round": next_round,
                    }
                )
                return (
                    self._plan_with_updates(
                        plan,
                        phase="student_argument_round_1",
                        completed_argument_count=3,
                        target_action=(
                            f"이제 학생의 {ordinal(next_round)} 근거에 대한 새로운 반론을 시작한다는 점이 분명히 드러나도록, "
                            "그 근거를 먼저 짚고 반론 1개를 제시한 뒤 학생의 재반론을 요청한다."
                        ),
                        transition_to_rebuttal=False,
                        should_end=False,
                    ),
                    next_state,
                )

            next_state.update(
                {
                    "turn_state": "completed",
                    "arguments_collected": 3,
                    "phase2_round": 3,
                }
            )
            return (
                self._plan_with_updates(
                    plan,
                    phase="closing",
                    completed_argument_count=3,
                    target_action="학생의 마지막 재반론을 짧게 정리하고, 전체 흐름 한 줄 요약과 잘한 점 1개, 보완점 1개를 말하며 이번 연습을 마무리한다.",
                    transition_to_rebuttal=False,
                    should_end=True,
                ),
                next_state,
            )

        return (
            self._plan_with_updates(
                plan,
                phase="closing",
                completed_argument_count=max(3, inferred_arguments),
                should_end=True,
            ),
            next_state,
        )

    @staticmethod
    def _should_generate_draft(plan: PlannerOutput) -> bool:
        return not plan.need_external_grounding

    def prepare_turn(self, state: DebateState) -> DebateState:
        messages = state["messages"]
        topic = state["topic"]
        memory_summary = state.get("memory_summary", "")
        previous_phase = state.get("previous_phase", "")
        dialogue_state = state.get("dialogue_state") or self.default_dialogue_state()

        user_text = self._last_user_text(messages)
        routing = self.router.route(user_text=user_text, conversation_turns=len(messages))

        planner_started = now()
        raw_plan, planner_response_metadata = self.planner.plan(
            messages,
            topic,
            memory_summary,
            previous_phase,
            dialogue_state,
        )
        planner_metric = build_metric(
            step="planner",
            started_at=planner_started,
            model_name=self.planner.settings.planner_model,
            input_payload={
                "topic": topic,
                "previous_phase": previous_phase,
                "dialogue_state": dialogue_state,
                "memory_summary": memory_summary,
                "messages": messages[-14:],
            },
            output_payload=raw_plan.model_dump(),
            response_metadata=planner_response_metadata,
        )

        normalized_plan, next_dialogue_state = self._normalize_plan(raw_plan, dialogue_state)
        turn_trace: Dict[str, Any] = {
            "step_order": ["planner"],
            "metrics": [planner_metric],
            "planner": {
                "raw": raw_plan.model_dump(),
                "normalized": normalized_plan.model_dump(),
                "metric": planner_metric,
            },
            "initial_response": {
                "status": "pending_until_cache_miss",
                "text": "",
                "used_as_candidate": False,
                "source": routing.model_name,
                "metric": None,
                "compatibility": {},
                "compatibility_metric": None,
            },
            "cache": {"status": "pending"},
            "external_documents": {"query": "", "results": "", "metric": None},
            "executor": {"initial_candidate": "", "final_response": "", "source": "", "metrics": []},
            "grader": [],
            "rewrite": [],
            "memory": {
                "existing_summary": memory_summary,
                "should_refresh_memory": False,
                "summary_ready": False,
                "summary_metric": None,
            },
            "final_response": "",
        }

        cache_scope = self._build_cache_scope(normalized_plan, next_dialogue_state)
        return {
            "routing": routing.to_dict(),
            "raw_planner": raw_plan.model_dump(),
            "planner": normalized_plan.model_dump(),
            "latest_phase": normalized_plan.phase,
            "dialogue_state": next_dialogue_state,
            "cache_scope": cache_scope,
            "turn_trace": turn_trace,
        }

    def cache_lookup(self, state: DebateState) -> DebateState:
        trace = dict(state.get("turn_trace", {}))

        if not self.settings.enable_cache:
            cache_metric = build_metric(
                step="cache_lookup",
                started_at=now(),
                model_name="-",
                input_payload="cache_disabled",
                output_payload={"hit": False, "reason": "disabled"},
                status="disabled",
            )
            trace = self._extend_trace(trace, step_name="cache_lookup(disabled)", metric=cache_metric)
            trace["cache"] = {
                "status": "disabled",
                "similarity": None,
                "response": "",
                "metric": cache_metric,
            }
            return {
                "cache_hit": None,
                "used_cache": False,
                "turn_trace": trace,
            }

        user_text = self._last_user_text(state["messages"])
        planner = PlannerOutput(**state["planner"])

        cache_started = now()
        hit = self.cache.lookup(
            user_text=user_text,
            phase=planner.phase,
            topic=state["topic"],
            scope=state.get("cache_scope", ""),
        )
        cache_metric = build_metric(
            step="cache_lookup",
            started_at=cache_started,
            model_name=self.cache.settings.embedding_model,
            input_payload=user_text,
            output_payload={"hit": hit is not None, "phase": planner.phase},
            status="hit" if hit else "miss",
        )

        trace = self._extend_trace(trace, step_name=f"cache_lookup({'hit' if hit else 'miss'})", metric=cache_metric)
        trace["cache"] = {
            "status": "hit" if hit else "miss",
            "similarity": hit.similarity if hit else None,
            "response": hit.response if hit else "",
            "metric": cache_metric,
        }

        if hit is None:
            return {"cache_hit": None, "used_cache": False, "turn_trace": trace}

        trace["initial_response"]["status"] = "skipped_cache_hit"
        trace["final_response"] = hit.response
        trace["executor"] = {
            "initial_candidate": "",
            "final_response": hit.response,
            "source": "cache",
            "metrics": [],
        }
        return {
            "response": hit.response,
            "cache_hit": hit.to_dict(),
            "used_cache": True,
            "search_context": hit.metadata.get("metadata", {}).get("search_context", ""),
            "turn_trace": trace,
        }

    @staticmethod
    def route_after_cache(state: DebateState) -> str:
        if state.get("response"):
            return "memory_signal"
        return "execute"

    def execute(self, state: DebateState) -> DebateState:
        planner_dict = state["planner"]
        typed_plan = PlannerOutput(**planner_dict)
        user_text = self._last_user_text(state["messages"])
        trace = dict(state.get("turn_trace", {}))

        accepted_draft = ""
        initial_trace = dict(trace.get("initial_response", {}))
        if self._should_generate_draft(typed_plan):
            draft_started = now()
            draft_bundle = self.executor.generate_draft(
                messages=state["messages"],
                topic=state["topic"],
                memory_summary=state.get("memory_summary", ""),
                previous_phase=state.get("previous_phase", ""),
                dialogue_state=state.get("dialogue_state") or self.default_dialogue_state(),
                model_name=state["routing"]["model_name"],
            )
            draft_text = draft_bundle.get("text", "")
            initial_metric = build_metric(
                step="initial_response",
                started_at=draft_started,
                model_name=state["routing"]["model_name"],
                input_payload={
                    "topic": state["topic"],
                    "previous_phase": state.get("previous_phase", ""),
                    "dialogue_state": state.get("dialogue_state") or {},
                    "memory_summary": state.get("memory_summary", ""),
                    "messages": state["messages"][-14:],
                },
                output_payload=draft_text,
                response_metadata=draft_bundle.get("response_metadata"),
            )
            trace = self._extend_trace(trace, step_name="initial_response", metric=initial_metric)
            initial_trace.update(
                {
                    "status": "generated",
                    "text": draft_text,
                    "metric": initial_metric,
                    "source": state["routing"]["model_name"],
                }
            )

            if self.executor.should_assess_draft_compatibility(typed_plan):
                compatibility_started = now()
                compatibility_bundle = self.executor.assess_draft_compatibility(draft_text, typed_plan, state["topic"])
                compatibility = compatibility_bundle.get("result", {})
                compatibility_metric = build_metric(
                    step="draft_compatibility",
                    started_at=compatibility_started,
                    model_name=self.executor.settings.verifier_model,
                    input_payload={
                        "topic": state["topic"],
                        "phase": typed_plan.phase,
                        "target_action": typed_plan.target_action,
                        "draft": draft_text,
                    },
                    output_payload=compatibility,
                    response_metadata=compatibility_bundle.get("response_metadata"),
                    status="accepted" if compatibility.get("compatible") else "rejected",
                )
                trace = self._extend_trace(trace, step_name="draft_compatibility", metric=compatibility_metric)
                initial_trace.update(
                    {
                        "compatibility": compatibility,
                        "compatibility_metric": compatibility_metric,
                    }
                )
                accepted_draft = draft_text if compatibility.get("compatible") else ""
            else:
                accepted_draft = draft_text.strip()
                initial_trace.update(
                    {
                        "compatibility": {"compatible": True, "reason": "단순 단계라 compatibility 검사를 생략함."},
                        "compatibility_metric": None,
                        "status": "compatibility_skipped",
                    }
                )
        else:
            initial_trace.update(
                {
                    "status": "skipped_external_grounding",
                    "text": "",
                    "metric": None,
                    "compatibility": {
                        "compatible": False,
                        "reason": "외부 근거가 필요한 턴은 executor tool call에서만 검색합니다.",
                    },
                    "compatibility_metric": None,
                }
            )

        initial_trace["used_as_candidate"] = bool(accepted_draft)
        trace["initial_response"] = initial_trace

        response, execution_trace = self.executor.generate_with_verification(
            plan=typed_plan,
            messages=state["messages"],
            topic=state["topic"],
            memory_summary=state.get("memory_summary", ""),
            previous_phase=state.get("previous_phase", ""),
            dialogue_state=state.get("dialogue_state") or self.default_dialogue_state(),
            search_context="",
            model_name=state["routing"]["model_name"],
            draft_response=accepted_draft,
        )

        search_trace = execution_trace.get("search_trace") or {}
        if search_trace.get("used"):
            search_metric = search_trace.get("metric")
            if search_metric:
                trace = self._extend_trace(trace, step_name="external_documents", metric=search_metric)
            trace["external_documents"] = {
                "query": " | ".join(search_trace.get("queries", [])),
                "results": search_trace.get("results", ""),
                "metric": search_metric,
            }
        else:
            trace["external_documents"] = {"query": "", "results": "", "metric": None}

        execution_metrics = execution_trace.get("metrics", [])
        for metric in execution_metrics:
            step = metric.get("step")
            if step == "external_documents":
                continue
            trace = self._extend_trace(trace, metric=metric)

        if execution_trace.get("initial_candidate_source") in {"executor", "draft"}:
            trace = self._extend_trace(trace, step_name="executor")
        if execution_trace.get("grader_steps"):
            trace = self._extend_trace(trace, step_name="grader")
        if execution_trace.get("rewrite_steps"):
            trace = self._extend_trace(trace, step_name="rewrite")
        trace = self._extend_trace(trace, step_name="final")

        trace["executor"] = {
            "initial_candidate": execution_trace.get("initial_candidate", ""),
            "final_response": execution_trace.get("final_response", response),
            "source": execution_trace.get("initial_candidate_source", ""),
            "metrics": execution_metrics,
        }
        trace["grader"] = execution_trace.get("grader_steps", [])
        trace["rewrite"] = execution_trace.get("rewrite_steps", [])
        trace["final_response"] = execution_trace.get("final_response", response)

        search_context = search_trace.get("results", "")

        if self.settings.enable_cache:
            self.cache.store(
                user_text=user_text,
                phase=typed_plan.phase,
                topic=state["topic"],
                scope=state.get("cache_scope", ""),
                response=response,
                metadata={
                    "routing": state["routing"],
                    "search_context": search_context,
                    "trace": trace,
                },
            )

        return {
            "response": response,
            "search_context": search_context,
            "used_cache": False,
            "turn_trace": trace,
        }

    def memory_signal(self, state: DebateState) -> DebateState:
        trace = dict(state.get("turn_trace", {}))
        memory_started = now()
        should_refresh = self.memory.should_refresh_summary(
            messages=state["messages"],
            previous_phase=state.get("previous_phase", ""),
            current_phase=state.get("latest_phase", ""),
            existing_summary=state.get("memory_summary", ""),
        )
        memory_metric = build_metric(
            step="memory_signal",
            started_at=memory_started,
            model_name="-",
            input_payload={
                "previous_phase": state.get("previous_phase", ""),
                "current_phase": state.get("latest_phase", ""),
                "message_count": len(state.get("messages", [])),
            },
            output_payload={"should_refresh": should_refresh},
            status="scheduled" if should_refresh else "skipped",
        )
        trace = self._extend_trace(trace, step_name="memory", metric=memory_metric)

        memory_trace = dict(trace.get("memory", {}))
        memory_trace.update(
            {
                "existing_summary": state.get("memory_summary", ""),
                "should_refresh_memory": should_refresh,
                "summary_ready": False,
                "decision_metric": memory_metric,
            }
        )
        trace["memory"] = memory_trace
        return {"should_refresh_memory": should_refresh, "turn_trace": trace}