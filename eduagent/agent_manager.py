from abc import ABC, abstractmethod
from typing import Any

from .agents.base import BaseAgent
from .tools.base import BaseTool


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
    def find_agent_for_request(self, request: dict[str, Any]) -> str:
        """
        Find the best agent to handle a request

        Args:
            request: User request dictionary

        Returns:
            ID of the agent that should handle the request
        """

    @abstractmethod
    def handle_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """
        Handle a user request through the appropriate agent

        Args:
            request: User request dictionary

        Returns:
            Response from the agent
        """

    @abstractmethod
    def list_agents(self) -> list[dict[str, Any]]:
        """
        Get list of available agents and their capabilities

        Returns:
            List of agent information dictionaries
        """

    @abstractmethod
    def list_tools(self) -> list[dict[str, Any]]:
        """
        Get list of available tools and their capabilities

        Returns:
            List of tool information dictionaries
        """

    @abstractmethod
    def check_agent_status(self) -> dict[str, Any]:
        """
        Check status of all agents

        Returns:
            Dictionary with agent status information
        """

    @abstractmethod
    def handle_agent_error(self, agent_id: str, error: Exception) -> dict[str, Any]:
        """
        Handle agent error and provide alternatives

        Args:
            agent_id: ID of the agent that failed
            error: Exception that occurred

        Returns:
            Dictionary with error handling information
        """


class EducationalAgentManager(AgentManager):
    """
    Concrete implementation of educational AI agent manager
    Specialized for educational use cases
    """

    def __init__(self) -> None:
        super().__init__()
        self.request_log: list[dict[str, Any]] = []
        self.agent_stats: dict[str, Any] = {}

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

    def find_agent_for_request(self, request: dict[str, Any]) -> str:
        """Find best agent for a request based on request type"""
        request_type = request.get("type", "general")

        # Simple matching based on request type
        if request_type in ["question_generation", "generate_questions"]:
            return self.agent_mapping.get("question_generator", "")
        if request_type in ["assessment", "evaluate_answers"]:
            return self.agent_mapping.get("assessment", "")
        if request_type in ["tutoring", "explanation", "learning_support"]:
            return self.agent_mapping.get("tutor", "")
        # Use first available agent as default
        return next(iter(self.agents.keys()), "")

    def handle_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle user request through appropriate agent"""
        # Log the request
        self.request_log.append({
            "timestamp": "current_time",  # Would use actual timestamp in implementation
            "request": request,
            "status": "processing"
        })

        # Find the right agent
        agent_id = self.find_agent_for_request(request)

        if not agent_id or agent_id not in self.agents:
            return {
                "error": "No suitable agent found for this request",
                "available_agents": list(self.agents.keys())
            }

        agent = self.agents[agent_id]

        # Check if agent can handle this request
        if not agent.validate_request(request):
            return {
                "error": "Request not valid for this agent",
                "agent_id": agent_id,
                "agent_capabilities": agent.get_agent_capabilities()
            }

        # Process the request
        try:
            response = agent.process_request(request)

            # Update request log
            self.request_log[-1]["status"] = "completed"
            self.request_log[-1]["agent_id"] = agent_id

            return response

        except Exception as e:
            # Handle agent error
            error_response = self.handle_agent_error(agent_id, e)
            self.request_log[-1]["status"] = "failed"
            self.request_log[-1]["error"] = str(e)

            return error_response

    def list_agents(self) -> list[dict[str, Any]]:
        """Get list of available agents"""
        agent_list = []
        for agent_id, agent in self.agents.items():
            agent_list.append({
                "agent_id": agent_id,
                "name": agent.name,
                "description": agent.description,
                "capabilities": agent.get_agent_capabilities(),
                "actions": agent.get_available_actions()
            })
        return agent_list

    def list_tools(self) -> list[dict[str, Any]]:
        """Get list of available tools"""
        tool_list = []
        for tool_name, tool in self.tools.items():
            tool_list.append({
                "tool_name": tool_name,
                "description": tool.description,
                "version": tool.version,
                "capabilities": tool.get_tool_capabilities(),
                "schema": tool.get_tool_schema()
            })
        return tool_list

    def check_agent_status(self) -> dict[str, Any]:
        """Check status of all agents"""
        status_data = {}
        for agent_id in self.agents:
            # Basic status information
            agent_requests = [r for r in self.request_log if r.get("agent_id") == agent_id]
            completed = [r for r in agent_requests if r.get("status") == "completed"]
            failed = [r for r in agent_requests if r.get("status") == "failed"]

            status_data[agent_id] = {
                "total_requests": len(agent_requests),
                "completed": len(completed),
                "failed": len(failed),
                "success_rate": len(completed) / len(agent_requests) if agent_requests else 0,
                "last_request": agent_requests[-1] if agent_requests else None
            }

        return status_data

    def handle_agent_error(self, agent_id: str, error: Exception) -> dict[str, Any]:
        """Handle agent error"""
        return {
            "error": f"Agent {agent_id} encountered an error",
            "error_details": str(error),
            "suggestions": ["try_again", "use_different_agent"],
            "other_agents": [aid for aid in self.agents if aid != agent_id]
        }
