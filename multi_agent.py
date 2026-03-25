from __future__ import annotations

from functools import lru_cache

from config import get_settings
from graph.workflow import DebateChatbotRuntime


INITIAL_ASSISTANT_MESSAGE = (
    "좋아. 먼저 간단히 절차를 설명해볼게. "
    "우리는 먼저 네 입장을 정하고, 그 입장을 지지하는 근거 2개를 정리한 뒤, "
    "반론과 재반론 연습으로 넘어갈 거야. 이제 본격적인 토론을 시작할게. "
    "주제는 '알고리즘의 추천이 우리의 삶을 풍요롭게 해줄까?'야. 너는 찬성과 반대 중 어느 쪽이니?"
)


@lru_cache(maxsize=1)
def get_runtime() -> DebateChatbotRuntime:
    return DebateChatbotRuntime()


def get_topic() -> str:
    return get_settings().topic
