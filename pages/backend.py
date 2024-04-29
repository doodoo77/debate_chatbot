from st_supabase_connection import SupabaseConnection
import altair as alt
from datetime import datetime
import streamlit as st
import pandas as pd
from openai import OpenAI
import csv
from scipy.stats import norm
import re

########################################################################################
# SETUP 

st.set_page_config(
    page_title = "고민모니",
    page_icon = "./images/logo.png"
)

# .streamlit/style.css 파일 열기
with open("./.streamlit/style.css") as css:
    # CSS 파일을 읽어와서 스타일 적용
    st.markdown(f'<style>{css.read()}</style>', unsafe_allow_html=True)

st.title("결과 분석 중입니다...🔍\n 쪼꼼만 기다려주이소~~>< \n 오래 걸려도 이해해 줄 수 있지예~~?❤️❤️❤️")
########################################################################################


st_supabase_client = st.connection("supabase",type=SupabaseConnection)

# Set OpenAI API key 
client = OpenAI(api_key=st.secrets['OPENAI_API_KEY'], 
                organization=st.secrets['OPENAI_ORGANIZATION'])
openai_api_key = st.secrets['OPENAI_API_KEY']

data = st_supabase_client.table("chat").select("*").execute()
df = pd.DataFrame(data.data)
df['created_at'] = pd.to_datetime(df['created_at'])

if "user_id" not in st.session_state:
    st.error("로그인이 필요합니다.")
    if st.button("로그인하러 가기"):
        st.switch_page("pages/Login.py")
    st.stop()
    
user_id = st.session_state["user_id"]
user_name = st.session_state["user_metadata"]["user_name"]

current_date = datetime.now()

filtered_df = df[(df['user_name'] == user_name) & 
                 (df['user_id'] == user_id) &
                 (df['created_at'].dt.year == current_date.year) &
                 (df['created_at'].dt.month == current_date.month) &
                 (df['created_at'].dt.day == current_date.day)]

def get_chat_history(df):
    chat_history = ""
    for index, row in df.iterrows():
        if row['role'] == 'user':
            chat_history += "User: " + str(row['message']) + "\n"
        elif row['role'] == 'assistant':
            chat_history += "AI: " + str(row['message']) + "\n"
    return chat_history

context = get_chat_history(filtered_df)

