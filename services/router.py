from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

from config import get_settings


LOGIC_MARKERS = [
    "왜냐하면",
    "따라서",
    "하지만",
    "반면",
    "예를 들어",
    "즉",
    "근거",
    "사례",
    "반론",
    "재반론",
]


@dataclass
class RoutingDecision:
    model_name: str
    difficulty: str
    score: int
    reasons: List[str]

    def to_dict(self) -> dict:
        return {
            "model_name": self.model_name,
            "difficulty": self.difficulty,
            "score": self.score,
            "reasons": self.reasons,
        }


class DynamicRouter:
    def __init__(self) -> None:
        self.settings = get_settings()

    def route(self, user_text: str, conversation_turns: int) -> RoutingDecision:
        normalized = user_text.strip()
        reasons: List[str] = []
        score = 0

        char_len = len(normalized)
        sentence_count = max(1, len(re.findall(r"[.!?\n]", normalized)) + 1)
        marker_count = sum(1 for marker in LOGIC_MARKERS if marker in normalized)

        if char_len > 80:
            score += 1
            reasons.append("입력 길이가 김")
        if char_len > 180:
            score += 1
            reasons.append("장문 발화")
        if sentence_count >= 3:
            score += 1
            reasons.append("문장 수가 많음")
        if marker_count >= 2:
            score += 1
            reasons.append("논리 연결어가 다수 포함됨")
        if conversation_turns >= 10:
            score += 1
            reasons.append("장기 대화 구간")

        if score >= 3:
            return RoutingDecision(
                model_name=self.settings.model_hard,
                difficulty="hard",
                score=score,
                reasons=reasons or ["복합 논증 구간"],
            )

        return RoutingDecision(
            model_name=self.settings.model_easy,
            difficulty="easy",
            score=score,
            reasons=reasons or ["비교적 단순한 요청"],
        )
