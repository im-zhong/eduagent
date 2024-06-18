# TODO(G_shang_hui)
# take user input, retrieve relevant documents, and return them
# ref: https://python.langchain.com/docs/integrations/vectorstores/pgvector/


#from typing import List
#from dotenv import load_dotenv  # 导入加载配置的库
# --- ZhipuAI LangChain 集成 ---
from langchain_community.chat_models import ChatZhipuAI
from langchain_community.embeddings import ZhipuAIEmbeddings

# --- 核心 LangChain 组件导入 ---
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

# --- PGVector 导入 ---
from langchain_postgres.vectorstores import PGVector

# 1. 加载配置文件uv
# 加载 .env 文件中的配置到 os.environ
#load_dotenv()
#改成setting文件导入我的配置文件
from eduagent.defs import defs
from eduagent.settings import new_settings

settings = new_settings(defs.pathes.example_settings_file)  #创建一个setting实例

# 从settings中获取配置
ZHIPUAI_API_KEY: str= settings.llm.api_key
assert ZHIPUAI_API_KEY is not None
PG_CONNECTION_STRING = settings.pg_vector.connection_string
COLLECTION_NAME: str = settings.pg_vector.collection_name
assert COLLECTION_NAME is not None
GLM_MODEL: str = settings.llm.model_name
EMBEDDING_MODEL = settings.llm.embedding_model_name

# 检查必要的配置项
if not all([ZHIPUAI_API_KEY, PG_CONNECTION_STRING, COLLECTION_NAME]):
    missing = [
        k
        for k, v in {
            "ZHIPUAI_API_KEY": ZHIPUAI_API_KEY,
            "PG_CONNECTION_STRING": PG_CONNECTION_STRING,
            "COLLECTION_NAME": COLLECTION_NAME,
        }.items()
        if not v
    ]
    raise OSError(
        f"配置文件 (.env) 中缺少以下关键配置项: {', '.join(missing)}。请检查您的 .env 文件。"
    )


def setup_vector_store(texts: list[str]) -> PGVector:
    """
    设置并连接到 PGVector 向量存储。
    配置信息来自 .env 文件。
    """
    
    # 1. ZhipuAI Embedding 模型
    embeddings = ZhipuAIEmbeddings(
        model = EMBEDDING_MODEL,
        api_key = ZHIPUAI_API_KEY   # 明确传递 API Key
    )

    # 2. 连接到 PGVector
    vector_store = PGVector(
        embeddings=embeddings,  # 文本转向量所使用的嵌入模型
        collection_name=COLLECTION_NAME,  # RAG 应用知识库的唯一标识符。一旦您在代码中决定了一个名称（并通过 .env 文件配置），那么所有的加载、存储和检索操作都必须使用这个名称才能访问到正确的向量数据。
        connection=PG_CONNECTION_STRING,  # 数据库连接字符串
        use_jsonb=True,  # 推荐使用 JSONB 存储 元数据
    )

    # 3. 填充文档（只有在集合为空时才执行）
    if not vector_store.get(limit=1)["ids"]:
        print(f"PGVector 集合 '{COLLECTION_NAME}' 为空，正在创建和填充文档...")
        docs = [Document(page_content=t) for t in texts]
        vector_store.add_documents(docs)
        print(f"已向 {COLLECTION_NAME} 集合中添加 {len(docs)} 个文档。")
    else:
        print(f"PGVector 集合 '{COLLECTION_NAME}' 已存在，跳过填充。")

    return vector_store


def simple_rag_retrieval(query: str, vector_store: PGVector) -> str:
    """
    通过 LangChain RAG 链使用 GLM-4.5 和 PGVector 进行检索。
    """
    # 1. 配置 GLM-4.5 LLM
    llm = ChatZhipuAI(
        model=GLM_MODEL,
        temperature=0.1,
        api_key=ZHIPUAI_API_KEY,  # 明确传递 API Key
    )

    # 2. 创建检索器 (Retriever)
    retriever = vector_store.as_retriever(search_kwargs={"k": 3})

    # 3. 定义 RAG 提示模板
    template = """你是一个专业的问答助手，请根据提供的上下文 (Context) 来回答问题 (Question)。
    你的回答必须使用中文，并请只使用你从 Context 中获得的信息来回答。
    如果 Context 中没有相关信息，请诚实地回答你不知道。

    Context:
    {context}

    Question: {question}

    Answer:
    """
    prompt = ChatPromptTemplate.from_template(template)

    # 4. 构建 RAG Chain 
    def format_docs(docs: list[Document]) -> str:
        """将检索到的文档列表格式化为单个字符串，作为 Context 传递。"""
        return "\n\n".join(doc.page_content for doc in docs)

    rag_chain = (
        # 检索器：使用用户的 question 检索 docs
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt  # 组合提示词
        | llm  # 调用 GLM-4.5
        | StrOutputParser()  # 解析输出为字符串
    )

    # 5. 执行 Chain
    response = rag_chain.invoke(query)
    return response
