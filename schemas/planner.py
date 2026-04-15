from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


PhaseType = Literal[
    "orientation",
    "stance_selection",
    "collect_argument_1",
    "collect_argument_2",
    "collect_argument_3",
    "counter_argument_round_1",
    "counter_argument_round_2",
    "student_argument_round_1",
    "student_argument_round_2",
    "student_rebuttal_round",
    "closing",
]


class PlannerOutput(BaseModel):
    phase: PhaseType = Field(description="현재 토론의 큰 단계")
    student_stance: Literal["pro", "con", "unknown"] = Field(description="학생이 토론 주제에 대해 취한 입장")
    completed_argument_count: int = Field(description="학생 입장을 지지하는 근거 중 정리 완료된 개수")
    requires_specificity: bool = Field(description="학생 답변이 추상적이라 구체화 요청이 필요한지")
    requires_example: bool = Field(description="학생 답변에 실제 사례가 없어 사례 요청이 필요한지")
    need_external_grounding: bool = Field(description="신뢰성 강화를 위해 외부 검색이 필요한지")
    search_query: Optional[str] = Field(default="", description="외부 검색이 필요할 때 사용할 검색 질의")
    target_action: str = Field(description="이번 턴에서 챗봇이 해야 할 행동")
    transition_to_rebuttal: bool = Field(description="지금 턴에서 반론 및 재반론 단계로 넘겨야 하는지")
    should_end: bool = Field(description="토론 종료 여부")
    rationale: str = Field(description="판단 근거")


class VerificationResult(BaseModel):
    verdict: Literal["pass", "revise"]
    issues: str = Field(description="문제가 있으면 짧게")
    revision_instruction: str = Field(description="수정 지침")


class CompatibilityResult(BaseModel):
    compatible: bool
    reason: str
