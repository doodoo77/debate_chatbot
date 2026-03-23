# debate_chatbot

서울과학기술대학교 인공지능응용학과 프로젝트용 1:1 찬반 토론 연습 챗봇입니다.

현재 코드는 아래 구조를 중심으로 재설계되어 있습니다.

- **Planner Agent**: 현재 토론 단계를 구조화해서 판단
- **Execute Agent**: 토론 발화 생성, Tavily 기반 외부 검색 Tool Calling, 자기검증 루프 수행
- **Memory Agent**: 장기 대화 요약을 백그라운드에서 비동기로 갱신
- **Dynamic Routing**: 학생 발화 난이도에 따라 `gpt-4o-mini` / `gpt-4o` 라우팅
- **Semantic Cache**: Redis 기반 의미 유사 캐시
- **LangGraph Workflow**: `prepare_turn -> cache_lookup -> execute -> memory_signal`

## 프로젝트 구조

```text
app.py
multi_agent.py
config.py
prompts.py
agents/
  planner.py
  executor.py
  memory.py
services/
  llm.py
  router.py
  search.py
  cache.py
  similarity.py
graph/
  workflow.py
schemas/
  planner.py
```

## 실행 전 준비

### 1. 가상환경 생성

```bash
conda create -n debatebot python=3.10 -y
conda activate debatebot
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. Streamlit secrets 설정

`.streamlit/secrets.toml` 파일을 만들고 아래 값을 채워주세요.

```toml
OPENAI_API_KEY = "YOUR_OPENAI_KEY"
OPENAI_ORGANIZATION = "YOUR_OPENAI_ORG"  # 선택
TAVILY_API_KEY = "YOUR_TAVILY_KEY"
REDIS_URL = "redis://localhost:6379/0"
MODEL_EASY = "gpt-4o-mini"
MODEL_HARD = "gpt-4o"
```

Redis 서버가 로컬에서 떠 있어야 Semantic Cache가 Redis에 저장됩니다.
Redis 연결이 실패하면 앱은 메모리 캐시로 자동 폴백합니다.

### 4. 실행

```bash
streamlit run app.py
```

## 구현 포인트

### Planner Agent
- 최근 대화와 메모리 요약을 바탕으로 현재 단계를 Pydantic 스키마로 구조화합니다.
- 학생 입장, 현재 phase, 구체화 필요 여부, 사례 요청 여부, 외부 검색 필요 여부를 JSON 형태로 관리합니다.

### Execute Agent
- Planner 결과와 Memory 요약을 받아 현재 턴 발화를 생성합니다.
- 외부 근거가 필요하면 Tavily 검색을 수행하고, 필요 시 Tool Calling 경로를 사용합니다.
- Verifier를 통해 단계 정합성과 논리 흐름을 검증합니다.
- 재생성 결과가 기존 답변과 지나치게 유사하면 조기 종료합니다.

### Memory Agent
- 토큰 임계치 초과 또는 phase family 전환 시 요약 갱신 신호를 발생시킵니다.
- 요약은 백그라운드 스레드에서 비동기로 생성됩니다.

### 성능 최적화
- Planner와 초안 생성을 병렬 실행합니다.
- Redis 기반 semantic caching으로 반복 입력에 대한 응답을 재사용합니다.
- 입력 길이와 논리 복잡도에 따라 모델을 라우팅합니다.

## 주의사항

- 기본 토론 주제는 `알고리즘의 추천이 우리의 삶을 풍요롭게 해줄까?`로 고정되어 있습니다.
- 구조는 확장 가능하게 설계되어 있어 다른 주제로 바꾸려면 `DEBATE_TOPIC` 또는 secrets 값을 변경하면 됩니다.
