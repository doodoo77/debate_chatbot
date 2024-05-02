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
st.set_page_config(
    page_title = "토론챗봇",
    page_icon = "./images/logo.png"
)

st.title("평가 결과")

st.write("여기에 설명 가능")

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
# Chains
# ----------------------------------------------------------------------------------------------------
eval_prompt = ChatPromptTemplate.from_messages([
    ("system", "Translate into English."),
    ("user", "{input}")
])

eval_chain = eval_prompt | fast_llm
            
# ----------------------------------------------------------------------------------------------------
# Evaluation
# ----------------------------------------------------------------------------------------------------
# Display 
with st.chat_message("assistant"):
    # stream = client.chat.completions.create(
    #     model=st.session_state["openai_model"],
    #     messages=[
    #         {"role": "system", "content": "대화 내역 요약해줘"},
    #         {"role": "user", "content": conversation_text}            
    #     ],
    #     stream=True,
    # )
    stream = eval_chain.stream({"input": conversation_text})
    response = st.write_stream(stream)