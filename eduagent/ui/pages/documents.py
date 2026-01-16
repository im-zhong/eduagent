"""Document management page for upload and listing."""
from __future__ import annotations

import humanize
import streamlit as st

from eduagent.ui.api_client import EduAgentAPIClient


def render(client: EduAgentAPIClient) -> None:
    """Render document management page.

    Args:
        client: API client instance
    """
    st.title("文档管理")
    st.write("上传和管理教材文档")

    # Create tabs for upload and list
    tab1, tab2 = st.tabs(["上传文档", "文档列表"])

    # Upload tab
    with tab1:
        st.subheader("上传新文档")
        st.write("支持上传 PDF、DOCX、TXT 等格式的教材文档")

        uploaded_file = st.file_uploader(
            "选择文档文件",
            type=["pdf", "doc", "docx", "txt", "md"],
            help="支持 PDF、DOC、DOCX、TXT、Markdown 格式",
        )

        if uploaded_file is not None:
            # Display file info
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"文件名: {uploaded_file.name}")
            with col2:
                st.info(f"大小: {humanize.naturalsize(uploaded_file.size)}")

            if st.button("上传文档", type="primary"):
                with st.spinner("正在上传..."):
                    file_bytes = uploaded_file.read()
                    result = client.upload_document(uploaded_file.name, file_bytes)

                    if "error" in result:
                        st.error(f"上传失败: {result['error']}")
                    else:
                        st.success("文档上传成功！")
                        st.json(result)

    # List tab
    with tab2:
        st.subheader("已上传文档")

        if st.button("刷新列表"):
            st.rerun()

        result = client.list_documents()

        if "error" in result:
            st.error(f"获取文档列表失败: {result['error']}")
        elif isinstance(result, list):
            documents = result
            if not documents:
                st.info("暂无文档，请先上传文档")
            else:
                # Display documents in a table
                for doc in documents:
                    with st.expander(
                        f"{doc.get('filename', 'unknown')} (ID: {doc.get('id', 'N/A')})"
                    ):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("文件名", doc.get("filename", "unknown"))
                        with col2:
                            st.metric(
                                "大小",
                                humanize.naturalsize(doc.get("file_size", 0)),
                            )
                        with col3:
                            st.metric(
                                "类型", doc.get("content_type", "unknown")
                            )

                        st.write(f"**创建时间:** {doc.get('created_at', 'unknown')}")
                        st.write(f"**更新时间:** {doc.get('updated_at', 'unknown')}")
        else:
            st.warning("未知的响应格式")
            st.json(result)
