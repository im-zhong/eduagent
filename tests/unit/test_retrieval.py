import pytest
from unittest.mock import MagicMock, patch, ANY, call
from langchain_core.documents import Document
from langchain_core.messages import AIMessage

# --- 重要 ---
# 请确保将您的原始脚本保存为 'rag_pipeline.py'，并放在同一目录下
# 这样这个测试文件才能正常工作。

# 我们在顶层 mock (模拟) 配置加载, 这会在测试运行前执行。
# 这可以防止真实脚本在测试环境中因缺少配置而抛出 OSError。
# 我们创建一个假的 settings 对象, 模块将加载这个假对象。
fake_settings = MagicMock()
fake_settings.llm.api_key = "FAKE_API_KEY"
fake_settings.pg_vector.connection_string = "postgresql://fake:fake@localhost:5432/fakedb"
fake_settings.pg_vector.collection_name = "fake_collection"
fake_settings.llm.model_name = "fake-glm-model"
fake_settings.llm.embedding_model_name = "fake-embedding-model"

# 我们使用 patch() 来替换 '__init__.py' 模块 *内部* 的 'new_settings' 函数。
patcher = patch('rag_pipeline.new_settings', return_value=fake_settings)
patcher.start()


# --- 测试 setup_vector_store ---

@patch('rag_pipeline.PGVector')
@patch('rag_pipeline.ZhipuAIEmbeddings')
def test_setup_vector_store_when_empty(MockZhipuAIEmbeddings, MockPGVector):
    """
    测试 setup_vector_store 在 PGVector 集合为空时, 是否能正确添加文档。
    """
    # 1. 设置 Mock
    mock_embed_instance = MagicMock()
    MockZhipuAIEmbeddings.return_value = mock_embed_instance
    
    mock_store_instance = MagicMock()
    # 模拟一个空集合: get() 返回空的 'ids'
    mock_store_instance.get.return_value = {"ids": []}
    MockPGVector.return_value = mock_store_instance
    
    test_texts = ["文档1", "文档2"]

    # 2. 调用函数
    vector_store = rag_pipeline.setup_vector_store(texts=test_texts)

    # 3. 断言
    # 检查 ZhipuAIEmbeddings 是否被正确初始化
    MockZhipuAIEmbeddings.assert_called_once_with(
        model=fake_settings.llm.embedding_model_name,
        api_key=fake_settings.llm.api_key
    )
    
    # 检查 PGVector 是否被正确初始化
    MockPGVector.assert_called_once_with(
        embeddings=mock_embed_instance,
        collection_name=fake_settings.pg_vector.collection_name,
        connection=fake_settings.pg_vector.connection_string,
        use_jsonb=True
    )
    
    # 检查我们是否正确地检查了集合是否为空
    mock_store_instance.get.assert_called_once_with(limit=1)
    
    # 检查文档是否被添加
    mock_store_instance.add_documents.assert_called_once()
    # 验证被添加的 *内容*
    call_args = mock_store_instance.add_documents.call_args[0][0]
    assert isinstance(call_args, list)
    assert len(call_args) == 2
    assert call_args[0].page_content == "文档1"
    assert call_args[1].page_content == "文档2"
    assert isinstance(call_args[0], Document)
    
    # 检查是否返回了正确的 vector store 实例
    assert vector_store == mock_store_instance

@patch('rag_pipeline.PGVector')
@patch('rag_pipeline.ZhipuAIEmbeddings')
def test_setup_vector_store_when_existing(MockZhipuAIEmbeddings, MockPGVector):
    """
    测试 setup_vector_store 在 PGVector 集合已存在数据时, 是否能正确 *跳过* 添加文档。
    """
    # 1. 设置 Mock
    mock_embed_instance = MagicMock()
    MockZhipuAIEmbeddings.return_value = mock_embed_instance
    
    mock_store_instance = MagicMock()
    # 模拟一个 *已存在的* 集合
    mock_store_instance.get.return_value = {"ids": ["existing-id-123"]}
    MockPGVector.return_value = mock_store_instance
    
    test_texts = ["文档1", "文档2"]

    # 2. 调用函数
    vector_store = rag_pipeline.setup_vector_store(texts=test_texts)

    # 3. 断言
    # 检查存储的初始化是否仍然发生
    MockZhipuAIEmbeddings.assert_called_once()
    MockPGVector.assert_called_once()
    
    # 检查我们是否正确地检查了集合是否为空
    mock_store_instance.get.assert_called_once_with(limit=1)
    
    # *主要断言*: 检查文档 *没有* 被添加
    mock_store_instance.add_documents.assert_not_called()
    
    # 检查是否返回了正确的 vector store 实例
    assert vector_store == mock_store_instance


# --- 测试 simple_rag_retrieval ---

@patch('rag_pipeline.ChatZhipuAI')
def test_simple_rag_retrieval(MockChatZhipuAI):
    """
    测试整个 RAG 链的逻辑, 仅 mock LLM 和 vector store 的 retriever。
    """
    # 1. 设置 Mock
    
    # 模拟 LLM
    mock_llm_instance = MagicMock()
    # LLM 的 'invoke' 方法返回一个消息对象
    final_ai_response = "基于上下文的模拟AI响应。"
    mock_ai_message = AIMessage(content=final_ai_response)
    mock_llm_instance.invoke.return_value = mock_ai_message
    MockChatZhipuAI.return_value = mock_llm_instance
    
    # 模拟 Vector Store 及其 Retriever
    mock_store = MagicMock(spec=rag_pipeline.PGVector)
    mock_retriever = MagicMock()
    # retriever (它是一个 runnable) 会被 query 'invoke'
    retrieved_docs = [Document(page_content="这是检索到的上下文。")]
    mock_retriever.invoke.return_value = retrieved_docs
    mock_store.as_retriever.return_value = mock_retriever
    
    query = "上下文是什么？"

    # 2. 调用函数
    # 我们传入模拟的 vector store
    result = rag_pipeline.simple_rag_retrieval(query, mock_store)

    # 3. 断言
    
    # 检查最终输出是否为来自 AI 的字符串内容
    assert result == final_ai_response
    
    # 检查 LLM 是否被正确初始化
    MockChatZhipuAI.assert_called_once_with(
        model=fake_settings.llm.model_name,
        temperature=0.1,
        api_key=fake_settings.llm.api_key
    )
    
    # 检查 retriever 是否被正确创建
    mock_store.as_retriever.assert_called_once_with(search_kwargs={"k": 3})
    
    # 检查 retriever 是否被用户的 query 调用
    mock_retriever.invoke.assert_called_once_with(query)
    
    # 检查 LLM 是否被正确格式化的 prompt 调用
    mock_llm_instance.invoke.assert_called_once()
    # 获取传递给 LLM 的 prompt 对象
    prompt_passed_to_llm = mock_llm_instance.invoke.call_args[0][0]
    prompt_as_string = str(prompt_passed_to_llm)
    
    # 验证 prompt 包含了所有关键部分
    assert "你是一个专业的问答助手" in prompt_as_string
    assert "Context:" in prompt_as_string
    # 检查我们 *检索到的文档* 是否在上下文中
    assert "这是检索到的上下文。" in prompt_as_string
    assert "Question: 上下文是什么？" in prompt_as_string


# 所有测试完成后停止 patching
patcher.stop()