"""
Operations console for EduAgent.
Provides pages for ingestion, workflow execution, and analytics using new quiz APIs.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import cast

import streamlit as st


# from eduagent.ui import common
from eduagent.ui.api_client import EduAgentAPIClient
from eduagent.ui.pages import (
    agent_chat,
    documents,
    retrieval,
    unified_chat,
    # agent_workflow,
    # analytics_monitor,
    # async_pipeline,
    # ingestion_lab,
    overview,
    # rag_chat,
    # scoring_studio,
    # workflow_runner,
)


# 这个东西不应该在这里，尽可能减少这种全局模块吧，我突然觉得非常的不合适
# 包括咱们之前考虑到的，settings模块也不会进入到每个模块的依赖里面了，其实背后的原理都是一样的
# 就是高内聚 低耦合！
class UIDefs:
    """UI-related constants and definitions"""

    # Page titles and icons
    TEACHER_DASHBOARD_TITLE = "EduAgent - Teacher Dashboard"
    STUDENT_DASHBOARD_TITLE = "EduAgent - Student Dashboard"
    PAGE_ICON = "📚"

    # Navigation options with page handlers
    TEACHER_PAGES: list[tuple[str, Callable[[EduAgentAPIClient], None]]] = [
        ("总览", overview.render),
        ("文档管理", documents.render),
        ("检索与索引", retrieval.render),
        ("统一对话", unified_chat.render),
        ("Agent 对话", agent_chat.render),
        # ("数据解析", ingestion_lab.render),
        # ("工作流运行", workflow_runner.render),
        # ("ReAct 代理", agent_workflow.render),
        # ("RAG 对话", rag_chat.render),
        # ("异步流水线", async_pipeline.render),
        # ("评分工作台", scoring_studio.render),
        # ("数据监控", analytics_monitor.render),
    ]

    TEACHER_NAV_OPTIONS: list[str] = [name for name, _ in TEACHER_PAGES]

    STUDENT_NAV_OPTIONS: list[str] = []

    # Subject options
    SUBJECTS: list[str] = [
        "Math",
        "Science",
        "History",
        "Language",
        "Physics",
        "Chemistry",
        "Biology",
        "Computer Science",
    ]

    # Grade levels
    GRADE_LEVELS: list[str] = [
        "Elementary",
        "Middle School",
        "High School",
        "College",
    ]

    # Question types
    QUESTION_TYPES: list[str] = [
        "Multiple Choice",
        "True/False",
        "Short Answer",
        "Essay",
        "Calculation",
        "Fill in Blank",
    ]

    # Difficulty levels
    DIFFICULTY_LEVELS: list[str] = ["Easy", "Medium", "Hard"]

    # Cognitive levels
    COGNITIVE_LEVELS: list[str] = [
        "Memory",
        "Understanding",
        "Application",
        "Analysis",
        "Evaluation",
        "Creation",
    ]

    # Time periods for analytics
    TIME_PERIODS: list[str] = ["7 days", "30 days", "90 days", "All time"]


uidefs = UIDefs()

DEFAULT_API_URL = "http://api.eduagent:8000"


def _load_service_jwt_from_config() -> str | None:
    """Return service JWT from Streamlit secrets/config if present."""
    secrets = getattr(st, "secrets", None)
    if not secrets:
        return None
    token = secrets.get("service_jwt")
    if isinstance(token, str) and token.strip():
        return token.strip()
    return None


def _bootstrap_session_state() -> None:
    """Initialize session defaults from config."""
    if not isinstance(st.session_state.get("service_jwt"), str):
        token = _load_service_jwt_from_config()
        if token:
            st.session_state.service_jwt = token
    api_url = st.session_state.get("api_base_url")
    if not isinstance(api_url, str) or not api_url.strip():
        st.session_state.api_base_url = DEFAULT_API_URL


def _load_api_client() -> EduAgentAPIClient:
    base_url = st.session_state.get("api_base_url")
    if not isinstance(base_url, str) or not base_url.strip():
        base_url = DEFAULT_API_URL
        st.session_state.api_base_url = base_url
    token = cast(str | None, st.session_state.get("service_jwt"))
    # Always create a fresh client to avoid stale cached instances.
    return EduAgentAPIClient(base_url, token)

    # if isinstance(client, EduAgentAPIClient):
    #     # Streamlit may cache an older client instance across code updates.
    #     if not hasattr(client, "health_check"):
    #         st.session_state.pop("api_client", None)
    #     else:
    #         client.configure(base_url, token)
    #         return client
    # st.session_state.api_client = EduAgentAPIClient(base_url, token)
    # return st.session_state.api_client


def _configure_sidebar(client: EduAgentAPIClient) -> None:
    st.sidebar.header("API 配置")
    stored_url = st.session_state.get("api_base_url") or client.base_url
    base_url = st.sidebar.text_input(
        "服务基础地址",
        value=stored_url,
    )
    token = cast(str | None, st.session_state.get("service_jwt"))
    if token:
        st.sidebar.caption("已从 Streamlit 配置加载服务 JWT。")
    else:
        st.sidebar.warning("未在 Streamlit 配置中找到服务 JWT。")
    if st.sidebar.button("应用配置"):
        effective_base = base_url or DEFAULT_API_URL
        st.session_state.api_base_url = effective_base
        client.configure(effective_base, token or None)
        st.sidebar.success("配置已更新。")


def main() -> None:
    st.set_page_config(
        page_title="出题智能体 Demo",
        page_icon=uidefs.PAGE_ICON,
        layout="wide",
    )
    _bootstrap_session_state()
    st.sidebar.title("出题智能体 Demo")
    client = _load_api_client()
    _configure_sidebar(client)
    st.sidebar.markdown("---")

    tabs = st.tabs(uidefs.TEACHER_NAV_OPTIONS)
    for tab, (_, handler) in zip(tabs, uidefs.TEACHER_PAGES):
        # https://docs.streamlit.io/develop/api-reference/layout/stabs
        # To add elements to the returned containers, you can use the with notation (preferred)
        # conditional render:
        # All content within every tab is computed and sent to the frontend, regardless of which tab is selected.
        # Tabs do not currently support conditional rendering.
        # If you have a slow-loading tab, consider using a widget like st.segmented_control to conditionally render content instead.
        with tab:
            # oooooo! 在这里执行函数就行了，和直接写streamlit代码是一样的
            # 所以用来封装streamlit代码的函数没有什么特别的，就是普通的函数里面放上streamlit代码就行了
            # 然后就只需要在st.tabs返回的tab里面with tab然后执行streamlit代码就ok了！
            handler(client)


if __name__ == "__main__":
    main()
