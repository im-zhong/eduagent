from __future__ import annotations

import streamlit as st

from eduagent.ui.api_client import EduAgentAPIClient


def render(client: EduAgentAPIClient) -> None:
    st.title("出题智能体 Demo")
    # st.write("管理解析任务、运行 LangGraph 流水线，并通过安全 API 协调出题与评估。")
    if st.button("检查 API 健康状态"):
        with st.spinner("正在联系 API..."):
            result = client.health_check()
            if "error" in result:
                st.error(result["error"])
            else:
                st.success("API 正常")
                st.json(result)

    st.subheader("工作流程")
    st.markdown(
        "1. 在 **数据解析** 上传教材或文档\n"
        "2. 选择某本教材，使用出题智能体在上面进行出题\n"
    )
