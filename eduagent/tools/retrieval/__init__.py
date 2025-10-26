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
from langchain_core.prompts import ChatPromptTemplate

# --- PGVector 导入 ---
from langchain_postgres.vectorstores import PGVector
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import START, StateGraph
from typing_extensions import List, TypedDict

#改成setting文件导入我的配置文件
from eduagent.defs import defs
from eduagent.settings import new_settings

settings = new_settings(defs.pathes.example_settings_file)  #创建一个setting实例

# 从settings中获取配置
ZHIPUAI_API_KEY: str= settings.llm.api_key
PG_CONNECTION_STRING = settings.pg_vector.connection_string
COLLECTION_NAME: str = settings.pg_vector.collection_name

# 初始化模型
# 初始化嵌入模型
embeddings = ZhipuAIEmbeddings(
    api_key="你的API密钥",
    model="embedding-2"  # 默认就是 embedding-2
)
llm = ChatZhipuAI(
    model="glm-4", 
    api_key="你的API密钥",
    temperature=0.1
    )

#准备数据
docs = [
    Document(
        page_content="there are cats in the pond",
        metadata={"id": 1, "location": "pond", "topic": "animals"},
    ),
    Document(
        page_content="ducks are also found in the pond",
        metadata={"id": 2, "location": "pond", "topic": "animals"},
    ),
    Document(
        page_content="fresh apples are available at the market",
        metadata={"id": 3, "location": "market", "topic": "food"},
    ),
    Document(
        page_content="the market also sells fresh oranges",
        metadata={"id": 4, "location": "market", "topic": "food"},
    ),
    Document(
        page_content="the new art exhibit is fascinating",
        metadata={"id": 5, "location": "museum", "topic": "art"},
    ),
    Document(
        page_content="a sculpture exhibit is also at the museum",
        metadata={"id": 6, "location": "museum", "topic": "art"},
    ),
    Document(
        page_content="a new coffee shop opened on Main Street",
        metadata={"id": 7, "location": "Main Street", "topic": "food"},
    ),
    Document(
        page_content="the book club meets at the library",
        metadata={"id": 8, "location": "library", "topic": "reading"},
    ),
    Document(
        page_content="the library hosts a weekly story time for kids",
        metadata={"id": 9, "location": "library", "topic": "reading"},
    ),
    Document(
        page_content="a cooking class for beginners is offered at the community center",
        metadata={"id": 10, "location": "community center", "topic": "classes"},
    )
    ]
#文档拆分
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
all_splits = text_splitter.split_documents(docs)

# 定义 RAG 提示模板
rag_template = """你是一个专业的问答助手，请根据提供的上下文 (Context) 来回答问题 (Question)。
    你的回答必须使用中文，并请只使用你从 Context 中获得的信息来回答。
    如果 Context 中没有相关信息，请诚实地回答你不知道。

    Context:
    {context}

    Question: {question}

    Answer:
    """
prompt = ChatPromptTemplate.from_template(template=rag_template)
class State(TypedDict):
    question: str
    context: List[Document]
    answer: str


#连接向量数据库，并且初始化一些数据进去
def setup_vector_store() -> PGVector:
    """
    设置并连接到 PGVector 向量存储。
    配置信息来自 settings文件。
    """
    # 2. 连接到 PGVector
    vector_store = PGVector(
        embeddings=embeddings,  # 文本转向量所使用的嵌入模型
        collection_name=COLLECTION_NAME,  # RAG 应用知识库的唯一标识符。一旦您在代码中决定了一个名称（并通过 .env 文件配置），那么所有的加载、存储和检索操作都必须使用这个名称才能访问到正确的向量数据。
        connection=PG_CONNECTION_STRING,  # 数据库连接字符串
        use_jsonb=True,  # 推荐使用 JSONB 存储 元数据
    )
    vector_store.add_documents(documents=all_splits)

    return vector_store

#创建向量数据库实例
vector_store = setup_vector_store()

def retrieve(state: State):
    retriever = vector_store.as_retriever( search_kwargs={"k": 3})
    res = retriever.invoke(state["question"])
    return {"context": res}

def generate(state: State):
    docs_content = "\n\n".join(doc.page_content for doc in state["context"])
    messages = prompt.invoke({"question": state["question"], "context": docs_content})
    response = llm.invoke(messages)
    return {"answer": str(response.content)}

def simple_rag_retrieval(query: dict) -> str:
    #组成工作流
    graph_builder = StateGraph(State).add_sequence([retrieve, generate])
    graph_builder.add_edge(START, "retrieve")
    graph = graph_builder.compile()
    #执行工作流
    response = graph.invoke(query)
    return response["answer"]
