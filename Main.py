import streamlit as st
import os 
from matplotlib import font_manager as fm
# ----------------------------------------------------------------------------------------------------
# Page Config
# ----------------------------------------------------------------------------------------------------

st.set_page_config(page_title = "토론 챗봇")

title = "서울과학기술대학교 인간중심인공지능 연구실"
description = "먼저 바쁘신 와중에 실험에 참여해주셔서 감사합니다. <br><br> 본 실험에서 참가자께서는 1) 챗봇과 토론을 진행하신 후, <br> 2) 토론 내용을 기반으로 인공지능이 분석한 본인의 비판적사고 스킬 점수를 제공받습니다. <br> 본 실험은 이러한 인공지능 평가에 대한 참가자의 인식을 조사하기 위해 설계되었습니다. <br><br> 수집된 데이터(토론 내용, 비판적사고 스킬 점수, 인터뷰 내용)는 <br> 오직 학술 연구 목적으로만 사용되며, 생명윤리법 제15조에 의해서 보호받습니다. <br><br> 다시 한번 실험에 참여해주셔서 감사합니다. <br><br> 실험 참여에 동의하시면 아래 '시작하기' 버튼을 눌러주세요."

fpath = os.path.join(os.getcwd(), "./NanumGothic-ExtraBold.ttf")
prop= fm.FontProperties(fname=fpath)

with st.container(border=True):
    st.markdown(
        f"""<h2 style='text-align: center; color: black; font-size: 1.7rem; fontpropertise: prop'>{title}</h2>
        <h6 style='text-align: center; color: black; font-size: 1rem; fontpropertise: prop'>{description}</h6>
        """, unsafe_allow_html=True)

    if st.button("시작하기", type="primary", use_container_width=True):
        st.switch_page("pages/1. Reading_material.py")
