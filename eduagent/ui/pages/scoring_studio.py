# from __future__ import annotations

# import json
# from typing import Any, cast

# import streamlit as st

# from eduagent.ui import common
# from eduagent.ui.api_client import EduAgentAPIClient


# def render(client: EduAgentAPIClient) -> None:
#     st.title("评分工作台")
#     quiz_job_id = st.text_input("需要评分的测验任务 ID")
#     questions = common.json_text_area("题目 JSON", "score_questions")
#     rules_text = st.text_area(
#         "可选规则 JSON",
#         height=120,
#         placeholder='{"allow_distractors": true}',
#     )
#     rules: dict[str, Any] | None = None
#     if rules_text.strip():
#         try:
#             parsed = json.loads(rules_text)
#             if isinstance(parsed, dict):
#                 rules = cast(dict[str, Any], parsed)
#             else:
#                 st.warning("规则 JSON 需要是对象/字典")
#         except json.JSONDecodeError as exc:
#             st.warning(f"规则 JSON 无效: {exc}")
#     if st.button("开始评分") and quiz_job_id and questions:
#         with st.spinner("正在请求评分任务..."):
#             response = client.request_quiz_scoring(quiz_job_id, questions, rules)
#         st.json(response)
