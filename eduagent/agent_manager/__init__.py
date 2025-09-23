"""
Agent Management System for EduAgent

Provides comprehensive agent orchestration, management, and coordination
functionality for educational AI agents.
"""

from .agent_manager import AgentManager, EducationalAgentManager
from .agent_types import (
    AgentCapability,
    AgentError,
    AgentInfo,
    AgentPerformanceMetrics,
    AgentRegistration,
    AgentRequest,
    AgentResponse,
    AgentStatus,
    RequestLog,
    SystemStatus,
    ToolInfo,
    ToolRegistration,
)

__all__ = [
    "AgentCapability",
    "AgentError",
    "AgentInfo",
    "AgentManager",
    "AgentPerformanceMetrics",
    "AgentRegistration",
    "AgentRequest",
    "AgentResponse",
    "AgentStatus",
    "EducationalAgentManager",
    "RequestLog",
    "SystemStatus",
    "ToolInfo",
    "ToolRegistration",
]
