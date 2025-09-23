# Main API application
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .endpoints import api_routers

# Create FastAPI application
api = FastAPI(
    title="EduAgent AI Question Generation API",
    description="AI-powered educational question generation and assessment system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
api.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all API routers
for router in api_routers:
    api.include_router(router, prefix="/api/v1", tags=["AI Education Services"])


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
