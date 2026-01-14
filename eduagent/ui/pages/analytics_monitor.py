# from __future__ import annotations

# import streamlit as st

# from eduagent.defs import defs
# from eduagent.ui.api_client import EduAgentAPIClient


# def render(client: EduAgentAPIClient) -> None:
#     st.title("数据监控")
#     tab1, tab2, tab3 = st.tabs(["学生表现", "班级分析", "错题分析"])
#     time_period_labels = {
#         "7 days": "近 7 天",
#         "30 days": "近 30 天",
#         "90 days": "近 90 天",
#         "All time": "全部时间",
#     }
#     subject_labels = {
#         "Math": "数学",
#         "Science": "科学",
#         "History": "历史",
#         "Language": "语言",
#         "Physics": "物理",
#         "Chemistry": "化学",
#         "Biology": "生物",
#         "Computer Science": "计算机科学",
#     }
#     with tab1:
#         student_id = st.text_input("学生 ID")
#         time_period = st.selectbox(
#             "时间范围",
#             defs.ui.TIME_PERIODS,
#             format_func=lambda value: time_period_labels.get(value, value),
#         )
#         if st.button("获取学生分析") and student_id:
#             result = client.get_performance_analytics(student_id, time_period)
#             st.json(result)
#     with tab2:
#         class_id = st.text_input("班级 ID")
#         time_period = st.selectbox(
#             "班级时间范围",
#             defs.ui.TIME_PERIODS,
#             key="class_period",
#             format_func=lambda value: time_period_labels.get(value, value),
#         )
#         if st.button("获取班级分析") and class_id:
#             result = client.get_class_analytics(class_id, time_period)
#             st.json(result)
#     with tab3:
#         student = st.text_input("学生（错题分析）")
#         subject = st.selectbox(
#             "学科",
#             defs.ui.SUBJECTS,
#             format_func=lambda value: subject_labels.get(value, value),
#         )
#         if st.button("分析错题") and student:
#             result = client.analyze_mistakes(student, subject)
#             st.json(result)
