from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DifficultyLevel(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class QuestionType(str, Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    SHORT_ANSWER = "short_answer"
    ESSAY = "essay"
    FILL_IN_BLANK = "fill_in_blank"
    CALCULATION = "calculation"


class SubjectArea(str, Enum):
    MATH = "math"
    SCIENCE = "science"
    HISTORY = "history"
    LANGUAGE = "language"
    COMPUTER_SCIENCE = "computer_science"
    GENERAL = "general"
    PHYSICS = "physics"
    CHEMISTRY = "chemistry"
    BIOLOGY = "biology"


class CognitiveLevel(str, Enum):
    MEMORY = "memory"
    UNDERSTANDING = "understanding"
    APPLICATION = "application"
    ANALYSIS = "analysis"
    EVALUATION = "evaluation"
    CREATION = "creation"


class UserRole(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"


# ============ Knowledge Extraction Schemas ============
class TextbookUploadRequest(BaseModel):
    filename: str = Field(..., description="Textbook file name")
    file_type: str = Field(..., description="File type (pdf/docx/image)")
    subject: SubjectArea = Field(..., description="Subject area")
    grade_level: str = Field(..., description="Grade level")


class KnowledgeExtractionResponse(BaseModel):
    extraction_id: str
    status: str
    extracted_concepts: list[dict[str, Any]]
    created_at: datetime


class KnowledgePoint(BaseModel):
    id: str
    name: str
    description: str
    subject: SubjectArea
    chapter: str
    section: str


class AbilityTarget(BaseModel):
    knowledge_point_id: str
    cognitive_level: CognitiveLevel
    description: str


class CommonMistake(BaseModel):
    knowledge_point_id: str
    mistake_pattern: str
    description: str
    frequency: float = Field(0.0, ge=0.0, le=1.0)


class KnowledgeGraphResponse(BaseModel):
    knowledge_points: list[KnowledgePoint]
    ability_targets: list[AbilityTarget]
    common_mistakes: list[CommonMistake]
    graph_structure: dict[str, Any]


# ============ Question Generation Schemas ============
class QuestionGenerationRequest(BaseModel):
    knowledge_point_ids: list[str] = Field(..., description="Target knowledge points")
    question_type: QuestionType = Field(
        QuestionType.MULTIPLE_CHOICE, description="Question type"
    )
    difficulty: DifficultyLevel = Field(
        DifficultyLevel.MEDIUM, description="Difficulty level"
    )
    num_questions: int = Field(
        1, ge=1, le=10, description="Number of questions to generate"
    )
    cognitive_level: CognitiveLevel | None = Field(
        None, description="Specific cognitive level target"
    )
    include_explanation: bool = Field(
        default=True, description="Include answer explanation"
    )


class QuestionOption(BaseModel):
    id: str
    text: str
    is_correct: bool
    mistake_pattern: str | None = Field(
        None, description="Associated mistake pattern if incorrect"
    )


class GeneratedQuestion(BaseModel):
    id: str
    question_text: str
    question_type: QuestionType
    difficulty: DifficultyLevel
    cognitive_level: CognitiveLevel
    knowledge_point_ids: list[str]
    options: list[QuestionOption] | None = None
    correct_answer: str | None = None
    explanation: str | None = None
    solution_steps: list[str] | None = None
    estimated_difficulty: float = Field(0.5, ge=0.0, le=1.0)


class QuestionGenerationResponse(BaseModel):
    questions: list[GeneratedQuestion]
    generation_id: str
    generated_at: datetime


class DifficultyControlRequest(BaseModel):
    question_text: str
    target_difficulty: DifficultyLevel
    max_steps: int | None = Field(None, description="Maximum solution steps")
    knowledge_depth: int | None = Field(None, description="Knowledge depth level")


class DifficultyControlResponse(BaseModel):
    adjusted_question: str
    difficulty_score: float
    cognitive_complexity: float
    step_count: int


# ============ Assessment & Feedback Schemas ============
class AnswerSubmission(BaseModel):
    question_id: str
    student_answer: str
    time_taken: float | None = Field(None, description="Time taken in seconds")


class AssessmentRequest(BaseModel):
    submissions: list[AnswerSubmission]
    student_id: str
    exercise_id: str | None = None


class AssessmentResult(BaseModel):
    question_id: str
    is_correct: bool
    score: float
    feedback: str
    correct_answer: str
    explanation: str
    mistake_pattern: str | None = None


class AssessmentResponse(BaseModel):
    results: list[AssessmentResult]
    total_score: float
    accuracy: float
    weak_knowledge_points: list[str]
    common_mistakes: list[str]


class FeedbackRequest(BaseModel):
    question_text: str
    student_answer: str
    correct_answer: str
    knowledge_point_id: str


class FeedbackResponse(BaseModel):
    score: float
    detailed_feedback: str
    suggestions: list[str]
    recommended_practice: list[str]


# ============ User & Platform Management Schemas ============
class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., description="User email")
    password: str = Field(..., min_length=6)
    role: UserRole = Field(UserRole.STUDENT)
    grade_level: str | None = None
    subject_interests: list[SubjectArea] | None = None


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: UserRole
    grade_level: str | None
    subject_interests: list[SubjectArea] | None
    created_at: datetime
    is_active: bool


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ============ Exercise & Practice Schemas ============
class ExerciseCreateRequest(BaseModel):
    title: str
    description: str | None = None
    subject: SubjectArea
    difficulty: DifficultyLevel
    knowledge_point_ids: list[str]
    num_questions: int = Field(10, ge=1, le=50)
    time_limit: int | None = Field(None, description="Time limit in minutes")


class ExerciseResponse(BaseModel):
    id: str
    title: str
    description: str | None
    subject: SubjectArea
    difficulty: DifficultyLevel
    question_ids: list[str]
    created_at: datetime
    created_by: str


class PracticeSessionRequest(BaseModel):
    exercise_id: str | None = None
    knowledge_point_ids: list[str] | None = None
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    num_questions: int = Field(10, ge=1, le=20)


class PracticeSessionResponse(BaseModel):
    session_id: str
    questions: list[GeneratedQuestion]
    started_at: datetime
    time_limit: int | None


# ============ Analytics & Reporting Schemas ============
class PerformanceAnalyticsRequest(BaseModel):
    student_id: str | None = None
    class_id: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    subject: SubjectArea | None = None


class KnowledgePointAnalytics(BaseModel):
    knowledge_point_id: str
    accuracy: float
    attempt_count: int
    average_time: float
    common_mistakes: list[str]


class PerformanceAnalyticsResponse(BaseModel):
    overall_accuracy: float
    total_attempts: int
    average_time_per_question: float
    knowledge_point_analytics: list[KnowledgePointAnalytics]
    progress_trend: list[dict[str, Any]]
    weak_areas: list[str]


class MistakeAnalysisRequest(BaseModel):
    student_id: str
    knowledge_point_id: str | None = None
    time_period: str | None = Field(None, description="e.g., '7d', '30d', '90d'")


class MistakeAnalysisResponse(BaseModel):
    mistake_patterns: list[dict[str, Any]]
    frequency_distribution: dict[str, int]
    recommended_remediation: list[str]
    similar_questions: list[str]


# ============ System & Health Schemas ============
class HealthCheckResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime
    components: dict[str, str]


class ErrorResponse(BaseModel):
    error: str
    code: int
    details: str | None = None
    request_id: str | None = None


class BatchOperationResponse(BaseModel):
    operation_id: str
    status: str
    processed_count: int
    success_count: int
    failed_count: int
    errors: list[dict[str, Any]] | None = None
