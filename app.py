import streamlit as st
from openai import OpenAI
import os 
from matplotlib import font_manager as fm
from prompts import pos_prompt
import time
# ----------------------------------------------------------------------------------------------------
# Page Config
# ----------------------------------------------------------------------------------------------------

st.set_page_config(page_title = "토론 챗봇")

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
                
    if "토론이 종료되었어." or "10초" in response:
        time.sleep(10)
        st.switch_page("pages/Evaluation.py")