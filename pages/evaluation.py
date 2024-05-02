import streamlit as st
from openai import OpenAI


client = OpenAI(
    api_key=st.secrets['OPENAI_API_KEY'], 
    organization=st.secrets['OPENAI_ORGANIZATION']
)

# ----------------------------------------------------------------------------------------------------
# Page Config
# ----------------------------------------------------------------------------------------------------
st.set_page_config(
    page_title = "고민모니",
    page_icon = "./images/logo.png"
)

st.title("평가 결과")

st.write("여기에 설명 가능")
st.markdown("---")

with st.expander("평가 결과 보기"):
    # Display chat messages from history on app rerun
    for message in st.session_state.messages[1:]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

