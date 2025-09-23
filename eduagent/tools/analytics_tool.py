import uuid
from abc import abstractmethod

from .base import BaseTool
from .types import (
    SubmissionData,
    TextbookMetadata,
    ToolParameters,
    ToolResult,
)


class AnalyticsTool(BaseTool):
    """
    Tool interface for educational analytics and reporting
    Provides insights into student performance and learning patterns
    """

    # Constants for query parsing
    MIN_STUDENT_ID_PARTS = 2
    MIN_SUBJECT_PARTS = 3

    def __init__(self) -> None:
        super().__init__(
            tool_name="analytics_tool",
            description="Generate educational analytics and performance insights",
        )

    @abstractmethod
    def get_student_analytics(
        self, student_id: uuid.UUID, time_period: str = "30d"
    ) -> ToolResult:
        """
        Get comprehensive analytics for a student

        Args:
            student_id: ID of the student
            time_period: Time period for analysis

        Returns:
            Dictionary with student analytics
        """

    @abstractmethod
    def get_class_analytics(
        self, class_id: uuid.UUID, time_period: str = "30d"
    ) -> ToolResult:
        """
        Get analytics for an entire class

        Args:
            class_id: ID of the class
            time_period: Time period for analysis

        Returns:
            Dictionary with class analytics
        """

    @abstractmethod
    def identify_learning_gaps(
        self, student_id: uuid.UUID, subject_area: str
    ) -> ToolResult:
        """
        Identify learning gaps for a student

        Args:
            student_id: ID of the student
            subject_area: Subject area to analyze

        Returns:
            Dictionary with identified learning gaps
        """

    @abstractmethod
    def generate_progress_report(
        self, student_id: uuid.UUID, report_type: str = "comprehensive"
    ) -> ToolResult:
        """
        Generate progress report for a student

        Args:
            student_id: ID of the student
            report_type: Type of report to generate

        Returns:
            Dictionary with progress report
        """

    @abstractmethod
    def predict_performance(
        self, student_id: uuid.UUID, future_timeframe: str = "30d"
    ) -> ToolResult:
        """
        Predict future performance for a student

        Args:
            student_id: ID of the student
            future_timeframe: Timeframe for prediction

        Returns:
            Dictionary with performance predictions
        """

    def execute(
        self,
        operation: str,
        file_path: str | None = None,  # noqa: ARG002
        textbook_metadata: TextbookMetadata | None = None,  # noqa: ARG002
        user_query: str | None = None,
        submissions: list[SubmissionData] | None = None,  # noqa: ARG002
    ) -> ToolResult:
        """Execute analytics tool operation"""
        if operation == "student_analytics" and user_query:
            # Parse student_id from user_query
            student_id = (
                user_query.split(":")[1].strip() if ":" in user_query else user_query
            )
            return self.get_student_analytics(uuid.UUID(student_id))
        if operation == "class_analytics" and user_query:
            # Parse class_id from user_query
            class_id = (
                user_query.split(":")[1].strip() if ":" in user_query else user_query
            )
            return self.get_class_analytics(uuid.UUID(class_id))
        if operation == "identify_gaps" and user_query:
            # Parse student_id and subject_area from user_query
            parts = user_query.split(":")
            student_id = (
                parts[1].strip()
                if len(parts) > self.MIN_STUDENT_ID_PARTS - 1
                else user_query
            )
            subject_area = (
                parts[2].strip()
                if len(parts) > self.MIN_SUBJECT_PARTS - 1
                else "general"
            )
            return self.identify_learning_gaps(uuid.UUID(student_id), subject_area)
        if operation == "generate_report" and user_query:
            # Parse student_id from user_query
            student_id = (
                user_query.split(":")[1].strip() if ":" in user_query else user_query
            )
            return self.generate_progress_report(uuid.UUID(student_id))
        return ToolResult(
            success=False, error=f"Unknown or invalid operation: {operation}"
        )

        return ToolResult(
            success=False, error=f"Operation not implemented: {operation}"
        )

    def validate_parameters(self, parameters: ToolParameters) -> bool:
        """Validate analytics tool parameters"""
        operation = parameters.operation

        if operation == "student_analytics":
            return parameters.knowledge_point_ids is not None
        if operation == "class_analytics":
            return parameters.knowledge_point_ids is not None
        if operation == "identify_gaps":
            return parameters.knowledge_point_ids is not None
        if operation in ("generate_report", "predict_performance"):
            return parameters.knowledge_point_ids is not None
        return False

    def get_tool_schema(self) -> ToolResult:
        """Return analytics tool schema"""
        return ToolResult(
            result_type="tool_schema",
            message=f"Analytics tool schema for {self.tool_name}",
        )

    def get_tool_capabilities(self) -> ToolResult:
        """Return analytics tool capabilities"""
        return ToolResult(
            result_type="tool_capabilities",
            message="Analytics tool capabilities: student_analytics, class_analytics, learning_gap_analysis, progress_tracking, performance_prediction, report_generation, real_time_analytics",
        )
