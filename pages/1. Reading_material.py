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



title = "1) 토론주제에 대한 배경지식 익히기 위한 기사 읽기"

write = "- 챗봇과 토론을 진행하기전에, 토론주제에 대한 배경지식을 파악하기 위해서 아래 버튼을 클릭하여 기사들을 10분동안 읽어주세요. <br> - 10분이 지나면 아래의 대화창을 통해 챗봇과 토론 하시면 됩니다."




with st.container(border=True):
    st.markdown(
        f"""<h2 style='text-align: left; color: black; font-size: 1.7rem; font-family: 'Roboto''>{title}</h2>
        <h6 style='text-align: left; color: black; font-size: 1rem; font-family: 'Roboto''>{write}</h6>
        """, unsafe_allow_html=True)
    
    st.link_button("기사 1 읽기", "http://www.iconsumer.or.kr/news/articleView.html?idxno=25078")
    st.link_button("기사 2 읽기", "https://link.springer.com/article/10.1007/s40593-022-00318-x#Sec3")
    
    if st.button("챗봇과 토론하기", type="primary"):
        st.switch_page("pages/2. Interact_with_chatbot.py ")
   
    ph = st.empty()
    N = 11*60
    
    for secs in range(N,0,-1):
        mm, ss = secs//60, secs%60
        ph.metric("", f"{mm:02d}:{ss:02d}")
        time.sleep(1)
    


    
st.markdown("---")
