from __future__ import annotations

import streamlit as st

from eduagent.ui.api_client import EduAgentAPIClient


def render(client: EduAgentAPIClient) -> None:
    st.title("EduAgent 运维控制台")
    st.write("管理解析任务、运行 LangGraph 流水线，并通过安全 API 协调出题与评估。")
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
        "2. 可选使用 **工作流运行** 查看同步结果\n"
        "3. 在 **异步流水线** 编排 Celery 任务\n"
        "4. 在 **评分工作台** 验证题目质量\n"
        "5. 通过 **数据监控** 观察整体指标"
    )
