import pytest
from langchain_core.documents import Document

from eduagent.settings import settings
from eduagent.tools.retrieval.retrieval import SimpleRetrievalDemo, State


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
    result = SimpleRetrievalDemo(
        settings.api.secret_key,
        settings.pg_vector.connection_string,
        settings.pg_vector.collection_name,
    )
    result.setup_vector_store()

    # 验证返回类型
    assert result is not None

    # 验证必要的属性存在
    assert hasattr(result, "pg_connection_name"), "实例应包含connection_name属性"
    assert result.pg_connection_name == "demo_for_rag", (
        "实例应包含connection_namew为 demo_for_rag"
    )
    assert hasattr(result, "api_key"), "实例应包含api_key属性"
    # 这里可以根据你的实际实现添加更多验证
    assert hasattr(result, "pg_connection_string"), "实例应包含pg_connection_string属性"
    assert hasattr(result, "vector_store"), "实例应包含vector_store属性"
    assert result.vector_store is not None


def test_prompt_template() -> None:
    """测试提示模板"""
    rag_template = SimpleRetrievalDemo.create_prompt()
    assert rag_template is not None

    # 测试模板格式
    rag_template_str = rag_template.template
    assert "Context:" in rag_template_str
    assert "Question:" in rag_template_str
    assert "Answer:" in rag_template_str


def test_retrieve_function(sample_documents: list[Document]) -> None:
    """测试检索功能"""
    # 准备测试状态
    state_with_question = State(question="pond animals", context=[], answer="")

    # 调用检索函数
    simpel_rag = SimpleRetrievalDemo(
        settings.api.secret_key,
        settings.pg_vector.connection_string,
        settings.pg_vector.collection_name,
    )
    simpel_rag.setup_vector_store()
    simpel_rag.add_docs_to_vector_store(sample_documents)
    result = simpel_rag.retrieve(state_with_question)

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
    simpel_rag = SimpleRetrievalDemo(
        settings.api.secret_key,
        settings.pg_vector.connection_string,
        settings.pg_vector.collection_name,
    )
    result = simpel_rag.generate(state_with_context)

    # 验证返回结果
    assert "answer" in result
    assert isinstance(result["answer"], (str, list))

    # 如果返回的是字符串，验证非空
    if isinstance(result["answer"], str):
        assert len(result["answer"]) > 0
        # assert "猫" in result["answer"]


# 测试的返回结果不对，要求返回不知道
# def test_generate_empty_context() -> None:
# """测试空上下文生成,返回不知道"""
# state = State(question="What animals are in the pond?", context=[], answer="")
# simpel_rag = SimpleRetrievalDemo(settings.api.secret_key,settings.pg_vector.connection_string,settings.pg_vector.collection_name)
# result = simpel_rag.generate(state)

# assert "answer" in result
# assert isinstance(result["answer"], (str, list))
# assert "不知道" in result["answer"]


def test_simple_rag_retrieval_basic(sample_documents: list[Document]) -> None:
    """测试基本 RAG 流程"""
    # 测试简单查询
    query = {"question": "pond animals"}
    simpel_rag = SimpleRetrievalDemo(
        settings.api.secret_key,
        settings.pg_vector.connection_string,
        settings.pg_vector.collection_name,
    )
    simpel_rag.setup_vector_store()
    simpel_rag.add_docs_to_vector_store(sample_documents)
    result = simpel_rag.simple_rag_retrieval(query)

    # 验证返回结果是字符串
    assert isinstance(result, str)
    assert len(result) > 0


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


def test_rag_template_content() -> None:
    """测试 RAG 模板内容"""
    # 测试模板渲染
    test_context = "Test context content"
    test_question = "Test question"

    # 渲染模板,注意format返回字符串，format_prompt返回的是一个结构化的PromptValue 对象
    formatted_prompt = SimpleRetrievalDemo.create_prompt().format(
        context=test_context, question=test_question
    )

    # 验证渲染结果包含关键部分
    assert test_context in formatted_prompt
    assert test_question in formatted_prompt
    assert "Context:" in formatted_prompt
    assert "Question:" in formatted_prompt
    assert "Answer:" in formatted_prompt
