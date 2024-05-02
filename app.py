import streamlit as st


# ----------------------------------------------------------------------------------------------------
# Page Config
# ----------------------------------------------------------------------------------------------------
st.set_page_config(page_title = "토론 챗봇")

title = "여기에 연구 제목"
description = "여기에 연구 및 실험 설명"

with st.container(border=True):
    st.markdown(
        f"""<h2 style='text-align: center; color: black;'>{title}</h1>
        <h5 style='text-align: center; color: black;'>{description}</h5>
        """, unsafe_allow_html=True)

    if st.button("시작하기", type="primary", use_container_width=True):
        st.switch_page("pages/chat.py")
