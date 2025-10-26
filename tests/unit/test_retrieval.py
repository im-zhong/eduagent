import pytest
from langchain_core.documents import Document
from langchain_postgres import PGVector

from eduagent.tools.retrieval.retrieval import (
    State,
    embeddings,
    generate,
    llm,
    prompt,
    retrieve,
    setup_vector_store,
    simple_rag_retrieval,
)


@pytest.fixture
def sample_documents() -> list[Document]:
    """提供测试文档"""
    return [
        Document(
            page_content="there are cats in the pond",
            metadata={"id": 1, "location": "pond", "topic": "animals"},
        ),
        Document(
            page_content="ducks are also found in the pond",
            metadata={"id": 2, "location": "pond", "topic": "animals"},
        ),
    ]


def test_setup_vector_store() -> None:
    """测试向量数据库设置"""
    # 测试函数是否正常返回 PGVector 实例
    result: PGVector = setup_vector_store()

    # 验证返回类型
    assert result is not None
    assert isinstance(result, PGVector), (
        f"Expected PGVector instance, got {type(result)}"
    )

    # 验证必要的属性存在
    assert hasattr(result, "collection_name"), "PGVector实例应包含collection_name属性"
    assert result.collection_name == "demo_for_rag", (
        "GVector实例应包含collection_namew为 demo_for_rag"
    )
    assert hasattr(result, "embedding_function"), (
        "PGVector实例应包含embedding_function属性"
    )
    # 这里可以根据你的实际实现添加更多验证


def test_embeddings_initialization() -> None:
    """测试嵌入模型初始化"""
    assert embeddings is not None
    # 测试是否含以下方法
    assert hasattr(embeddings, "embed_documents")
    assert hasattr(embeddings, "embed_query")
    # 确保嵌入函数能正常工作，并返回一个非空列表（即向量）。
    vector = embeddings.embed_query("test query")
    assert isinstance(vector, list)
    assert len(vector) > 1


def test_llm_initialization() -> None:
    """测试 LLM 初始化"""
    assert llm is not None
    assert hasattr(llm, "invoke")
    # 测试是否能够成功生成响应
    response = llm.invoke("Hello, how are you?")
    assert isinstance(response.content, str)  # type:ignore
    assert len(response.content) > 0


def test_prompt_template() -> None:
    """测试提示模板"""
    assert prompt is not None

    # 测试模板格式
    rag_template = prompt.template
    assert "Context:" in rag_template
    assert "Question:" in rag_template
    assert "Answer:" in rag_template


def test_retrieve_function() -> None:
    """测试检索功能"""
    # 准备测试状态
    state_with_question = State(question="pond animals", context=[], answer="")

    # 调用检索函数
    result = retrieve(state_with_question)

    # 验证返回结果context是list类型
    assert "context" in result
    assert isinstance(result["context"], list)

    # 验证返回的文档都是 Document 类型
    for doc in result["context"]:
        assert isinstance(doc, Document)


def test_generate_function(sample_documents: list[Document]) -> None:
    """测试生成功能"""
    # 准备带有上下文的测试状态
    state_with_context = State(
        question="What animals are in the pond?", context=sample_documents, answer=""
    )

    # 调用生成函数
    result = generate(state_with_context)

    # 验证返回结果
    assert "answer" in result
    assert isinstance(result["answer"], (str, list))

    # 如果返回的是字符串，验证非空
    if isinstance(result["answer"], str):
        assert len(result["answer"]) > 0
        # assert "猫" in result["answer"]


def test_generate_empty_context() -> None:
    """测试空上下文生成,返回不知道"""
    state = State(question="What animals are in the pond?", context=[], answer="")

    result = generate(state)

    assert "answer" in result
    assert isinstance(result["answer"], (str, list))
    # assert "不知道" in result["answer"]


def test_simple_rag_retrieval_basic() -> None:
    """测试基本 RAG 流程"""
    # 测试简单查询
    query = {"question": "pond animals"}

    result = simple_rag_retrieval(query)

    # 验证返回结果是字符串
    assert isinstance(result, str)
    assert len(result) > 0


def test_simple_rag_retrieval_empty_query() -> None:
    """测试空查询的 RAG 流程"""
    empty_query = {"question": ""}

    result = simple_rag_retrieval(empty_query)

    assert isinstance(result, str)


def test_state_typeddict_structure() -> None:
    """测试 State TypedDict 结构"""
    # 测试正确的状态结构
    valid_state = State(
        question="test question",
        context=[Document(page_content="test content")],
        answer="test answer",
    )

    assert valid_state["question"] == "test question"
    assert len(valid_state["context"]) == 1
    assert valid_state["answer"] == "test answer"


def test_document_structure() -> None:
    """测试 Document 结构"""
    doc = Document(page_content="test content", metadata={"id": 1, "source": "test"})

    assert doc.page_content == "test content"
    assert "id" in doc.metadata  # type: ignore
    assert doc.metadata["id"] == 1  # type: ignore


def test_rag_template_content() -> None:
    """测试 RAG 模板内容"""
    # 测试模板渲染
    test_context = "Test context content"
    test_question = "Test question"

    # 渲染模板,注意format返回字符串，format_prompt返回的是一个结构化的PromptValue 对象
    formatted_prompt = prompt.format(context=test_context, question=test_question)

    # 验证渲染结果包含关键部分
    assert test_context in formatted_prompt
    assert test_question in formatted_prompt
    assert "Context:" in formatted_prompt
    assert "Question:" in formatted_prompt
    assert "Answer:" in formatted_prompt
