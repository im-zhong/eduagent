# TODO(G_shang_hui)
# take user input, retrieve relevant documents, and return them
# ref: https://python.langchain.com/docs/integrations/vectorstores/pgvector/


# from typing import List
# from dotenv import load_dotenv  # 导入加载配置的库
# --- ZhipuAI LangChain 集成 ---
from typing import Any

from langchain_community.chat_models import ChatZhipuAI
from langchain_community.embeddings import ZhipuAIEmbeddings

# --- 核心 LangChain 组件导入 ---
from langchain_core.documents import Document
from langchain_core.prompt_values import PromptValue
from langchain_core.prompts import PromptTemplate

# --- PGVector 导入 ---
from langchain_postgres.vectorstores import PGVector
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import START, StateGraph  # type: ignore
from typing_extensions import TypedDict

# 改成setting文件导入我的配置文件
# from eduagent.defs import defs
# from eduagent.settings import settings 单例

# # load_dotenv()  # 加载配置文件
# PG_CONNECTION_STRING = settings.pg_vector.connection_string
# COLLECTION_NAME: str = settings.pg_vector.collection_name

# zhipu_api_key = os.getenv("ZHIPUAI_API_KEY")
# zhipu_api_key = settings.api.secret_key

# assert zhipu_api_key is not None
# 从settings中获取配置


# 定义一个状态类
class State(TypedDict):
    question: str
    context: list[Document]
    answer: str


# simple_rag类
class SimpleRetrievalDemo:
    # 构造函数
    def __init__(
        self, api_key: str, pg_connection_string: str, pg_connection_name: str
    ) -> None:
        self.api_key = api_key
        self.pg_connection_string = pg_connection_string
        self.pg_connection_name = pg_connection_name
        self.vector_store: PGVector | None = None

    @staticmethod
    def create_prompt() -> PromptTemplate:
        # 定义 RAG 提示模板
        rag_template = """你是一个专业的问答助手，请根据提供的上下文 (Context) 来回答问题 (Question)。
            你的回答必须使用中文，并请只使用你从 Context 中获得的信息来回答。
            如果 Context 中没有相关信息，请诚实地回答你不知道,仅仅返回不知道三个字即可。

            Context:
            {context}

            Question: {question}

            Answer:
            """
        return PromptTemplate.from_template(template=rag_template)

    # 文档拆分器
    @staticmethod
    def document_partitioning(docs: list[Document]) -> list[Document]:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200
        )
        return text_splitter.split_documents(docs)

    # 初始化向量数据库
    def setup_vector_store(self) -> None:
        # 所用到的嵌入模型
        embeddings = ZhipuAIEmbeddings(
            api_key=self.api_key,
            model="embedding-2",
        )
        # 创建PGVector实例
        vector_store = PGVector(
            embeddings=embeddings,  # 文本转向量所使用的嵌入模型
            collection_name=self.pg_connection_name,  # RAG 应用知识库的唯一标识符。一旦您在代码中决定了一个名称（并通过 .env 文件配置），那么所有的加载、存储和检索操作都必须使用这个名称才能访问到正确的向量数据。
            connection=self.pg_connection_string,  # 数据库连接字符串
            use_jsonb=True,  # 推荐使用 JSONB 存储 元数据
        )
        self.vector_store = vector_store

    def get_vector_store(self) -> PGVector:
        if self.vector_store is None:
            self.setup_vector_store()
        return self.vector_store  # type: ignore

    def add_docs_to_vector_store(self, docs: list[Document]) -> None:
        docs_partition = self.document_partitioning(docs)
        vector_store = self.get_vector_store()  # 这里确保获取到的是PGVector，不是None
        vector_store.add_documents(documents=docs_partition)

    # 检索节点,为工作流服务，在langgraph中看作是检索节点
    def retrieve(self, state: State) -> dict[str, list[Document]]:
        vector_store = self.get_vector_store()  # 这里确保获取到的是PGVector，不是None
        retriever = vector_store.as_retriever(search_kwargs={"k": 3})
        res = retriever.invoke(state["question"])
        return {"context": res}

    # 生成节点，为工作流服务，在langgraph中看作是生成节点
    def generate(self, state: State) -> dict[str, str | list[str | dict[Any, Any]]]:
        docs_content: str = "\n\n".join(doc.page_content for doc in state["context"])
        messages: PromptValue = self.create_prompt().format_prompt(
            question=state["question"], context=docs_content
        )
        llm = ChatZhipuAI(model="glm-4v", api_key=self.api_key, temperature=0.1)
        response = llm.invoke(messages)
        return {"answer": response.content}  # type: ignore

    # 简单的检索生成工作流
    def simple_rag_retrieval(self, query: dict[str, str]) -> str:
        # 组成工作流
        graph_builder = StateGraph(State).add_sequence([self.retrieve, self.generate])
        graph_builder.add_edge(START, "retrieve")
        graph = graph_builder.compile()  # type: ignore
        # 执行工作流
        response = graph.invoke(query)  # type: ignore
        return response["answer"]  # type: ignore
