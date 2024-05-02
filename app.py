import streamlit as st
from PIL import Image, ImageDraw, ImageFont

# ----------------------------------------------------------------------------------------------------
# Page Config
# ----------------------------------------------------------------------------------------------------
st.set_page_config(
    page_title = "토론 챗봇",
)

title = "제목"
description = "설명"

with st.container(border=True):
    st.markdown(
        f"""<h1 style='text-align: center; color: black;'>{title}</h1>
        <h5 style='text-align: center; color: black;'>{description}</h5>
        """, unsafe_allow_html=True)

    if st.button("시작하기", use_container_width=True):
        st.switch_page("pages/chat.py")
