import streamlit as st
import pandas as pd
from datetime import datetime
from st_supabase_connection import SupabaseConnection
import altair as alt
import numpy as np

from result_dictionary import stressor_icons
from result_dictionary import symptoms_icons
from result_dictionary import coping_icons
from menu import menu

# from backend import average_score, percentile, summary, overall_summary
from dummy_data import df_sorted

#######################################################################################
# SETUP

st.set_page_config(
    page_title = "고민모니",
    page_icon = "./images/logo.png"
)

# .streamlit/style.css 파일 열기
with open("./.streamlit/style.css") as css:
    # CSS 파일을 읽어와서 스타일 적용
    st.markdown(f'<style>{css.read()}</style>', unsafe_allow_html=True)


st_supabase_client = st.connection("supabase",type=SupabaseConnection)

if "user_id" not in st.session_state:
    st.error("로그인이 필요합니다.")
    if st.button("로그인하러 가기"):
        st.switch_page("pages/Login.py")
    st.stop()

user_id = st.session_state["user_id"]
user_name = st.session_state["user_metadata"]["user_name"]


data = st_supabase_client.table("history").select("*").execute()
df = pd.DataFrame(data.data)
current_date = datetime.now()

filtered_df = df[(df['user_name'] == user_name) & 
                 (df['user_id'] == user_id) &
                 (df['date'] == str(current_date.year) + '-' + str(current_date.month) + '-' + str(current_date.day))]

average_score = filtered_df['average_score'].values[0]
percentile = filtered_df['percentile'].values[0]
summary = filtered_df['summary'].values[0]
overall_summary = filtered_df['overall_summary'].values[0]

# 평탄화된 리스트 생성
summary_list = [sentence.strip() for sentence in summary.split('\n') if sentence]
########################################################################################

# 메인 헤더
st.header("학업 스트레스 검사 결과")

try:
    # 사용자 학업 스트레스 점수와 해당 구간의 사람 수 표시
    st.write(f"{user_name}님의 점수는 {average_score: .2f}점이에요.")


    # 스트레스 점수 정보
    st.markdown("### 스트레스 수치")
    st.write(f":red[상위 {percentile}%]")  # 스트레스 점수를 빨간색으로 표시


    # 스트레스 원인 정보
    st.markdown("### 스트레스 원인")
    stressor = summary_list[0].split(':')[0].strip()
    stressor_explain = summary_list[0].split(':')[1].strip() 
    stressor_icon = stressor_icons.get(stressor, '👌')
    st.write(f"{stressor_icon} {stressor}")
    st.write(f"{stressor_explain}")

   # 스트레스 증상
    st.markdown("### 스트레스 증상")
    symptom = summary_list[1].split(':')[0].strip()
    symptom_explain = summary_list[1].split(':')[1].strip() 
    symptom_icon = symptoms_icons.get(symptom, '👌')
    st.write(f"{symptom_icon} {symptom}")
    st.write(f"{symptom_explain}")

    # 스트레스 대처 전략 정보
    st.markdown("### 스트레스 대처 전략")
    coping = summary_list[2].split(':')[0].strip()
    coping_explain = summary_list[2].split(':')[1].strip() 
    coping_icon = coping_icons.get(coping, '👌')
    st.write(f"{coping_icon} {coping}")
    st.write(f"{coping_explain}")

 
    st.write("#")

    st.subheader("학업 스트레스 점수 추이")

    # 라인 차트 시각화
    st.line_chart(df_sorted, x="날짜", y="스트레스 점수")
   
except:
    st.image('./images/nulldata.png')

col1, col2, col3 = st.columns(3)
with col2:
    if st.button(":bar_chart:    이전 기록 확인하기",
            use_container_width=True):
        st.switch_page("pages/History.py")
    if st.button("🏠   홈 화면으로 돌아가기",
            use_container_width=True, ):
        st.switch_page("pages/Chatbot.py")

menu()