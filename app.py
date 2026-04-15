from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd
import streamlit as st

import re
import time


def _normalize_compact(text: str) -> str:
    return re.sub(r"\s+", "", (text or "").strip().lower())


EXTRA_SIGNAL_PATTERNS = [
    "이유", "왜냐", "근거", "예를들면", "예를 들면", "어떻게", "?", "생각", "반박", "재반론",
]

PRO_PATTERNS = [
    "찬성", "찬성이야", "나는찬성이야", "저는찬성이에요", "전찬성이야", "저는찬성",
]
CON_PATTERNS = [
    "반대", "반대야", "나는반대야", "저는반대예요", "전반대야", "저는반대",
]


def detect_stance_only_reply(text: str) -> str | None:
    compact = _normalize_compact(text)
    if not compact:
        return None
    has_pro = any(p in compact for p in PRO_PATTERNS)
    has_con = any(p in compact for p in CON_PATTERNS)
    has_extra = any(p.replace(" ", "") in compact for p in EXTRA_SIGNAL_PATTERNS)
    if has_pro and not has_con and not has_extra:
        return "pro"
    if has_con and not has_pro and not has_extra:
        return "con"
    return None


def build_stance_fast_response(stance: str) -> str:
    if stance == "pro":
        return "좋아, 그럼 찬성 입장에서 생각해보자. 먼저 첫 번째 근거를 말해볼래?"
    if stance == "con":
        return "좋아, 그럼 반대 입장에서 생각해보자. 먼저 첫 번째 근거를 말해볼래?"
    return "좋아, 먼저 찬성과 반대 중 네 입장을 분명하게 말해볼래?"


def apply_stance_fast_state(dialogue_state: Dict[str, Any], stance: str) -> Dict[str, Any]:
    next_state = dict(dialogue_state or {})
    next_state.update(
        {
            "student_stance": stance,
            "turn_state": "awaiting_argument_1",
            "arguments_collected": 0,
            "phase1_intro_sent": False,
            "phase2_intro_sent": False,
            "phase1_round": 0,
            "phase2_round": 0,
        }
    )
    return next_state


def build_fast_path_trace(step_name: str, response: str, stance: str) -> Dict[str, Any]:
    return {
        "step_order": [step_name],
        "metrics": [
            {
                "step": step_name,
                "duration_ms": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": 0.0,
                "status": "fast_path",
                "model_name": "fast_path",
            }
        ],
        "planner": {
            "raw": {"phase": "collect_argument_1", "student_stance": stance},
            "normalized": {
                "phase": "collect_argument_1",
                "student_stance": stance,
                "target_action": "학생의 첫 번째 근거를 요청한다.",
            },
            "metric": None,
        },
        "initial_response": {
            "status": "skipped_fast_path",
            "used_as_candidate": False,
            "text": "없음",
            "metric": None,
        },
        "external_documents": {"query": None, "results": None, "metric": None},
        "executor": {
            "source": "fast_path_stance",
            "metrics": [],
            "initial_candidate": response,
            "final_response": response,
        },
        "grader": [],
        "rewrite": [],
        "memory": {"should_refresh_memory": False},
        "final_response": response,
    }


from multi_agent import INITIAL_ASSISTANT_MESSAGE, get_runtime, get_topic
from services.llm import require_openai_key
from services.telemetry import sum_metric_cost, sum_metric_duration


st.set_page_config(page_title="AI 토론 튜터", page_icon="🗣️", layout="centered")


@st.cache_resource
def load_runtime():
    return get_runtime()


runtime = load_runtime()
TOPIC = get_topic()


st.title("AI 토론 튜터")

with st.container(border=True):
    st.markdown(f"**토론 주제**: {TOPIC}")


error_message = require_openai_key()
if error_message:
    st.error(error_message)
    st.stop()


if "messages" not in st.session_state:
    st.session_state.messages: List[Dict[str, str]] = [
        {"role": "assistant", "content": INITIAL_ASSISTANT_MESSAGE}
    ]
if "memory_summary" not in st.session_state:
    st.session_state.memory_summary = ""
if "memory_future" not in st.session_state:
    st.session_state.memory_future = None
if "previous_phase" not in st.session_state:
    st.session_state.previous_phase = "orientation"
if "dialogue_state" not in st.session_state:
    st.session_state.dialogue_state = runtime.default_dialogue_state()
if "last_run_meta" not in st.session_state:
    st.session_state.last_run_meta = {}
if "last_run_trace" not in st.session_state:
    st.session_state.last_run_trace = {}


