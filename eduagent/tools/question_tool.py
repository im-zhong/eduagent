import uuid
from abc import abstractmethod

from .base import BaseTool
from .types import (
    DistractorData,
    QuestionConfig,
    QuestionData,
    SubmissionData,
    TextbookMetadata,
    ToolParameters,
    ToolResult,
)


class QuestionGenerationTool(BaseTool):
    """
    Tool interface for educational question generation
    Generates questions based on knowledge points and educational constraints
    """

    # Constants for query parsing
    MIN_PARTS = 2
    DEFAULT_DIFFICULTY = 0.5
    DEFAULT_QUESTION_TYPE = "multiple_choice"

    def __init__(self) -> None:
        super().__init__(
            tool_name="question_generation_tool",
            description="Generate educational questions with controlled difficulty and cognitive levels",
        )

    @abstractmethod
    def generate_questions(
        self,
        knowledge_point_ids: list[uuid.UUID],
        question_type: str,
        config: QuestionConfig | None = None,
    ) -> ToolResult:
        """
        Generate educational questions based on knowledge points

        Args:
            knowledge_point_ids: List of knowledge point IDs
            question_type: Type of question (multiple_choice, short_answer, etc.)
            config: Configuration object with generation parameters

        Returns:
            Dictionary with generated questions
        """

    @abstractmethod
    def adjust_difficulty(
        self, question_text: str, target_difficulty: float
    ) -> ToolResult:
        """
        Adjust question difficulty while maintaining educational value

        Args:
            question_text: Original question text
            target_difficulty: Desired difficulty level

        Returns:
            Dictionary with adjusted question
        """

    @abstractmethod
    def generate_distractors(
        self, question_text: str, knowledge_point_id: uuid.UUID
    ) -> list[DistractorData]:
        """
        Generate cognitively appropriate distractors

        Args:
            question_text: Question text
            knowledge_point_id: Knowledge point ID for context

        Returns:
            List of distractor dictionaries
        """

    @abstractmethod
    def validate_question(self, question_data: QuestionData) -> ToolResult:
        """
        Validate question quality and educational appropriateness

        Args:
            question_data: Question data to validate

        Returns:
            Dictionary with validation results
        """

    def execute(
        self,
        operation: str,
        file_path: str | None = None,  # noqa: ARG002
        textbook_metadata: TextbookMetadata | None = None,  # noqa: ARG002
        user_query: str | None = None,
        submissions: list[SubmissionData] | None = None,  # noqa: ARG002
    ) -> ToolResult:
        """Execute question generation tool operation"""
        if operation == "generate" and user_query:
            # Parse question parameters from user_query
            parts = user_query.split(":")
            if len(parts) >= self.MIN_PARTS:
                knowledge_point_ids = [uuid.UUID(parts[1].strip())]
                question_type = (
                    parts[2].strip()
                    if len(parts) > self.MIN_PARTS
                    else self.DEFAULT_QUESTION_TYPE
                )
                config = QuestionConfig(
                    difficulty=self.DEFAULT_DIFFICULTY,
                    cognitive_level="application",
                    num_questions=1,
                    constraints=None,
                )
                return self.generate_questions(
                    knowledge_point_ids, question_type, config
                )
        elif operation == "adjust_difficulty" and user_query:
            # Parse difficulty adjustment from user_query
            parts = user_query.split(":")
            if len(parts) >= self.MIN_PARTS:
                question_text = parts[1].strip()
                target_difficulty = (
                    float(parts[2].strip())
                    if len(parts) > self.MIN_PARTS
                    else self.DEFAULT_DIFFICULTY
                )
                return self.adjust_difficulty(question_text, target_difficulty)
        elif operation == "validate" and user_query:
            # Parse question data from user_query
            question_data = QuestionData(
                question_text=user_query,
                question_type="short_answer",
                cognitive_level="application",
                difficulty=self.DEFAULT_DIFFICULTY,
            )
            return self.validate_question(question_data)
        else:
            return ToolResult(
                success=False, error=f"Unknown or invalid operation: {operation}"
            )

        return ToolResult(
            success=False, error=f"Operation not implemented: {operation}"
        )

    def validate_parameters(self, parameters: ToolParameters) -> bool:
        """Validate question generation tool parameters"""
        operation = parameters.operation

        if operation == "generate":
            return (
                parameters.knowledge_point_ids is not None
                and parameters.question_type is not None
            )
        if operation == "adjust_difficulty":
            return (
                parameters.question_text is not None
                and parameters.target_difficulty is not None
            )
        if operation == "generate_distractors":
            return (
                parameters.question_text is not None
                and parameters.knowledge_point_ids is not None
            )
        if operation == "validate":
            return parameters.question_data is not None
        return False

    def get_tool_schema(self) -> ToolResult:
        """Return question generation tool schema"""
        return ToolResult(
            result_type="tool_schema",
            message=f"Question generation tool schema for {self.tool_name}",
        )

    def get_tool_capabilities(self) -> ToolResult:
        """Return question generation tool capabilities"""
        return ToolResult(
            result_type="tool_capabilities",
            message="Question generation tool capabilities: multiple_choice, short_answer, essay, true_false with difficulty_control, cognitive_level_control, distractor_generation, quality_validation, batch_generation",
        )
