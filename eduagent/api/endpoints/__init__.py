from .analytics import router as analytics_router
from .assessment import router as assessment_router
from .exercises import router as exercises_router
from .knowledge import router as knowledge_router
from .questions import router as questions_router

# Include all routers
api_routers = [
    analytics_router,
    assessment_router,
    exercises_router,
    knowledge_router,
    questions_router,
]

# Export for main app
__all__ = ["api_routers"]
