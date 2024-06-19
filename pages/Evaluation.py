import streamlit as st
from openai import OpenAI

from prompts import eval_prompt


client = OpenAI(
    api_key=st.secrets['OPENAI_API_KEY'], 
    organization=st.secrets['OPENAI_ORGANIZATION']
)

# ----------------------------------------------------------------------------------------------------
# Page Config
# ----------------------------------------------------------------------------------------------------
st.set_page_config(page_title = "토론챗봇")

title = "인공지능이 평가한 비판적사고 스킬 점수"
st.markdown(
        f"""<h2 style='text-align: left; color: black; font-size: 1.7rem; font-family: 'Roboto''>{title}</h2>
        """, unsafe_allow_html=True)


# ----------------------------------------------------------------------------------------------------
# Conversation history
# ----------------------------------------------------------------------------------------------------
# Save conversation
if "messages" in st.session_state:
    conversation = st.session_state.messages
else:
    st.error("대화 내역이 존재하지 않습니다.")

conversation_text = ""
with st.expander("대화 내역 보기"):
    # Display chat messages from history on app rerun
    for message in conversation[1:]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
        conversation_text += str(message["role"]) + ": " + str(message["content"]) + "\n"
                       
# ----------------------------------------------------------------------------------------------------
# Evaluation
# ----------------------------------------------------------------------------------------------------
with st.chat_message("assistant"):
    stream = client.chat.completions.create(
        model=st.session_state["openai_model"],
        messages=[
            {"role": "system", "content": eval_prompt},
            {"role": "user", "content": conversation_text}            
        ],
        stream=True,
    )
    response = st.write_stream(stream)