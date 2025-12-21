"""
Operations console for EduAgent.
Provides pages for ingestion, workflow execution, and analytics using the new quiz APIs.
"""

from __future__ import annotations

from typing import cast

import streamlit as st

from eduagent.defs import defs
from eduagent.ui import common
from eduagent.ui.api_client import EduAgentAPIClient
from eduagent.ui.pages import (
    agent_workflow,
    analytics_monitor,
    async_pipeline,
    ingestion_lab,
    overview,
    rag_chat,
    scoring_studio,
    workflow_runner,
)

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
    client = st.session_state.get("api_client")
    if isinstance(client, EduAgentAPIClient):
        client.configure(base_url, token)
        return client
    st.session_state.api_client = EduAgentAPIClient(base_url, token)
    return st.session_state.api_client


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


PAGE_HANDLERS = {
    "总览": overview.render,
    "数据解析": ingestion_lab.render,
    "工作流运行": workflow_runner.render,
    "ReAct 代理": agent_workflow.render,
    "RAG 对话": rag_chat.render,
    "异步流水线": async_pipeline.render,
    "评分工作台": scoring_studio.render,
    "数据监控": analytics_monitor.render,
}


def main() -> None:
    st.set_page_config(
        page_title="EduAgent 运维控制台",
        page_icon=defs.ui.PAGE_ICON,
        layout="wide",
    )
    _bootstrap_session_state()
    st.sidebar.title("EduAgent 控制台")
    client = _load_api_client()
    _configure_sidebar(client)
    st.sidebar.markdown("---")

    tabs = st.tabs(defs.ui.TEACHER_NAV_OPTIONS)
    for tab, page_name in zip(tabs, defs.ui.TEACHER_NAV_OPTIONS):
        handler = PAGE_HANDLERS.get(page_name, overview.render)
        with tab:
            handler(client)


if __name__ == "__main__":
    main()