def get_scores(context):
    system_prompt = f"""Based on the conversation between 'User' and 'AI', your task is to assign scores \
    reflecting the frequency of various causes of academic stress, symptoms of academic stress, and coping strategies for academic stress of 'User' as discussed in the dialogue. \
    Use a scale from 0 to 5 to rate each item, where 0 means the item was never mentioned, 1 means 'Never', 2 means 'Rarely', 3 means 'Sometimes', 4 means 'Often', and 5 means 'Always'.

    The items to be scored are as follows:
    1. Causes of Academic Stress: Intense competition (치열한 경쟁), Assignment overload (과제 부담), Relationship with professors (교수님과의 관계), Evaluation (평가), Academic pressure (학업 부담), Difficulty of classes (수업 난이도), Pressure to participate in classes (수업 참여 부담), Limited time (제한된 시간).
    2. Symptoms of Academic Stress: Sleep disorders (수면 장애), Chronic fatigue (만성 피로), Headaches (두통), Digestive issues such as abdominal pain (복부 통증 등의 소화 문제), Nail-biting (손톱 물기), Drowsiness (졸음), Anxiety (불안감), Depression (우울감), Despair (절망감), Decreased concentration (집중 저하), Increased aggression (공격성 증가), Tendency to argue (논쟁 경향), Isolation from others (사람들로부터의 고립), Indifference to studies (학업에 대한 무관심), Increase or decrease in food intake (음식 섭취 증가 또는 감소).
    3. Academic Stress Coping Strategies: Active coping (능동적 대응), Planning and execution (계획 수립 및 수행), Self-praise (자신에 대한 칭찬), Religious beliefs (종교적 신념), Information gathering about the situation (상황에 대한 정보 수집), Emotional expression and sharing secrets (감정 표출 및 비밀 공유).

    Knowledge:
    Causes of Academic Stress
    Intense competition (치열한 경쟁): The fierce battle among students to achieve top grades, acceptance into prestigious universities, or scholarships creates a high-pressure environment. This atmosphere fosters a fear of failure and a constant push to excel beyond peers, significantly contributing to stress levels.
    Assignment overload (과제 부담): This refers to the overwhelming number of assignments, projects, and deadlines students face. Balancing numerous tasks simultaneously can be daunting, leading to feelings of anxiety and stress due to the fear of not meeting expectations or deadlines.
    Relationship with professors (교수님과의 관계): Strained or challenging relationships with professors can increase academic stress. Difficulty in communication, differing expectations, or perceived unfairness in treatment or grading can create a hostile learning environment.
    Evaluation (평가): The pressure of exams, grades, and continuous assessment can be a significant source of stress. The fear of poor performance or the consequences of not achieving certain academic standards can lead to heightened anxiety.
    Academic pressure (학업 부담): This encompasses the overall expectation to succeed academically, often imposed by oneself, family, or society. The need to attain a certain level of achievement to pursue further education or career aspirations can be overwhelming.
    Difficulty of classes (수업 난이도): Courses with complex content, high expectations, or poor instructional quality can lead to frustration and stress. Students may struggle to understand material or keep up with the pace, fearing falling behind.
    Pressure to participate in classes (수업 참여 부담): The expectation to actively engage in discussions, answer questions, or present in front of peers can induce anxiety. This is particularly stressful for introverted or shy students who may fear public speaking or judgment.
    Limited time (제한된 시간): Managing academic responsibilities alongside extracurricular activities, part-time jobs, or personal commitments can create a time crunch. The constant race against the clock to fulfill obligations can lead to stress and burnout.
    Symptoms of Academic Stress
    Sleep disorders (수면 장애): Difficulty falling asleep, insomnia, or disrupted sleep patterns are common in stressed students. This affects overall health and ability to concentrate during the day.
    Chronic fatigue (만성 피로): Persistent tiredness not relieved by rest, often due to continuous stress, affecting students’ energy levels and motivation.
    Headaches (두통): Stress can trigger tension headaches, characterized by a constant ache around the head, especially in the temples or back of the neck.
    Digestive issues such as abdominal pain (복부 통증 등의 소화 문제): Stress can affect the gastrointestinal system, leading to symptoms like abdominal pain, nausea, or indigestion.
    Nail-biting (손톱 물기): A physical manifestation of nervousness or anxiety, often a subconscious response to stress.
    Drowsiness (졸음): Excessive sleepiness despite adequate sleep can indicate stress, as the body’s way of shutting down to escape stressors.
    Anxiety (불안감): Persistent worry about academic performance, future prospects, or other stressors, often manifesting as restlessness or a feeling of being overwhelmed.
    Depression (우울감): Feelings of sadness, hopelessness, or lack of interest in activities once enjoyed, often resulting from prolonged stress.
    Despair (절망감): A sense of hopelessness or inability to see a positive outcome, particularly in regard to academic achievements or future prospects.
    Decreased concentration (집중 저하): Difficulty focusing on tasks or retaining information, often due to the distracting nature of stress.
    Increased aggression (공격성 증가): Heightened irritability or frustration, leading to aggressive reactions or outbursts.
    Tendency to argue (논쟁 경향): An increased inclination towards disagreement or conflict, often as a stress response.
    Isolation from others (사람들로부터의 고립): Withdrawing from social interactions, preferring solitude, which can worsen feelings of stress and loneliness.
    Indifference to studies (학업에 대한 무관심): A lack of interest or motivation towards academic work, often a sign of burnout.
    Increase or decrease in food intake (음식 섭취 증가 또는 감소): Changing eating habits, either eating more or less, can be a response to stress.
    Academic Stress Coping Strategies
    Active coping (능동적 대응): Taking direct action to confront and manage the sources of stress, rather than avoiding them.
    Planning and execution (계획 수립 및 수행): Setting realistic goals, prioritizing tasks, and developing a structured approach to manage workload effectively.
    Self-praise (자신에 대한 칭찬): Acknowledging and rewarding oneself for achievements, however small, to build self-esteem and reduce feelings of inadequacy.
    Religious beliefs (종교적 신념): Some find solace and strength in their faith, using prayer or meditation as a means to cope with stress.
    Information gathering about the situation (상황에 대한 정보 수집): Understanding the stressors more deeply can aid in devising more effective strategies to address them.
    Emotional expression and sharing secrets (감정 표출 및 비밀 공유): Talking about one's feelings and experiences with trusted individuals can provide relief from emotional burdens and foster a support network.

    Below is the conversation between 'User' and 'AI':
    {context}

    Your response should be formatted as follows, with each item's respective score, except for those whose score is 0:
    1, 5, 3, 4, 2, ...
    (You must return only numbers and commas. No texts!!) 
    """

    completion = client.chat.completions.create(
        model="gpt-4-0125-preview",
        messages=[
            {"role": "system", "content": system_prompt},
        ],
        temperature=0.0,
        stream=False
    )
    return completion.choices[0].message.content

scores = get_scores(context)
numbers = re.findall(r'\d+', scores)
number_list = [int(num) for num in numbers]
average_score = sum(number_list) / len(number_list)

