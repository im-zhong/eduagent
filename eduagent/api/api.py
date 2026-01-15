# Main API application
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from eduagent.api.security import require_service_token
from eduagent.documents.models import Base as DocumentsBase
from eduagent.logger import get_logger
from eduagent.storage.engine import async_engine, create_tables_for_module
from eduagent.settings import settings
from eduagent.llm import get_chat_model
from eduagent.agents.chat import get_agent, ensure_user_threads_table
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
# from eduagent.user.models import Base
# from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
# from eduagent.agents.chat import get_agent, ensure_user_threads_table
# from eduagent.llm import get_chat_model

# --------------------
from .endpoints import api_routers
from .exception_handlers import (
    global_exception_handler,
    http_exception_handler,
)

api_logger = get_logger(__name__, component="api.core")


# 2. 保留你的 lifespan 函数，用于应用启动时创建数据库表
# @asynccontextmanager
# async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
#     """
#     在应用启动时, 创建数据库表
#     """
#     api_logger.info("Initializing API database schema")
#     async with async_engine.begin() as conn:
#         await conn.run_sync(Base.metadata.create_all)
#     api_logger.info("API startup complete")
#     yield
#     # 应用关闭时的清理工作（如果需要）
#     api_logger.info("API shutdown sequence completed")


# # perfect for
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # create async pg saver
#     async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:
#         await checkpointer.setup()
#         await ensure_user_threads_table(checkpointer.conn)

#         # 需要在这里创建agent graph和checkpointer
#         # 不同用户的agent用config来区分
#         agent = get_agent(model=llm, checkpointer=checkpointer)
#         app.state.agent = agent
#         # get the async pgsql connector
#         app.state.conn = checkpointer.conn
#         yield

# 看起来我们必须先启动一个pg了
# 看起来async pg saver的内部实现并没有使用sqlalchemy，直接用的psycopg
# DB_URI = "postgresql://ysu_keg:123456789@db.eduagent:5432/eduagent?sslmode=disable"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Create database tables for documents module
    api_logger.info("Creating database tables for documents module")
    await create_tables_for_module(DocumentsBase)
    api_logger.info("Initializing LangGraph checkpointer and chat agent")
    conn_str = (
        "postgresql://"
        f"{settings.database.user}:{settings.database.password}"
        f"@{settings.database.host}:{settings.database.port}"
        f"/{settings.database.name}"
    )
    async with AsyncPostgresSaver.from_conn_string(conn_str) as checkpointer:
        await checkpointer.setup()
        await ensure_user_threads_table(checkpointer.conn)
        agent = get_agent(get_chat_model(), checkpointer)
        app.state.agent = agent
        app.state.conn = checkpointer.conn
        api_logger.info("API startup complete")
        yield

    api_logger.info("API shutdown sequence completed")


# Create FastAPI application
api = FastAPI(
    title="EduAgent AI Question Generation API",
    description="AI-powered educational question generation and assessment system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,  # 3. 应用你的 lifespan
)

# Configure CORS (与主分支保持一致)
api.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register global exception handlers
api.add_exception_handler(Exception, global_exception_handler)
api.add_exception_handler(500, http_exception_handler)

# 4. 采用主分支的循环方式注册所有 API 路由
security_dependencies = [Depends(require_service_token)]

for router in api_routers:
    # 你的 users_router 应该有自己的 tags，这里统一为 "AI Education Services"
    # 如果需要为 users_router 设置不同的 tag, 你需要在 endpoints/users.py 中定义好
    api.include_router(
        router,
        prefix="/api/v1",
        tags=["AI Education Services"],
        dependencies=security_dependencies,
    )


@api.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    api_logger.debug("Root endpoint requested")
    return {
        "message": "EduAgent AI Question Generation API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@api.get("/api/v1/health", include_in_schema=False)
async def health_check() -> dict[str, str]:
    api_logger.debug("Health check endpoint requested")
    return {"status": "healthy", "service": "eduagent-api"}


@api.get("/api/v1/version", include_in_schema=False)
async def version_check() -> dict[str, str]:
    api_logger.debug("Version endpoint requested")
    return {"name": "eduagent", "version": "1.0.0"}


@api.get("/service-auth/verify", include_in_schema=False)
async def verify_service_auth(
    claims: Annotated[dict[str, Any], Depends(require_service_token)],
) -> dict[str, str]:
    subject = str(claims.get("sub", "unknown"))
    api_logger.debug("Service auth validated for %s", subject)
    return {"status": "ok", "subject": subject}
