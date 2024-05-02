import streamlit as st
# from openai import OpenAI

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate


# client = OpenAI(
#     api_key=st.secrets['OPENAI_API_KEY'], 
#     organization=st.secrets['OPENAI_ORGANIZATION']
# )

fast_llm = ChatOpenAI(model="gpt-3.5-turbo", streaming=True)
long_context_llm = ChatOpenAI(model="gpt-4-turbo", streaming=True)

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
# Set a default model
if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = "gpt-3.5-turbo"

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": "Your helpful assistant."},
        {"role": "assistant", "content": "대화 시작 시 인사말 여기에"}
    ]

# Display chat messages from history on app rerun
for message in st.session_state.messages[1:]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ----------------------------------------------------------------------------------------------------
# Chains
# ----------------------------------------------------------------------------------------------------
pos_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are helpful assistant."),
    ("user", "{input}")
])

pos_chain = pos_prompt | fast_llm

neg_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are helpful assistant."),
    ("user", "{input}")
])

neg_chain = pos_prompt | fast_llm

# ----------------------------------------------------------------------------------------------------
# Chat
# ----------------------------------------------------------------------------------------------------
# Accept user input
if user_input := st.chat_input("여기에 입력 관련 설명 가능"):
    
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(user_input)

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        # stream = client.chat.completions.create(
        #     model=st.session_state["openai_model"],
        #     messages=[
        #         {"role": m["role"], "content": m["content"]}
        #         for m in st.session_state.messages
        #     ],
        #     stream=True,
        # )
        stream = pos_chain.stream({"input": user_input})
        response = st.write_stream(stream)
        
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})
        
        