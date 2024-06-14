import streamlit as st
from openai import OpenAI

from prompts import pos_prompt


client = OpenAI(
    api_key=st.secrets['OPENAI_API_KEY'], 
    organization=st.secrets['OPENAI_ORGANIZATION']
)

# ----------------------------------------------------------------------------------------------------
# Page Config
# ----------------------------------------------------------------------------------------------------
st.set_page_config(page_title = "토론챗봇")

title = "2) 챗봇과 토론하기"
st.markdown(
        f"""<h2 style='text-align: left; color: black; font-size: 1.7rem; font-family: 'Roboto''>{title}</h2>
        """, unsafe_allow_html=True)

st.write("여기에 설명 가능")

if st.button("평가하기", type="primary"):
    st.switch_page("pages/3. Evaluation.py ")

st.markdown("---")

# ----------------------------------------------------------------------------------------------------
# Session State
# ----------------------------------------------------------------------------------------------------
if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = "gpt-4o"
    
# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": pos_prompt},
        {"role": "assistant", "content": "안녕하세요. 저는 오늘 당신과 토론을 진행할 토론 파트너입니다. 만나서 반가워요."}
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
        

        
    
        
        