import os

from langchain.chains import RetrievalQA
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.llms import OpenAIILike  # 或者使用GLM-4.5的适配器
from langchain.schema import Document
from langchain.vectorstores import PGVector

from eduagent.settings import settings


class GLMRetrieval:
    def __init__(self, connection_string: str, collection_name: str = "glm_retrieval"):
        # 初始化嵌入模型（使用与GLM-4.5兼容的模型）
        self.embeddings = HuggingFaceEmbeddings(
            model_name="BAAI/bge-large-zh-v1.5"  # 中文文本检索表现良好的模型
        )

        # 初始化向量数据库连接
        self.vectorstore = PGVector(
            connection_string=settings.pg_vector.connection_string,
            embedding_function=self.embeddings,
            collection_name=collection_name,
        )

        # 初始化GLM-45模型（需要根据实际API调整）
        # 注意：这里需要替换为实际的GLM-4.5访问方式
        self.llm = OpenAIILike(
            api_base="https://your-glm4-api-endpoint.com/v1",  # GLM-4.5 API端点
            api_key=os.getenv("GLM_API_KEY"),
            model_name="glm-4-5",
        )

        # 创建检索链
        self.qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.vectorstore.as_retriever(
                search_type="similarity", search_kwargs={"k": 3}
            ),
            return_source_documents=True,
        )

    def query(self, question: str) -> dict:
        """执行检索并返回结果"""
        return self.qa_chain({"query": question})

    def add_documents(self, documents: List[Document]):
        """向向量库添加文档"""
        self.vectorstore.add_documents(documents)


# 使用示例
def create_retrieval_system():
    # 从环境变量获取数据库连接字符串
    connection_string = os.getenv("PGVECTOR_CONNECTION_STRING")
    return GLMRetrieval(connection_string)
