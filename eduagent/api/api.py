# Main API application
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from eduagent.api.security import require_service_token
from eduagent.logger import get_logger
from eduagent.storage.engine import async_engine
from eduagent.user.models import Base

# --------------------
from .endpoints import api_routers

api_logger = get_logger(__name__, component="api.core")


# 2. 保留你的 lifespan 函数，用于应用启动时创建数据库表
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """
    在应用启动时, 创建数据库表
    """
    api_logger.info("Initializing API database schema")
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    api_logger.info("API startup complete")
    yield
    # 应用关闭时的清理工作（如果需要）
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


@api.get("/health", include_in_schema=False)
async def health_check() -> dict[str, str]:
    api_logger.debug("Health check endpoint requested")
    return {"status": "healthy", "service": "eduagent-api"}
