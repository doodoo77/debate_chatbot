import streamlit as st
from result_dictionary import stressor_icons
from result_dictionary import symptoms_icons
from result_dictionary import coping_icons
from menu import menu
from dummy_data import df_sorted

########################################################################################
# SETUP

st.set_page_config(
    page_title = "고민모니",
    page_icon = "./images/logo.png"
)

# .streamlit/style.css 파일 열기
with open("./.streamlit/style.css") as css:
    # CSS 파일을 읽어와서 스타일 적용
    st.markdown(f'<style>{css.read()}</style>', unsafe_allow_html=True)

########################################################################################

st.title("이전 결과 확인")

# 탭을 사용할 경우 (간단한 탭 구현)
tabs = st.tabs(["점수 추이", "대화별 상세 내역"])

# 홈 탭
with tabs[0]:
    st.subheader("학업 스트레스 점수 추이")

    # 라인 차트 시각화
    st.line_chart(df_sorted, x="날짜", y="스트레스 점수")

    col1, col2, col3 = st.columns(3)
    with col2:
        main_button = st.button(label = "🏠   홈 화면으로 돌아가기", key=0)
        if main_button:
            st.switch_page("pages/Home.py")


# 리포트 탭
with tabs[1]:
    st.subheader("대화별 상세 내역 보기")

    for i in range(len(df_sorted)):
        # f-string 내부의 인용 부호 수정
        with st.expander(label=f"{df_sorted.loc[i, '날짜']} : {df_sorted.loc[i, '대화 주요 내용']}"):
            st.metric(label="학업 스트레스 총점", value= f"{df_sorted.loc[i, '스트레스 점수']:.2f}", )

            st.write("스트레스 원인:")
            st.write(f"- {df_sorted.loc[i, '스트레스 원인']} {stressor_icons.get(df_sorted.loc[i, '스트레스 원인'], '👌')}")
            st.write("스트레스 증상:")
            st.write(f"- {df_sorted.loc[i, '스트레스 증상']} {symptoms_icons.get(df_sorted.loc[i, '스트레스 증상'], '👌')}")
            st.write("스트레스 대처 전략:")
            st.write(f"- {df_sorted.loc[i, '스트레스 대처 전략']} {coping_icons.get(df_sorted.loc[i, '스트레스 대처 전략'], '👌')}")

    col1, col2, col3 = st.columns(3)
    with col2:
        main_button = st.button(label = "🏠   홈 화면으로 돌아가기", key=1)
        if main_button:
            st.switch_page("pages/Home.py")

menu()