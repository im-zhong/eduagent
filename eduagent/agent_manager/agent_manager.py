from abc import ABC, abstractmethod
from datetime import UTC, datetime

from eduagent.agents.base import BaseAgent
from eduagent.tools.base import BaseTool

from .agent_types import (
    AgentError,
    AgentInfo,
    AgentRequest,
    AgentResponse,
    AgentStatus,
    RequestLog,
    SystemStatus,
    ToolInfo,
)

# Constants
ACTIVE_AGENT_SUCCESS_RATE_THRESHOLD = 0.5


class AgentManager(ABC):
    """
    Abstract manager for coordinating multiple educational AI agents
    Routes requests to appropriate agents and manages tool usage
    """

    def __init__(self) -> None:
        self.agents: dict[str, BaseAgent] = {}
        self.tools: dict[str, BaseTool] = {}
        self.agent_mapping: dict[str, str] = {}  # Maps request types to agent IDs

    @abstractmethod
    def add_agent(self, agent: BaseAgent) -> None:
        """
        Add an agent to the manager

        Args:
            agent: Agent instance to add
        """

    @abstractmethod
    def add_tool(self, tool: BaseTool) -> None:
        """
        Add a tool to the manager

        Args:
            tool: Tool instance to add
        """

    @abstractmethod
    def find_agent_for_request(self, request: AgentRequest) -> str:
        """
        Find the best agent to handle a request

        Args:
            request: User request object

        Returns:
            ID of the agent that should handle the request
        """
        error_msg = (
            "Concrete agent managers must implement find_agent_for_request method"
        )
        raise NotImplementedError(error_msg)

    @abstractmethod
    def handle_request(self, request: AgentRequest) -> AgentResponse:
        """
        Handle a user request through the appropriate agent

        Args:
            request: User request object

        Returns:
            Response from the agent
        """
        error_msg = "Concrete agent managers must implement handle_request method"
        raise NotImplementedError(error_msg)

    @abstractmethod
    def list_agents(self) -> list[AgentInfo]:
        """
        Get list of available agents and their capabilities

        Returns:
            List of agent information objects
        """
        error_msg = "Concrete agent managers must implement list_agents method"
        raise NotImplementedError(error_msg)

    @abstractmethod
    def list_tools(self) -> list[ToolInfo]:
        """
        Get list of available tools and their capabilities

        Returns:
            List of tool information objects
        """
        error_msg = "Concrete agent managers must implement list_tools method"
        raise NotImplementedError(error_msg)

    @abstractmethod
    def check_agent_status(self) -> SystemStatus:
        """
        Check status of all agents

        Returns:
            System status information
        """
        error_msg = "Concrete agent managers must implement check_agent_status method"
        raise NotImplementedError(error_msg)

    @abstractmethod
    def handle_agent_error(self, agent_id: str, error: Exception) -> AgentError:
        """
        Handle agent error and provide alternatives

        Args:
            agent_id: ID of the agent that failed
            error: Exception that occurred

        Returns:
            Error handling information
        """
        error_msg = "Concrete agent managers must implement handle_agent_error method"
        raise NotImplementedError(error_msg)


