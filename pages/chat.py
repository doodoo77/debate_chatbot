import streamlit as st
# from openai import OpenAI

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories.streamlit import StreamlitChatMessageHistory

from prompts import pos_prompt, neg_prompt

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

if "chain" not in st.session_state:
    st.session_state["chain"] = "positive"
    
# Initialize chat history
# if "messages" not in st.session_state:
#     st.session_state.messages = [
#         {"role": "system", "content": "Your helpful assistant."},
#         {"role": "assistant", "content": "대화 시작 시 인사말 여기에"}
#     ]

# Set up memory
msgs = StreamlitChatMessageHistory(key="langchain_messages")
if len(msgs.messages) == 0:
    msgs.add_ai_message("How can I help you?")

# Display chat messages from history on app rerun
# for message in st.session_state.messages:
#     if message["role"] == "system":
#         continue
#     with st.chat_message(message["role"]):
#         st.markdown(message["content"])

for msg in msgs.messages:
    st.chat_message(msg.type).write(msg.content)

# ----------------------------------------------------------------------------------------------------
# Chains
# ----------------------------------------------------------------------------------------------------
pos_prompt = ChatPromptTemplate.from_messages([
    ("system", pos_prompt),
    MessagesPlaceholder(variable_name="history"),
    ("user", "{input}")
])

pos_chain = pos_prompt | fast_llm

pos_chain_with_history = RunnableWithMessageHistory(
    pos_chain,
    lambda session_id: msgs,
    input_messages_key="input",
    history_messages_key="history",
)

neg_prompt = ChatPromptTemplate.from_messages([
    ("system", neg_prompt),
    MessagesPlaceholder(variable_name="history"),
    ("user", "{input}")
])

neg_chain = neg_prompt | fast_llm

# ----------------------------------------------------------------------------------------------------
# Chat
# ----------------------------------------------------------------------------------------------------
# Accept user input
if user_input := st.chat_input("여기에 입력 관련 설명 가능"):
    
    # Add user message to chat history
    # st.session_state.messages.append({"role": "user", "content": user_input})
    
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
        # st.write(st.session_state.chain)
        # if st.session_state.chain == "positive":
        #     stream = pos_chain.stream({"input": user_input})
        # elif st.session_state.chain == "negative":
        #     stream = neg_chain.stream({"input": user_input})
        # response = st.write_stream(stream)
        config = {"configurable": {"session_id": "any"}}
        response = pos_chain_with_history.invoke({"input": user_input}, config)
        st.markdown(response.content)            
        
    # Check
    if "you will debate with an opponent chatbot" in response:
        st.session_state.chain = "negative"
        
    # Add assistant response to chat history
    # st.session_state.messages.append({"role": "assistant", "content": response})
        
        