from __future__ import annotations

import json
import time
from statistics import mean

from multi_agent import INITIAL_ASSISTANT_MESSAGE, get_runtime, get_topic


SAMPLE_INPUTS = [
    "저는 찬성이에요. 알고리즘 추천은 필요한 정보를 빨리 찾게 도와줘요.",
    "첫 번째 근거는 유튜브나 넷플릭스처럼 취향에 맞는 콘텐츠를 빨리 찾게 해준다는 점이에요.",
    "두 번째 근거는 건강관리 앱이 사용자 상태에 맞춰 운동이나 식단을 추천해준다는 점이에요.",
    "그런데 추천이 계속 비슷한 정보만 보여줘서 오히려 시야가 좁아질 수도 있지 않나요?",
]


def main() -> None:
    runtime = get_runtime()
    topic = get_topic()
    messages = [{"role": "assistant", "content": INITIAL_ASSISTANT_MESSAGE}]
    previous_phase = "orientation"
    memory_summary = ""

    latencies = []
    run_logs = []

    for text in SAMPLE_INPUTS:
        messages.append({"role": "user", "content": text})
        start = time.perf_counter()
        result = runtime.graph.invoke(
            {
                "messages": messages,
                "topic": topic,
                "memory_summary": memory_summary,
                "previous_phase": previous_phase,
            }
        )
        latency = time.perf_counter() - start
        latencies.append(latency)

        response = result["response"]
        messages.append({"role": "assistant", "content": response})
        previous_phase = result.get("latest_phase", previous_phase)

        if result.get("should_refresh_memory"):
            memory_summary = runtime.memory.summarize(messages, topic, memory_summary)

        run_logs.append(
            {
                "user": text,
                "assistant": response,
                "latency_sec": round(latency, 3),
                "routing": result.get("routing", {}),
                "used_cache": result.get("used_cache", False),
                "phase": result.get("latest_phase"),
            }
        )

    summary = {
        "avg_latency_sec": round(mean(latencies), 3),
        "max_latency_sec": round(max(latencies), 3),
        "min_latency_sec": round(min(latencies), 3),
        "runs": run_logs,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