class EducationalAgentManager(AgentManager):
    """
    Concrete implementation of educational AI agent manager
    Specialized for educational use cases
    """

    def __init__(self) -> None:
        super().__init__()
        self.request_log: list[RequestLog] = []
        self.agent_stats: dict[str, AgentStatus] = {}

    def add_agent(self, agent: BaseAgent) -> None:
        """Add an agent to the manager"""
        self.agents[agent.agent_id] = agent

        # Set up agent with available tools
        agent.initialize_agent()

        # Map agent capabilities for request routing
        capabilities = agent.get_agent_capabilities()
        agent_type = capabilities.get("agent_type", "general")
        self.agent_mapping[agent_type] = agent.agent_id

    def add_tool(self, tool: BaseTool) -> None:
        """Add a tool to the manager"""
        self.tools[tool.tool_name] = tool

    def find_agent_for_request(self, request: AgentRequest) -> str:
        """Find best agent for a request based on request type"""
        request_type = request.type

        # Simple matching based on request type
        if request_type in ["question_generation", "generate_questions"]:
            return self.agent_mapping.get("question_generator", "")
        if request_type in ["assessment", "evaluate_answers"]:
            return self.agent_mapping.get("assessment", "")
        if request_type in ["tutoring", "explanation", "learning_support"]:
            return self.agent_mapping.get("tutor", "")
        # Use first available agent as default
        return next(iter(self.agents.keys()), "")

    def handle_request(self, request: AgentRequest) -> AgentResponse:
        """Handle user request through appropriate agent"""
        start_time = datetime.now(UTC)

        # Log the request
        log_entry = RequestLog(
            timestamp=start_time.isoformat(),
            request=request.payload,
            status="processing",
        )
        self.request_log.append(log_entry)

        # Find the right agent
        agent_id = self.find_agent_for_request(request)

        if not agent_id or agent_id not in self.agents:
            return AgentResponse(
                success=False,
                agent_id="system",
                response_data={
                    "error": "No suitable agent found for this request",
                    "available_agents": list(self.agents.keys()),
                },
                processing_time_seconds=0.0,
                error_message="No suitable agent found",
            )

        agent = self.agents[agent_id]

        # Check if agent can handle this request
        if not agent.validate_request(request.payload):
            return AgentResponse(
                success=False,
                agent_id=agent_id,
                response_data={
                    "error": "Request not valid for this agent",
                    "agent_id": agent_id,
                    "agent_capabilities": agent.get_agent_capabilities(),
                },
                processing_time_seconds=0.0,
                error_message="Request not valid for this agent",
            )

        # Process the request
        try:
            response_data = agent.process_request(request.payload)
            processing_time = (datetime.now(UTC) - start_time).total_seconds()

            # Update request log
            self.request_log[-1].status = "completed"
            self.request_log[-1].agent_id = agent_id

            return AgentResponse(
                success=True,
                agent_id=agent_id,
                response_data=response_data,
                processing_time_seconds=processing_time,
            )

        except Exception as e:
            # Handle agent error
            processing_time = (datetime.now(UTC) - start_time).total_seconds()
            error_response = self.handle_agent_error(agent_id, e)
            self.request_log[-1].status = "failed"
            self.request_log[-1].error = str(e)

            return AgentResponse(
                success=False,
                agent_id=agent_id,
                response_data={
                    "error": str(e),
                    "suggestions": error_response.suggestions,
                },
                processing_time_seconds=processing_time,
                error_message=str(e),
            )

    def list_agents(self) -> list[AgentInfo]:
        """Get list of available agents"""
        agent_list: list[AgentInfo] = []
        for agent_id, agent in self.agents.items():
            agent_info = AgentInfo(
                agent_id=agent_id,
                name=agent.name,
                description=agent.description,
                capabilities=agent.get_agent_capabilities(),
                actions=agent.get_available_actions(),
            )
            agent_list.append(agent_info)
        return agent_list

    def list_tools(self) -> list[ToolInfo]:
        """Get list of available tools"""
        tool_list: list[ToolInfo] = []
        for tool_name, tool in self.tools.items():
            tool_info = ToolInfo(
                tool_name=tool_name,
                description=tool.description,
                version=tool.version,
                capabilities=tool.get_tool_capabilities(),
                tool_schema=tool.get_tool_schema(),
            )
            tool_list.append(tool_info)
        return tool_list

    def check_agent_status(self) -> SystemStatus:
        """Check status of all agents"""
        status_data: dict[str, AgentStatus] = {}
        total_agents = len(self.agents)
        active_agents = 0
        total_requests = len(self.request_log)

        for agent_id in self.agents:
            # Basic status information
            agent_requests = [r for r in self.request_log if r.agent_id == agent_id]
            completed = [r for r in agent_requests if r.status == "completed"]
            failed = [r for r in agent_requests if r.status == "failed"]

            if agent_requests:
                success_rate = len(completed) / len(agent_requests)
                if (
                    success_rate > ACTIVE_AGENT_SUCCESS_RATE_THRESHOLD
                ):  # Consider agent active if success rate > 50%
                    active_agents += 1
            else:
                success_rate = 0.0

            status_data[agent_id] = AgentStatus(
                total_requests=len(agent_requests),
                completed=len(completed),
                failed=len(failed),
                success_rate=success_rate,
                last_request=agent_requests[-1] if agent_requests else None,
            )

        return SystemStatus(
            status_data=status_data,
            total_agents=total_agents,
            active_agents=active_agents,
            total_requests=total_requests,
            system_uptime="System running",  # Would calculate actual uptime in production
        )

    def handle_agent_error(self, agent_id: str, error: Exception) -> AgentError:
        """Handle agent error"""
        return AgentError(
            error_type=type(error).__name__,
            error_message=str(error),
            agent_id=agent_id,
            suggestions=["try_again", "use_different_agent"],
            alternative_agents=[aid for aid in self.agents if aid != agent_id],
        )
