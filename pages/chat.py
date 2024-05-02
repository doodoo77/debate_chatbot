import streamlit as st
from openai import OpenAI

from prompts import pos_prompt, neg_prompt


client = OpenAI(
    api_key=st.secrets['OPENAI_API_KEY'], 
    organization=st.secrets['OPENAI_ORGANIZATION']
)

# ----------------------------------------------------------------------------------------------------
# Page Config
# ----------------------------------------------------------------------------------------------------
st.set_page_config(page_title = "토론챗봇")

st.title("여기에 제목")

st.write("여기에 설명 가능")

st.link_button("기사 1 읽기", "http://www.iconsumer.or.kr/news/articleView.html?idxno=25078")
st.link_button("기사 2 읽기", "https://link.springer.com/article/10.1007/s40593-022-00318-x#Sec3")

if st.button("평가 결과 보기", type="primary"):
    st.switch_page("pages/evaluation.py")
    
st.markdown("---")

# ----------------------------------------------------------------------------------------------------
# Session State
# ----------------------------------------------------------------------------------------------------
if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = "gpt-3.5-turbo"
    
# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": pos_prompt},
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
if user_input := st.chat_input("여기에 입력 관련 설명 가능"):
    
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
        
    # Check
    if "종료" in response:
        st.session_state.messages.append({"role": "system", "content": neg_prompt})
        
    
        
        