def percentile_above(mean, std_dev, value):
    z_score = (value - mean) / std_dev
    percentile = (1 - norm.cdf(z_score)) * 100
    return percentile

percentile = percentile_above(3.773399014778325, 0.9273521676028207, average_score)
percentile = round(percentile, 2)

def summary(context):
    system_prompt = f"""Based on the conversation between 'User' and 'AI', your task is to find out the user's one representative stressor, symptom, and coping strategy.
    After you find out the representative stressor, symptom, and coping strategy, you should provide a brief summary of each item based on the conversation.

    The items to be chosen are as follows:
    1. Causes of Academic Stress: Intense competition (치열한 경쟁), Assignment overload (과제 부담), Relationship with professors (교수님과의 관계), Evaluation (평가), Academic pressure (학업 부담), Difficulty of classes (수업 난이도), Pressure to participate in classes (수업 참여 부담), Limited time (제한된 시간).
    2. Symptoms of Academic Stress: Sleep disorders (수면 장애), Chronic fatigue (만성 피로), Headaches (두통), Digestive issues such as abdominal pain (복부 통증 등의 소화 문제), Nail-biting (손톱 물기), Drowsiness (졸음), Anxiety (불안감), Depression (우울감), Despair (절망감), Decreased concentration (집중 저하), Increased aggression (공격성 증가), Tendency to argue (논쟁 경향), Isolation from others (사람들로부터의 고립), Indifference to studies (학업에 대한 무관심), Increase or decrease in food intake (음식 섭취 증가 또는 감소).
    3. Academic Stress Coping Strategies: Active coping (능동적 대응), Planning and execution (계획 수립 및 수행), Self-praise (자신에 대한 칭찬), Religious beliefs (종교적 신념), Information gathering about the situation (상황에 대한 정보 수집), Emotional expression and sharing secrets (감정 표출 및 비밀 공유).

    Below is the conversation between 'User' and 'AI':
    {context}

    Your response must follow the format below:
    치열한 경쟁: 강한 경쟁으로 인해 스트레스를 느끼고 있습니다. 
    수면 장애: 시험기간이 다가오면서 잠을 제대로 못 자고 있습니다.
    능동적 대응: 스트레스를 해소하기 위해 능동적으로 대처하고 있습니다. 

    You must answer in Korean.
    """

    completion = client.chat.completions.create(
        model="gpt-4-0125-preview",
        messages=[
            {"role": "system", "content": system_prompt},
        ],
        temperature=0.0,
        stream=False
    )
    return completion.choices[0].message.content

summary = summary(context)

def overall_summary(context):
    system_prompt = f"""Based on the conversation between 'User' and 'AI', your task is to summarize the user's stressor in one short sentence.

    Below is the conversation between 'User' and 'AI':
    {context}

    Your response must follow the format below:
    시험기간이 다가와 힘들었던 하루
    ('~인 하루' 형태로 끝낼 것)

    You must answer in Korean.
    """

    completion = client.chat.completions.create(
        model="gpt-4-0125-preview",
        messages=[
            {"role": "system", "content": system_prompt},
        ],
        temperature=0.0,
        stream=False
    )
    return completion.choices[0].message.content

overall_summary = overall_summary(context)

# current_date.year, current_date.month, current_date.day: 현재 날짜의 년, 월, 일
# average_score: 평균 점수
# percentile: 자신의 점수가 전체 사용자 중 몇 %에 위치하는지 
# summary: 대표적인 스트레스 요인, 증상, 대처 전략 요약
#          e.g., 평가: 사용자는 평가로 인한 스트레스를 겪고 있으며, 좋은 학점을 받아야 한다는 압박감을 느끼고 있습니다.
#               만성 피로: 사용자는 스트레스로 인해 만성 피로를 겪고 있으며, 매일 매일 피곤함을 느끼고 있습니다.
#               능동적 대응: 사용자는 학업 스트레스를 받는 상황에서 능동적으로 대응하려고 노력하고 있습니다.
# overall_summary: 전체 대화 한 줄 요약

try:
    st_supabase_client.table("history").select("user_id, user_name").execute()
except Exception as e:
    st.write(e)

if len(context) < 10:
        st.error("대화 데이터가 부족합니다.")
        if st.button("다시 챗봇과 대화하러 가기"):
            st.switch_page("pages/Chatbot.py")
        st.stop()

st_supabase_client.table("history").insert(
            [
                {
                    "user_id": user_id,
                    "user_name": user_name,
                    "date": str(current_date.year) + "-" + str(current_date.month) + "-" + str(current_date.day),
                    "average_score": average_score,
                    "percentile": percentile,
                    "summary": summary,
                    "overall_summary": overall_summary
                }
            ]
        ).execute()

st.switch_page("pages/Result.py")