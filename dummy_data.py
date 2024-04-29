import pandas as pd
import random
import datetime as dt

from result_dictionary import stressor_icons
from result_dictionary import symptoms_icons
from result_dictionary import coping_icons

random.seed = 10
# 임의의 날짜 생성 (지난 10일 동안의 날짜)
date_range = [dt.date.today() - dt.timedelta(days=i) for i in range(10)]

# 스트레스 점수는 0~100 범위에서 임의로 생성
stress_scores = [random.uniform(1, 5) for _ in range(10)]

# 임의의 대화 주요 내용
conversations = [
    "친구와 대화",
    "교수와 상담",
    "학업 계획",
    "시험 공부",
    "운동 이야기",
    "가족과 저녁 식사",
    "영화 감상",
    "음악 듣기",
    "여행 계획",
    "미래에 대한 고민",
]

stressor = list(stressor_icons.keys())
symptoms = list(symptoms_icons.keys())
coping = list(coping_icons.keys())

# DataFrame 생성
data = {
    "날짜": date_range,
    "스트레스 점수":  stress_scores,
    "대화 주요 내용": conversations[:10],  # 10개 이하로 제한
    "스트레스 원인": [random.choice(stressor) for _ in range(10)],
    "스트레스 증상": [random.choice(symptoms) for _ in range(10)],
    "스트레스 대처 전략": [random.choice(coping) for _ in range(10)],
}

df = pd.DataFrame(data)
# 데이터 프레임을 날짜 기준으로 내림차순 정렬
df_sorted = df.sort_values(by="날짜", ascending=False)