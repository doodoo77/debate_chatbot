import streamlit as st
from openai import OpenAI
import os 
from matplotlib import font_manager as fm
from prompts import stage0, stage1, stage2
from langchain.prompts import PromptTemplate
import time
# ----------------------------------------------------------------------------------------------------
# Page Config
# ----------------------------------------------------------------------------------------------------

st.set_page_config(page_title = "AI 토론 튜터")

title = "AI 토론 튜터와 토론 연습을 해보자"
# description = "토론주제에 대해서 챗봇과 토론 연습을 해보자"

fpath = os.path.join(os.getcwd(), "./NanumGothic-ExtraBold.ttf")
prop= fm.FontProperties(fname=fpath)

with st.container(border=True):
    st.markdown(
        f"""<h2 style='text-align: center; color: black; font-size: 1.7rem; fontpropertise: prop'>{title}</h2>""", unsafe_allow_html=True)
        
    st.image('img.PNG')


client = OpenAI(
    api_key=st.secrets['OPENAI_API_KEY'], 
    organization=st.secrets['OPENAI_ORGANIZATION']
)

# ----------------------------------------------------------------------------------------------------
# Prompt Template
# ----------------------------------------------------------------------------------------------------
template = """
[임무소개]
: 너는 이제 학생들에게 토론을 제공해줄 토론파트너 역할을 할거야. 
: 너는 (전체 토론 절차) 중에 내가 명시한 (특정 토론 절차)로만 토론을 진행하면 돼. 
: 주의할 점은. 너가 대사를 하고 나서 학생의 답변이 올 때까지 기다려야한다는 점이야 

[토론주제]
: 너가 학생과 토론하게 될 토론 주제는 “알고리즘의 추천이 우리의 삶을 풍요롭게 해준다.”야.

(전체 토론 절차)
: 먼저 전체적인 토론절차에 대해서 소개해줄게. 
0. Reading material

1. Constructive debate 
1.1. 이 단계에서는 너는 학생들의 주장에 해당하는 근거를 함께 세울거야.
1.2. 그리고 나서 해당 근거를 지지하는 실제 사례를 추가할거야.

2. Rebuttal debate
2.1. 이제 너는 학생의 입장(반대 혹은 찬성)과 다른 입장에서 근거를 제시하고, 학생이 너의 근거에 대해서 반론을 제기하면, 너는 재반론을 해.
2.2. 반대로 너가 학생의 근거에 대해 반론을 제기하고, 학생이 이에 대해서 재반론하는 단계를 가져.

(특정 토론 절차)
: 이제 너가 학생에게 제공해야하는 토론 절차는 아래와 같아
주의! 내가 해준 대사를 변경하지 말고 그대로 읽어야 해
{debate_stage}
"""

prompt_template = PromptTemplate(
    input_variables=["debate_stage"],
    template=template)

debate_stage_0 = prompt_template.format(debate_stage=stage0)
debate_stage_1 = prompt_template.format(debate_stage=stage1)
debate_stage_2 = prompt_template.format(debate_stage=stage2)



# ----------------------------------------------------------------------------------------------------
# Session State
# ----------------------------------------------------------------------------------------------------
if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = "gpt-4o"
    
# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": debate_stage_0},
        {"role": "assistant", "content": "안녕! 나는 오늘 너와 토론을 진행할 토론 파트너야. 만나서 반가워."}
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
    
    if "본격적인 토론을 시작할게" in response:
        st.session_state.messages.append({"role": "system", "content": debate_stage_1})
    elif "반론 및 재반론 연습을 시작해보자" in response:
        st.session_state.messages.append({"role": "system", "content": debate_stage_2})
                
    if "토론이 종료되었어" in response:
        time.sleep(5)
        st.switch_page("pages/Evaluation.py")
