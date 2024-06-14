import streamlit as st
from openai import OpenAI

from prompts import pos_prompt
import time

client = OpenAI(
    api_key=st.secrets['OPENAI_API_KEY'], 
    organization=st.secrets['OPENAI_ORGANIZATION']
)

# ----------------------------------------------------------------------------------------------------
# Page Config
# ----------------------------------------------------------------------------------------------------
st.set_page_config(page_title = "토론챗봇")



title = "토론주제에 대한 배경지식 익히기 위한 기사 읽기"

write = "챗봇과 토론을 진행하기전, 토론주제에 대한 배경지식을 쌓기 위해 아래 버튼[기사 x 읽기]을 클릭하여 10분동안 3개의 기사를 모두 읽어주세요. 기사의 내용은 토론 중에 활용될 예정이니 창을 닫지 마세요. <br><br> 10분이 지나면 아래 버튼[챗봇과 토론하기]을 클릭하여 챗봇과 토론 하시면 됩니다."




with st.container(border=True):
    st.markdown(
        f"""<h2 style='text-align: left; color: black; font-size: 1.7rem; font-family: 'Roboto''>{title}</h2>
        <h6 style='text-align: left; color: black; font-size: 1rem; font-family: 'Roboto''>{write}</h6>
        """, unsafe_allow_html=True)
    
    st.link_button("기사 1 읽기", "https://www.dailypop.kr/news/articleView.html?idxno=63727")
    st.link_button("기사 2 읽기", "https://www.khan.co.kr/it/it-general/article/202307080830001")
    st.link_button("기사 3 읽기", "https://www.kmib.co.kr/article/view.asp?arcid=0015339306")
    
    if st.button("챗봇과 토론하기", type="primary"):
        st.switch_page("pages/2. Interact_with_chatbot.py")
   
    ph = st.empty()
    N = 630
    
    for secs in range(N,0,-1):
        mm, ss = secs//60, secs%60
        ph.metric("", f"{mm:02d}:{ss:02d}")
        time.sleep(1)
    


    
st.markdown("---")
