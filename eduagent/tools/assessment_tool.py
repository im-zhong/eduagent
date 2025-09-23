import uuid
from abc import abstractmethod

from .base import BaseTool
from .types import (
    AssessmentCriteria,
    SubmissionData,
    TextbookMetadata,
    ToolParameters,
    ToolResult,
)


class AssessmentTool(BaseTool):
    """
    Tool interface for student assessment and feedback generation
    Evaluates answers and provides educational feedback
    """

    # Constants for query parsing
    MIN_PARTS = 3

    def __init__(self) -> None:
        super().__init__(
            tool_name="assessment_tool",
            description="Evaluate student answers and generate detailed feedback",
        )

    @abstractmethod
    def evaluate_answers(
        self,
        submissions: list[SubmissionData],
        assessment_criteria: AssessmentCriteria | None = None,
    ) -> ToolResult:
        """
        Evaluate student answers and provide assessment

        Args:
            submissions: List of student answer submissions
            assessment_criteria: Optional custom assessment criteria

        Returns:
            Dictionary with evaluation results
        """

    @abstractmethod
    def generate_feedback(
        self,
        submission_id: uuid.UUID,
        student_answer: str,
        correct_answer: str,
        feedback_level: str = "detailed",
    ) -> ToolResult:
        """
        Generate detailed feedback for a student answer

        Args:
            submission_id: ID of the answer submission
            student_answer: Student's answer text
            correct_answer: Correct answer text
            feedback_level: Level of feedback detail

        Returns:
            Dictionary with feedback and suggestions
        """

    @abstractmethod
    def identify_mistake_patterns(
        self, student_id: uuid.UUID, time_period: str | None = None
    ) -> ToolResult:
        """
        Identify common mistake patterns for a student

        Args:
            student_id: ID of the student
            time_period: Optional time period filter

        Returns:
            Dictionary with mistake patterns
        """

    @abstractmethod
    def calculate_performance_metrics(
        self, student_id: uuid.UUID, knowledge_point_ids: list[uuid.UUID] | None = None
    ) -> ToolResult:
        """
        Calculate performance metrics for a student

        Args:
            student_id: ID of the student
            knowledge_point_ids: Optional specific knowledge points

        Returns:
            Dictionary with performance metrics
        """

    def execute(
        self,
        operation: str,
        file_path: str | None = None,  # noqa: ARG002
        textbook_metadata: TextbookMetadata | None = None,  # noqa: ARG002
        user_query: str | None = None,
        submissions: list[SubmissionData] | None = None,
    ) -> ToolResult:
        """Execute assessment tool operation"""
        if operation == "evaluate" and submissions:
            return self.evaluate_answers(submissions)
        if operation == "generate_feedback" and user_query:
            # Parse feedback parameters from user_query
            parts = user_query.split(":")
            if len(parts) >= self.MIN_PARTS:
                submission_id = uuid.UUID(parts[1].strip())
                student_answer = parts[2].strip()
                correct_answer = parts[3].strip() if len(parts) > self.MIN_PARTS else ""
                return self.generate_feedback(
                    submission_id, student_answer, correct_answer
                )
        elif operation == "identify_mistakes" and user_query:
            # Parse student_id from user_query
            student_id = uuid.UUID(user_query.split(":")[1].strip())
            return self.identify_mistake_patterns(student_id)
        elif operation == "calculate_metrics" and user_query:
            # Parse student_id from user_query
            student_id = uuid.UUID(user_query.split(":")[1].strip())
            return self.calculate_performance_metrics(student_id)
        else:
            return ToolResult(
                success=False, error=f"Unknown or invalid operation: {operation}"
            )

        return ToolResult(
            success=False, error=f"Operation not implemented: {operation}"
        )

    def validate_parameters(self, parameters: ToolParameters) -> bool:
        """Validate assessment tool parameters"""
        operation = parameters.operation

        if operation == "evaluate":
            return True  # Submissions are passed directly to execute method
        if operation == "generate_feedback":
            return parameters.question_text is not None
        if operation in ("identify_mistakes", "calculate_metrics"):
            return parameters.knowledge_point_ids is not None
        return False

    def get_tool_schema(self) -> ToolResult:
        """Return assessment tool schema"""
        return ToolResult(
            result_type="tool_schema",
            message=f"Assessment tool schema for {self.tool_name}",
        )

    def get_tool_capabilities(self) -> ToolResult:
        """Return assessment tool capabilities"""
        return ToolResult(
            result_type="tool_capabilities",
            message="Assessment tool capabilities: auto_grading, feedback_generation, mistake_analysis, performance_tracking, personalized_feedback, real_time_assessment",
        )
