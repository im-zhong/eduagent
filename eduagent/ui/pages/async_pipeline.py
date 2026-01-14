# from __future__ import annotations

# import json

# import streamlit as st

# from eduagent.ui import common
# from eduagent.ui.api_client import EduAgentAPIClient


# def render(client: EduAgentAPIClient) -> None:
#     st.title("异步测验流水线")
#     st.subheader("生成任务")
#     ingestion_job = st.text_input("解析任务 ID", key="async_ingestion")
#     col1, col2 = st.columns(2)
#     subject = col1.text_input("学科覆盖", "")
#     query = col2.text_input("额外上下文/说明", "")
#     rules_default = {
#         "total_questions": 5,
#         "include_explanations": True,
#         "allow_distractors": True,
#     }
#     rules_text = st.text_area(
#         "测验规则（JSON）",
#         value=json.dumps(rules_default, indent=2),
#         height=160,
#     )
#     if st.button("提交生成任务") and ingestion_job:
#         try:
#             quiz_rules = json.loads(rules_text)
#         except json.JSONDecodeError as exc:
#             st.error(f"JSON 无效: {exc}")
#         else:
#             with st.spinner("正在提交生成任务..."):
#                 result = client.request_quiz_generation(
#                     ingestion_job,
#                     subject or None,
#                     query or None,
#                     quiz_rules,
#                 )
#             st.json(result)

#     st.markdown("---")
#     st.subheader("评估任务")
#     quiz_job_id = st.text_input("测验任务 ID", key="eval_quiz_job")
#     answers = common.json_text_area(
#         "答题卡（JSON 列表 {question_id, answer}）", "eval_answers"
#     )
#     if st.button("提交评估任务") and quiz_job_id and answers:
#         with st.spinner("正在提交评估任务..."):
#             response = client.request_quiz_evaluation(quiz_job_id, answers)
#         st.json(response)

#     st.markdown("---")
#     st.subheader("任务监控")
#     monitor_id = st.text_input("要监控的任务 ID")
#     if st.button("刷新状态") and monitor_id:
#         detail = client.get_quiz_job(monitor_id)
#         st.json(detail)
