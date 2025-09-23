import uuid
from abc import abstractmethod
from typing import Any

from .base import BaseTool


class QuestionGenerationTool(BaseTool):
    """
    Tool interface for educational question generation
    Generates questions based on knowledge points and educational constraints
    """

    def __init__(self):
        super().__init__(
            tool_name="question_generation_tool",
            description="Generate educational questions with controlled difficulty and cognitive levels"
        )
        # Define tool parameters
        self.add_parameter("knowledge_point_ids", "List of knowledge point IDs", required=True)
        self.add_parameter("question_type", "Type of question to generate", required=True)
        self.add_parameter("difficulty", "Target difficulty level")
        self.add_parameter("cognitive_level", "Target cognitive level")
        self.add_parameter("num_questions", "Number of questions to generate", default=1)
        self.add_parameter("constraints", "Additional generation constraints")

    @abstractmethod
    def generate_questions(self,
                         knowledge_point_ids: list[uuid.UUID],
                         question_type: str,
                         difficulty: float | None = None,
                         cognitive_level: str | None = None,
                         num_questions: int = 1,
                         constraints: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Generate educational questions based on knowledge points

        Args:
            knowledge_point_ids: List of knowledge point IDs
            question_type: Type of question (multiple_choice, short_answer, etc.)
            difficulty: Target difficulty level (0.0-1.0)
            cognitive_level: Target cognitive level
            num_questions: Number of questions to generate
            constraints: Additional generation constraints

        Returns:
            Dictionary with generated questions
        """

    @abstractmethod
    def adjust_difficulty(self,
                         question_text: str,
                         target_difficulty: float) -> dict[str, Any]:
        """
        Adjust question difficulty while maintaining educational value

        Args:
            question_text: Original question text
            target_difficulty: Desired difficulty level

        Returns:
            Dictionary with adjusted question
        """

    @abstractmethod
    def generate_distractors(self,
                           question_text: str,
                           knowledge_point_id: uuid.UUID) -> list[dict[str, Any]]:
        """
        Generate cognitively appropriate distractors

        Args:
            question_text: Question text
            knowledge_point_id: Knowledge point ID for context

        Returns:
            List of distractor dictionaries
        """

    @abstractmethod
    def validate_question(self, question_data: dict[str, Any]) -> dict[str, Any]:
        """
        Validate question quality and educational appropriateness

        Args:
            question_data: Question data to validate

        Returns:
            Dictionary with validation results
        """

    def execute(self, **kwargs) -> dict[str, Any]:
        """Execute question generation tool operation"""
        operation = kwargs.get("operation", "generate")

        if operation == "generate":
            return self.generate_questions(
                kwargs["knowledge_point_ids"],
                kwargs["question_type"],
                kwargs.get("difficulty"),
                kwargs.get("cognitive_level"),
                kwargs.get("num_questions", 1),
                kwargs.get("constraints")
            )
        if operation == "adjust_difficulty":
            return self.adjust_difficulty(
                kwargs["question_text"],
                kwargs["target_difficulty"]
            )
        if operation == "generate_distractors":
            return {"distractors": self.generate_distractors(
                kwargs["question_text"],
                kwargs["knowledge_point_id"]
            )}
        if operation == "validate":
            return self.validate_question(kwargs["question_data"])
        return {"error": f"Unknown operation: {operation}"}

    def validate_parameters(self, parameters: dict[str, Any]) -> bool:
        """Validate question generation tool parameters"""
        operation = parameters.get("operation", "generate")

        if operation == "generate":
            return "knowledge_point_ids" in parameters and "question_type" in parameters
        if operation == "adjust_difficulty":
            return "question_text" in parameters and "target_difficulty" in parameters
        if operation == "generate_distractors":
            return "question_text" in parameters and "knowledge_point_id" in parameters
        if operation == "validate":
            return "question_data" in parameters
        return False

    def get_tool_schema(self) -> dict[str, Any]:
        """Return question generation tool schema"""
        return {
            "name": self.tool_name,
            "description": self.description,
            "version": self.version,
            "operations": ["generate", "adjust_difficulty", "generate_distractors", "validate"],
            "parameters": self.parameters
        }

    def get_tool_capabilities(self) -> dict[str, Any]:
        """Return question generation tool capabilities"""
        return {
            "supported_question_types": ["multiple_choice", "short_answer", "essay", "true_false"],
            "difficulty_control": True,
            "cognitive_level_control": True,
            "distractor_generation": True,
            "quality_validation": True,
            "batch_generation": True
        }
