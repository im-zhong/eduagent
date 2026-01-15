"""Retrieval playground for chunk indexing and search."""
from __future__ import annotations

import streamlit as st

from eduagent.ui.api_client import EduAgentAPIClient


def _render_index_section(client: EduAgentAPIClient) -> None:
    st.subheader("向量索引")
    st.caption("需要先完成文档解析（生成 chunks）再执行索引。")
    doc_id = st.number_input("文档 ID", min_value=1, step=1, value=1)
    if st.button("索引文档 chunks", type="primary"):
        with st.spinner("正在索引..."):
            result = client.index_chunks(doc_id)
        if "error" in result:
            st.error(f"索引失败: {result['error']}")
        else:
            st.success("索引完成")
            st.json(result)


def _render_search_section(client: EduAgentAPIClient) -> None:
    st.subheader("检索测试")
    query = st.text_input("检索问题", value="")
    col1, col2 = st.columns(2)
    with col1:
        mode = st.selectbox("检索模式", ["sparse", "dense", "hybrid"])
    with col2:
        top_k = st.slider("返回数量", min_value=1, max_value=20, value=5)

    if st.button("开始检索"):
        if not query.strip():
            st.warning("请输入检索问题。")
            return
        with st.spinner("正在检索..."):
            result = client.search_chunks(query=query, top_k=top_k, mode=mode)
        if "error" in result:
            st.error(f"检索失败: {result['error']}")
            return

        hits = result.get("hits", [])
        if not hits:
            st.info("未找到相关内容。")
            return

        st.write(f"命中数量: {len(hits)}")
        for idx, hit in enumerate(hits, start=1):
            with st.expander(f"#{idx} | score: {hit.get('score', 0):.4f}"):
                st.write(f"doc_id: {hit.get('doc_id')}")
                st.write(f"chunk_id: {hit.get('chunk_id')}")
                st.write(hit.get("text", ""))


def render(client: EduAgentAPIClient) -> None:
    """Render retrieval page for Milvus indexing and search."""
    st.title("检索与索引")
    _render_index_section(client)
    st.divider()
    _render_search_section(client)
