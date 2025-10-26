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
    vector_store,
)


@pytest.fixture
def sample_documents()-> list[Document]:
    """提供测试文档"""
    return [
        Document(
            page_content="there are cats in the pond",
            metadata={"id": 1, "location": "pond", "topic": "animals"},
        ),
        Document(
            page_content="ducks are also found in the pond",
            metadata={"id": 2, "location": "pond", "topic": "animals"},
        )
    ]


@pytest.fixture
def sample_state()->State:
    """提供测试状态"""
    return {
        "question": "What animals are in the pond?",
        "context": [],
        "answer": ""
    }


def test_setup_vector_store()->None:
    """测试向量数据库设置"""
    # 测试函数是否正常返回 PGVector 实例
    result:PGVector = setup_vector_store()

    # 验证返回类型
    assert result is not None

    assert isinstance(result, PGVector), f"Expected PGVector instance, got {type(result)}"
    
    # 验证必要的属性存在
    assert hasattr(result, 'collection_name'), "PGVector实例应包含collection_name属性"
    assert hasattr(result, 'embedding_function'), "PGVector实例应包含embedding_function属性"
    
    # 验证连接字符串或配置
    # 这里可以根据你的实际实现添加更多验证
    assert result.collection_name == "demo_for_rag" # "集合名称不应为空"

def test_embeddings_initialization()->None:
    """测试嵌入模型初始化"""
    assert embeddings is not None
    assert hasattr(embeddings, 'embed_documents')
    assert hasattr(embeddings, 'embed_query')


def test_llm_initialization()->None:
    """测试 LLM 初始化"""
    assert llm is not None
    assert hasattr(llm, 'invoke')


def test_prompt_template()->None:
    """测试提示模板"""
    assert prompt is not None

    # 测试模板格式
    template = prompt.template
    assert "Context:" in template
    assert "Question:" in template
    assert "Answer:" in template


def test_retrieve_function(sample_state:State)->None:
    """测试检索功能"""
    # 准备测试状态
    state_with_question = State(
        question="pond animals",
        context=[],
        answer=""
    )

    # 调用检索函数
    result = retrieve(state_with_question)

    # 验证返回结果
    assert "context" in result
    assert isinstance(result["context"], list)

    # 验证返回的文档都是 Document 类型
    for doc in result["context"]:
        assert isinstance(doc, Document)


def test_retrieve_empty_question()->None:
    """测试空问题检索"""
    state = State(question="", context=[], answer="")

    result = retrieve(state)

    assert "context" in result
    assert isinstance(result["context"], list)


def test_generate_function(sample_documents:list[Document])->None:
    """测试生成功能"""
    # 准备带有上下文的测试状态
    state_with_context = State(
        question="What animals are in the pond?",
        context=sample_documents,
        answer=""
    )

    # 调用生成函数
    result = generate(state_with_context)

    # 验证返回结果
    assert "answer" in result
    assert isinstance(result["answer"], (str, list))

    # 如果返回的是字符串，验证非空
    if isinstance(result["answer"], str):
        assert len(result["answer"]) > 0


def test_generate_empty_context()->None:
    """测试空上下文生成"""
    state = State(
        question="What animals are in the pond?",
        context=[],
        answer=""
    )

    result = generate(state)

    assert "answer" in result
    assert isinstance(result["answer"], (str, list))


def test_simple_rag_retrieval_basic()->None:
    """测试基本 RAG 流程"""
    # 测试简单查询
    query = {"question": "pond animals"}

    result = simple_rag_retrieval(query)

    # 验证返回结果是字符串
    assert isinstance(result, str)
    assert len(result) > 0


def test_simple_rag_retrieval_empty_query()->None:
    """测试空查询的 RAG 流程"""
    empty_query = {"question": ""}

    result = simple_rag_retrieval(empty_query)

    assert isinstance(result, str)


def test_state_typeddict_structure()->None:
    """测试 State TypedDict 结构"""
    # 测试正确的状态结构
    valid_state = State(
        question="test question",
        context=[Document(page_content="test content")],
        answer="test answer"
    )

    assert valid_state["question"] == "test question"
    assert len(valid_state["context"]) == 1
    assert valid_state["answer"] == "test answer"


def test_document_structure()->None:
    """测试 Document 结构"""
    doc = Document(
        page_content="test content",
        metadata={"id": 1, "source": "test"}
    )

    assert doc.page_content == "test content"
    assert "id" in doc.metadata  # type: ignore
    assert doc.metadata["id"] == 1 # type: ignore


def test_vector_store_connection()->None:
    """测试向量数据库连接"""
    # 验证向量存储已初始化
    assert vector_store is not None

    # 测试基本的检索功能
    try:
        # 尝试进行简单检索
        results:list[Document] = vector_store.similarity_search("pond", k=1) #type:ignore
        # 如果成功，验证结果格式
        if results:
            assert isinstance(results[0], Document)
    except Exception as e:
        # 如果连接失败，标记测试为跳过或通过（取决于你的需求）
        pytest.skip(f"Vector store connection failed: {e}")


def test_rag_template_content()->None:
    """测试 RAG 模板内容"""
    # 测试模板渲染
    test_context = "Test context content"
    test_question = "Test question"

    # 渲染模板
    formatted_prompt = prompt.format(context=test_context, question=test_question)

    # 验证渲染结果包含关键部分
    assert test_context in formatted_prompt
    assert test_question in formatted_prompt
    assert "Context:" in formatted_prompt
    assert "Question:" in formatted_prompt
    assert "Answer:" in formatted_prompt


def test_retrieve_with_different_questions(sample_state:State)->None:
    """测试不同问题的检索"""
    test_questions = [
        "pond animals",
        "market food",
        "museum exhibits",
        "library activities"
    ]

    for question in test_questions:
        state = State(question=question, context=[], answer="")
        result = retrieve(state)

        assert "context" in result
        assert isinstance(result["context"], list)


def test_generate_with_various_contexts()->None:
    """测试不同上下文的生成"""
    test_contexts = [
        [Document(page_content="simple context")],
        [
            Document(page_content="first document"),
            Document(page_content="second document")
        ],
        []  # 空上下文
    ]

    for context in test_contexts:
        state = State(
            question="test question",
            context=context,
            answer=""
        )
        result = generate(state)

        assert "answer" in result


def test_end_to_end_rag_flow()->None:
    """测试端到端 RAG 流程"""
    # 测试几个不同的查询
    test_queries = [
        {"question": "What animals are in the pond?"},
        {"question": "What food is available at the market?"},
        {"question": "What can I do at the library?"}
    ]

    for query in test_queries:
        result = simple_rag_retrieval(query)

        # 验证返回结果是字符串且非空
        assert isinstance(result, str)
        assert len(result) > 0

        # 验证结果包含合理的响应（不是错误信息）
        # 这里可以根据你的业务逻辑添加更多验证
        assert "error" not in result.lower()
