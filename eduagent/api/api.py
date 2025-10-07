from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# --- 新增的导入 ---
from eduagent.storage.engine import async_engine
from eduagent.user.models import Base

# --------------------
from .endpoints import (
    analytics_router,
    assessment_router,
    exercises_router,
    knowledge_router,
    questions_router,
    users_router,  # 1. 导入新的 users_router
)


# 2. 新增 lifespan 函数用于应用启动时创建数据库表
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """
    在应用启动时, 创建数据库表
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # 应用关闭时的清理工作（如果需要）


# Create FastAPI application
api = FastAPI(
    title="EduAgent AI Question Generation API",
    description="AI-powered educational question generation and assessment system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,  # 3. 将 lifespan 应用到 FastAPI 实例
)

# ... [CORS 中间件部分保持不变] ...
api.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include all API routers
api.include_router(analytics_router, prefix="/api/v1", tags=["AI Education Services"])
api.include_router(assessment_router, prefix="/api/v1", tags=["AI Education Services"])
api.include_router(exercises_router, prefix="/api/v1", tags=["AI Education Services"])
api.include_router(knowledge_router, prefix="/api/v1", tags=["AI Education Services"])
api.include_router(questions_router, prefix="/api/v1", tags=["AI Education Services"])
api.include_router(users_router, prefix="/api/v1")  # 4. 注册新的用户路由


# ... [root 和 health_check 路由保持不变] ...
@api.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {
        "message": "EduAgent AI Question Generation API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@api.get("/health", include_in_schema=False)
async def health_check() -> dict[str, str]:
    return {"status": "healthy", "service": "eduagent-api"}
