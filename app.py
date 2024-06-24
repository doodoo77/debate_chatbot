import streamlit as st
from openai import OpenAI
import os 
from matplotlib import font_manager as fm
from prompts import pos_prompt
import time
# ----------------------------------------------------------------------------------------------------
# Page Config
# ----------------------------------------------------------------------------------------------------

st.set_page_config(page_title = "AI 토론 튜터")

title = "AI 토론 튜터와 토론 연습을 해보자"
# description = "토론주제에 대해서 챗봇과 토론 연습을 해보자"

fpath = os.path.join(os.getcwd(), "./NanumGothic-ExtraBold.ttf")
prop= fm.FontProperties(fname=fpath)

with st.container(border=True):
    st.markdown(
        f"""<h2 style='text-align: center; color: black; font-size: 1.7rem; fontpropertise: prop'>{title}</h2>""", unsafe_allow_html=True)
        
    st.image('img.PNG')


client = OpenAI(
    api_key=st.secrets['OPENAI_API_KEY'], 
    organization=st.secrets['OPENAI_ORGANIZATION']
)
# ----------------------------------------------------------------------------------------------------
# Session State
# ----------------------------------------------------------------------------------------------------
if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = "gpt-4o"
    
# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": pos_prompt},
        {"role": "assistant", "content": "안녕! 나는 오늘 너와 토론을 진행할 토론 파트너야. 만나서 반가워."}
        ]
       
    
# Display chat messages from history on app rerun
for message in st.session_state.messages:
    if message["role"] == "system":
        continue
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        


# ----------------------------------------------------------------------------------------------------
# Chat
# ----------------------------------------------------------------------------------------------------
if user_input := st.chat_input(""):
    
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(user_input)

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        stream = client.chat.completions.create(
            model=st.session_state["openai_model"],
            messages=[
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ],
            stream=True,
        )
        response = st.write_stream(stream)       
        
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})
                
    if "토론이 종료되었어" in response:
        time.sleep(5)
        st.switch_page("pages/Evaluation.py")