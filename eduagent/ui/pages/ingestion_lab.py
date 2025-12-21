from __future__ import annotations

import streamlit as st

from eduagent.api.schemas import SubjectArea
from eduagent.defs import defs
from eduagent.ui.api_client import EduAgentAPIClient


def render(client: EduAgentAPIClient) -> None:
    st.title("数据摄取")
    st.subheader("上传教材或 DOCX")
    file = st.file_uploader("选择文件", type=["docx", "pdf"])
    grade_labels = {
        "Elementary": "小学",
        "Middle School": "初中",
        "High School": "高中",
        "College": "大学",
    }
    grade = st.selectbox(
        "年级",
        defs.ui.GRADE_LEVELS,
        format_func=lambda value: grade_labels.get(value, value),
    )
    st.caption(
        "学科标签由摄取流水线自动推断，初始存储为“general”。"
    )
    subject_value = SubjectArea.GENERAL.value
    if st.button("开始摄取") and file is not None:
        with st.spinner("正在上传至摄取流水线..."):
            result = client.upload_ingestion_document(
                file.name, file.getvalue(), subject_value, grade
            )
        if "error" in result:
            st.error(result["error"])
        else:
            st.success("任务已创建")
            st.json(result)

    st.markdown("---")
    st.subheader("查询任务状态")
    lookup_id = st.text_input("测验任务 ID")
    if st.button("获取任务详情") and lookup_id:
        with st.spinner("正在获取任务信息..."):
            detail = client.get_quiz_job(lookup_id)
        if "error" in detail:
            st.error(detail["error"])
        else:
            st.json(detail)
