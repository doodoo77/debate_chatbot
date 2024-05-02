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

st.title("챗봇")

st.write("여기에 설명 가능")

if st.button("평가 결과 보기"):
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
# Chatbot
# ----------------------------------------------------------------------------------------------------
# Accept user input
if prompt := st.chat_input("여기에 입력 관련 설명 가능"):
    
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)

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
            
        # Store user and assistant message to database
        # st_supabase_client.table("chat").insert(
        #     [
        #         {
        #             "user_id": user_id,
        #             "user_name": user_name,
        #             "role": "user",
        #             "message": user_input,
        #             "created_at": datetime.now().isoformat()
        #         },
        #         {
        #             "user_id": user_id,
        #             "user_name": user_name,
        #             "role": "assistant",
        #             "message": assistant_reply,
        #             "created_at": datetime.now().isoformat()
        #         }
        #     ]
        # ).execute()
        
        # if "<대화가 종료되었습니다.>" in assistant_reply:
        #     st.switch_page("pages/Result.py")