"""
Agent management type definitions for EduAgent
Provides Pydantic models for agent operations and management
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from eduagent.tools.types import ToolResult


class AgentInfo(BaseModel):
    """Information about an agent"""

    agent_id: str
    name: str
    description: str
    capabilities: dict[str, Any]
    actions: list[str]


class ToolInfo(BaseModel):
    """Information about a tool"""

    tool_name: str
    description: str
    version: str
    capabilities: ToolResult
    tool_schema: ToolResult


class RequestLog(BaseModel):
    """Log entry for a processed request"""

    timestamp: str
    request: dict[str, Any]
    status: str
    agent_id: str | None = None
    error: str | None = None


class AgentStatus(BaseModel):
    """Status information for an agent"""

    total_requests: int = Field(0, ge=0)
    completed: int = Field(0, ge=0)
    failed: int = Field(0, ge=0)
    success_rate: float = Field(0.0, ge=0.0, le=1.0)
    last_request: RequestLog | None = None


class SystemStatus(BaseModel):
    """Overall system status information"""

    status_data: dict[str, AgentStatus]
    total_agents: int = Field(0, ge=0)
    active_agents: int = Field(0, ge=0)
    total_requests: int = Field(0, ge=0)
    system_uptime: str | None = None


class AgentRequest(BaseModel):
    """Request to be processed by an agent"""

    type: str
    payload: dict[str, Any]
    priority: str = "normal"
    timeout_seconds: int | None = None


class AgentResponse(BaseModel):
    """Response from an agent"""

    success: bool
    agent_id: str
    response_data: dict[str, Any]
    processing_time_seconds: float = Field(0.0, ge=0.0)
    error_message: str | None = None


class AgentError(BaseModel):
    """Error information for agent operations"""

    error_type: str
    error_message: str
    agent_id: str
    suggestions: list[str]
    alternative_agents: list[str]
    timestamp: datetime = Field(default_factory=datetime.now)


class AgentCapability(BaseModel):
    """Specific capability of an agent"""

    capability_name: str
    description: str
    supported_operations: list[str]
    confidence_level: float = Field(0.0, ge=0.0, le=1.0)
    requirements: list[str] | None = None


class AgentPerformanceMetrics(BaseModel):
    """Performance metrics for an agent"""

    agent_id: str
    total_processed: int = Field(0, ge=0)
    success_rate: float = Field(0.0, ge=0.0, le=1.0)
    average_processing_time: float = Field(0.0, ge=0.0)
    error_rate: float = Field(0.0, ge=0.0, le=1.0)
    last_used: datetime | None = None


class ToolRegistration(BaseModel):
    """Registration data for a new tool"""

    tool_name: str
    tool_type: str
    description: str
    version: str
    compatible_agents: list[str]
    required_permissions: list[str] | None = None


class AgentRegistration(BaseModel):
    """Registration data for a new agent"""

    agent_id: str
    agent_type: str
    name: str
    description: str
    required_tools: list[str]
    supported_request_types: list[str]
    max_concurrent_requests: int = Field(1, ge=1)
