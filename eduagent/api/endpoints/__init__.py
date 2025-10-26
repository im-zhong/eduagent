from .analytics import router as analytics_router
from .assessment import router as assessment_router
from .exercises import router as exercises_router
from .knowledge import router as knowledge_router
from .questions import router as questions_router

# from .users import router as users_router  # << 1. 导入 users_router

# Include all routers
api_routers = [
    analytics_router,
    assessment_router,
    exercises_router,
    knowledge_router,
    questions_router,
    # users_router,  # << 2. 将 users_router 添加到列表中
]

# Export for main app
__all__ = ["api_routers"]