ready_summary = runtime.memory.collect_ready_summary(st.session_state.memory_future)
if ready_summary:
    st.session_state.memory_summary = ready_summary.get("summary", "")
    st.session_state.memory_future = None
    memory_trace = dict(st.session_state.last_run_trace.get("memory", {}))
    memory_trace.update(
        {
            "existing_summary": st.session_state.memory_summary,
            "summary_ready": True,
            "should_refresh_memory": False,
            "summary_metric": ready_summary.get("metric"),
        }
    )
    st.session_state.last_run_trace["memory"] = memory_trace


def metric_line(metric: Dict[str, Any] | None) -> str:
    if not metric:
        return "-"
    duration_ms = metric.get("duration_ms")
    cost_value = metric.get("cost_usd")
    tokens = f"{metric.get('input_tokens', '-')} / {metric.get('output_tokens', '-')}"
    return f"{metric.get('step', '-')} · {duration_ms if duration_ms is not None else '-'}ms · {tokens} tok · ${cost_value if cost_value is not None else '-'}"


def compact_metrics_table(metrics: List[Dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for metric in metrics:
        rows.append(
            {
                "step": metric.get("step"),
                "time_ms": metric.get("duration_ms"),
                "in_tok": metric.get("input_tokens"),
                "out_tok": metric.get("output_tokens"),
                "cost_usd": metric.get("cost_usd"),
                "status": metric.get("status"),
            }
        )
    return pd.DataFrame(rows)


def classify_agent_name(step: str) -> str:
    if step == "planner":
        return "Planner"
    if step == "initial_response":
        return "Draft Generator"
    if step == "draft_compatibility":
        return "Verifier"
    if step == "external_documents":
        return "Search"
    if step.startswith("grader"):
        return "Verifier"
    if step.startswith("rewrite"):
        return "Executor"
    if step == "memory_signal":
        return "Memory"
    if step == "cache_lookup":
        return "Cache"
    if step.startswith("fast_path"):
        return "Fast Path"
    return "System"


def build_agent_timeline_table(trace: Dict[str, Any]) -> pd.DataFrame:
    metrics = trace.get("metrics") or []
    rows = []

    for idx, metric in enumerate(metrics, start=1):
        step = metric.get("step", "-")
        rows.append(
            {
                "순서": idx,
                "에이전트": classify_agent_name(step),
                "단계": step,
                "시간(ms)": metric.get("duration_ms"),
                "모델명": metric.get("model_name"),
            }
        )

    return pd.DataFrame(rows)


with st.sidebar:
    trace = st.session_state.last_run_trace or {}
    metrics = trace.get("metrics") or []
    meta = st.session_state.last_run_meta or {}
    step_order = trace.get("step_order") or []

    if metrics:
        st.subheader("에이전트 호출 요약")
        st.dataframe(
            build_agent_timeline_table(trace),
            use_container_width=True,
            hide_index=True,
        )

    st.subheader("디버그 요약")
    st.write(f"현재 단계: {st.session_state.previous_phase}")
    st.write(f"대화 상태: {st.session_state.dialogue_state.get('turn_state', '-')}")
    st.write(f"캐시: {'예' if meta.get('used_cache') else '아니오'}")
    if meta.get("cache_similarity") is not None:
        st.write(f"캐시 유사도: {meta['cache_similarity']:.3f}")
    st.write(f"총 시간: {meta.get('total_duration_ms', '-')}ms")
    st.write(f"총 비용: ${meta.get('total_cost_usd', '-')} ")
    if st.session_state.memory_future is not None:
        st.info("Memory Agent 요약 갱신 중")

    if step_order:
        st.markdown("**실행 순서**")
        st.code(" -> ".join(step_order), language="text")

    if metrics:
        with st.expander("호출 시간 / 비용", expanded=False):
            st.dataframe(compact_metrics_table(metrics), use_container_width=True, hide_index=True)

    if trace:
        planner_trace = trace.get("planner", {})
        initial_trace = trace.get("initial_response", {})
        external_trace = trace.get("external_documents", {})
        executor_trace = trace.get("executor", {})
        grader_trace = trace.get("grader") or []
        rewrite_trace = trace.get("rewrite") or []
        memory_trace = trace.get("memory") or {}

        with st.expander("Planner", expanded=False):
            normalized = planner_trace.get("normalized") or {}
            raw = planner_trace.get("raw") or {}
            st.write(f"phase: {normalized.get('phase', '-')}")
            st.write(f"stance: {normalized.get('student_stance', '-')}")
            st.write(f"target: {normalized.get('target_action', '-')}")
            st.caption(metric_line(planner_trace.get("metric")))
            if raw != normalized:
                st.markdown("**raw / normalized 차이**")
                st.json({"raw": raw, "normalized": normalized})
            else:
                st.caption("raw = normalized")

        with st.expander("초기 응답", expanded=False):
            st.write(f"status: {initial_trace.get('status', '-')}")
            st.write(f"used_as_candidate: {initial_trace.get('used_as_candidate', False)}")
            compatibility = initial_trace.get("compatibility") or {}
            if compatibility:
                st.write(f"compatibility: {compatibility.get('compatible')} / {compatibility.get('reason', '-')}")
            st.caption(metric_line(initial_trace.get("metric")))
            if initial_trace.get("compatibility_metric"):
                st.caption(metric_line(initial_trace.get("compatibility_metric")))
            st.code(initial_trace.get("text") or "없음", language="text")

        with st.expander("Search + Execute", expanded=True):
            st.write(f"search query: {external_trace.get('query') or '없음'}")
            if external_trace.get("metric"):
                st.caption(metric_line(external_trace.get("metric")))
            if external_trace.get("results"):
                st.code(external_trace.get("results"), language="text")
            st.write(f"response source: {executor_trace.get('source') or '-'}")
            for metric in executor_trace.get("metrics", []):
                if metric.get("step") != "external_documents":
                    st.caption(metric_line(metric))
            st.caption("initial candidate")
            st.code(executor_trace.get("initial_candidate") or "없음", language="text")
            st.caption("final response")
            st.code(executor_trace.get("final_response") or trace.get("final_response") or "없음", language="text")

        with st.expander("검증", expanded=False):
            st.markdown("**Grader**")
            st.json(grader_trace)
            st.markdown("**Rewrite**")
            st.json(rewrite_trace)

        with st.expander("Memory", expanded=False):
            st.write(f"should_refresh: {memory_trace.get('should_refresh_memory', False)}")
            if memory_trace.get("decision_metric"):
                st.caption(metric_line(memory_trace.get("decision_metric")))
            if memory_trace.get("summary_metric"):
                st.caption(metric_line(memory_trace.get("summary_metric")))
            st.json(memory_trace)


for message in st.session_state.messages:
    with st.chat_message("assistant" if message["role"] == "assistant" else "user"):
        st.markdown(message["content"])


if user_input := st.chat_input("토론 내용을 입력하세요"):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    fast_stance = None
    if st.session_state.dialogue_state.get("turn_state") == "awaiting_stance":
        fast_stance = detect_stance_only_reply(user_input)

    with st.chat_message("assistant"):
        if fast_stance:
            response = build_stance_fast_response(fast_stance)
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.session_state.previous_phase = "collect_argument_1"
            st.session_state.dialogue_state = apply_stance_fast_state(
                st.session_state.dialogue_state,
                fast_stance,
            )
            fast_trace = build_fast_path_trace("fast_path_stance", response, fast_stance)
            st.session_state.last_run_meta = {
                "model_name": "fast_path",
                "difficulty": "low",
                "used_cache": False,
                "cache_similarity": None,
                "turn_state": st.session_state.dialogue_state.get("turn_state"),
                "total_duration_ms": 0,
                "total_cost_usd": 0.0,
            }
            st.session_state.last_run_trace = fast_trace
            st.rerun()
        else:
            with st.spinner("토론 흐름을 분석하고 답변을 준비하는 중입니다..."):
                result = runtime.graph.invoke(
                    {
                        "messages": st.session_state.messages,
                        "topic": TOPIC,
                        "memory_summary": st.session_state.memory_summary,
                        "previous_phase": st.session_state.previous_phase,
                        "dialogue_state": st.session_state.dialogue_state,
                    },
                    config={"recursion_limit": 30},
                )

            response = result["response"]
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.session_state.previous_phase = result.get("latest_phase", st.session_state.previous_phase)
            st.session_state.dialogue_state = result.get("dialogue_state", st.session_state.dialogue_state)

            if result.get("should_refresh_memory"):
                st.session_state.memory_future = runtime.memory.schedule_summary(
                    messages=st.session_state.messages,
                    topic=TOPIC,
                    previous_summary=st.session_state.memory_summary,
                )

            routing = result.get("routing", {})
            cache_hit = result.get("cache_hit") or {}
            turn_trace = result.get("turn_trace", {})
            metrics = turn_trace.get("metrics") or []
            st.session_state.last_run_meta = {
                "model_name": routing.get("model_name"),
                "difficulty": routing.get("difficulty"),
                "used_cache": result.get("used_cache", False),
                "cache_similarity": cache_hit.get("similarity"),
                "turn_state": st.session_state.dialogue_state.get("turn_state"),
                "total_duration_ms": sum_metric_duration(metrics),
                "total_cost_usd": sum_metric_cost(metrics),
            }
            st.session_state.last_run_trace = turn_trace
            st.rerun()