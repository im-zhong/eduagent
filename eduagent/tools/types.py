"""
Type definitions for EduAgent tools
Provides meaningful type aliases to improve code readability and maintainability
"""

from pydantic import BaseModel, Field

# Tool-specific type aliases will be replaced with concrete Pydantic models


class ToolResult(BaseModel):
    """Standard result type for tool operations"""

    success: bool = True
    result_id: str | None = None
    result_type: str | None = None
    message: str | None = None
    error: str | None = None


# Specific tool parameter structures
class StudentIdParam(BaseModel):
    """Parameters for student-related operations"""

    student_id: str


class ClassIdParam(BaseModel):
    """Parameters for class-related operations"""

    class_id: str


class TimePeriodParam(BaseModel):
    """Parameters for time-based operations"""

    time_period: str


class AnalyticsParams(StudentIdParam, TimePeriodParam):
    """Combined parameters for analytics operations"""


class AssessmentParams(StudentIdParam):
    """Parameters for assessment operations"""

    feedback_level: str


class QuestionParams(BaseModel):
    """Parameters for question generation"""

    knowledge_point_ids: list[str]
    question_type: str
    difficulty: float | None
    cognitive_level: str | None
    num_questions: int


class DateRange(BaseModel):
    """Date range for filtering"""

    start_date: str
    end_date: str
    timezone: str = "UTC"


class FilterCriteria(BaseModel):
    """Filter criteria for RAG operations"""

    subject: str | None = None
    difficulty_level: str | None = None
    cognitive_level: str | None = None
    chapter: str | None = None
    section: str | None = None
    keywords: list[str] | None = None
    date_range: DateRange | None = None


class RAGParams(BaseModel):
    """Parameters for RAG operations"""

    user_query: str
    textbook_id: str | None
    filters: FilterCriteria | None


class DifficultyRange(BaseModel):
    """Difficulty range for question generation"""

    min_difficulty: float = Field(0.0, ge=0.0, le=1.0)
    max_difficulty: float = Field(1.0, ge=0.0, le=1.0)


class QuestionConstraints(BaseModel):
    """Additional constraints for question generation"""

    max_words: int | None = Field(
        None, ge=1, description="Maximum word count for question"
    )
    min_words: int | None = Field(
        None, ge=1, description="Minimum word count for question"
    )
    include_explanation: bool = Field(
        default=True, description="Include explanation with answer"
    )
    difficulty_range: DifficultyRange | None = Field(
        None, description="Allowed difficulty range"
    )
    banned_topics: list[str] | None = Field(None, description="Topics to avoid")
    required_keywords: list[str] | None = Field(
        None, description="Keywords that must appear"
    )
    language_style: str | None = Field(
        None, description="Language style (formal, casual, etc.)"
    )


# Question generation configuration model
class QuestionConfig(BaseModel):
    """Configuration for question generation"""

    difficulty: float | None = Field(
        None, ge=0.0, le=1.0, description="Target difficulty level (0.0-1.0)"
    )
    cognitive_level: str | None = Field(None, description="Target cognitive level")
    num_questions: int = Field(
        1, ge=1, le=100, description="Number of questions to generate"
    )
    constraints: QuestionConstraints | None = Field(
        None, description="Additional generation constraints"
    )


# Response models with concrete fields
class DifficultyMastery(BaseModel):
    """Mastery levels by difficulty"""

    easy_mastery: float = Field(0.0, ge=0.0, le=1.0)
    medium_mastery: float = Field(0.0, ge=0.0, le=1.0)
    hard_mastery: float = Field(0.0, ge=0.0, le=1.0)


class AnalyticsMetrics(BaseModel):
    """Analytics metrics for student performance"""

    accuracy_rate: float = Field(0.0, ge=0.0, le=1.0)
    average_time_seconds: float = Field(0.0, ge=0.0)
    total_questions_attempted: int = Field(0, ge=0)
    total_correct_answers: int = Field(0, ge=0)
    improvement_rate: float = Field(0.0, ge=-1.0, le=1.0)
    difficulty_mastery: DifficultyMastery | None = Field(
        None, description="Mastery by difficulty level"
    )


class AnalyticsResponse(BaseModel):
    """Response for analytics operations"""

    student_id: str
    metrics: AnalyticsMetrics
    insights: list[str]
    recommendations: list[str]
    time_period: str


class AssessmentResponse(BaseModel):
    """Response for assessment operations"""

    submission_id: str
    score: float
    feedback: str
    is_correct: bool
    feedback_level: str


class QuestionData(BaseModel):
    """Question data for validation operations"""

    question_id: str | None = None
    question_text: str
    question_type: str
    difficulty: float = Field(0.5, ge=0.0, le=1.0)
    cognitive_level: str
    subject: str | None = None
    options: list["OptionData"] | None = None
    correct_answer: str | None = None
    explanation: str | None = None
    solution_steps: list[str] | None = None


class OptionData(BaseModel):
    """Option data for multiple choice questions"""

    text: str
    is_correct: bool = False
    explanation: str | None = None


class DistractorData(BaseModel):
    """Distractor data for question generation"""

    text: str
    effectiveness_score: float = Field(0.5, ge=0.0, le=1.0)
    mistake_pattern: str | None = None
    explanation: str | None = None


class QuestionResponse(BaseModel):
    """Response for question operations"""

    question_id: str
    question_text: str
    question_type: str
    difficulty: float
    cognitive_level: str
    options: list[OptionData] | None
    correct_answer: str | None
    explanation: str | None


class RAGResponse(BaseModel):
    """Response for RAG operations"""

    query: str
    response: str
    sources: list["SourceData"]
    relevance_score: float
    textbook_id: str | None


# Error response model
class TextbookMetadata(BaseModel):
    """Textbook metadata for content extraction"""

    title: str
    author: str | None = None
    publisher: str | None = None
    subject: str
    grade_level: str
    file_type: str
    extraction_status: str = "pending"
    chapter_count: int | None = None
    extraction_progress: float = Field(0.0, ge=0.0, le=1.0)


class SubmissionData(BaseModel):
    """Student submission data for assessment"""

    submission_id: str
    student_id: str
    question_id: str
    answer_text: str
    is_correct: bool | None = None
    score: float = Field(0.0, ge=0.0)
    time_taken_seconds: float | None = None
    submitted_at: str
    feedback: str | None = None
    mistake_pattern: str | None = None


class SourceData(BaseModel):
    """Source data for RAG responses"""

    source_id: str
    title: str
    content: str
    page_number: int | None = None
    chapter: str | None = None
    section: str | None = None
    relevance_score: float = Field(0.0, ge=0.0, le=1.0)
    source_type: str = "textbook"


class ErrorDetails(BaseModel):
    """Detailed error information"""

    field_name: str | None = None
    validation_error: str | None = None
    suggested_fix: str | None = None
    error_code: str | None = None
    stack_trace: list[str] | None = None


class AssessmentCriteria(BaseModel):
    """Assessment criteria for evaluating student answers"""

    accuracy_weight: float = Field(0.6, ge=0.0, le=1.0)
    completeness_weight: float = Field(0.2, ge=0.0, le=1.0)
    clarity_weight: float = Field(0.2, ge=0.0, le=1.0)
    required_keywords: list[str] | None = None
    banned_keywords: list[str] | None = None
    min_word_count: int | None = Field(None, ge=1)
    max_word_count: int | None = Field(None, ge=1)


class MistakePattern(BaseModel):
    """Identified mistake pattern for a student"""

    pattern_id: str
    mistake_type: str
    frequency: float = Field(0.0, ge=0.0, le=1.0)
    description: str
    example_mistakes: list[str]
    suggested_corrections: list[str]
    knowledge_point_id: str | None = None


class KnowledgePointScore(BaseModel):
    """Score for a specific knowledge point"""

    knowledge_point_id: str
    knowledge_point_name: str
    score: float = Field(0.0, ge=0.0, le=1.0)
    attempts: int = Field(0, ge=0)
    improvement: float = Field(0.0, ge=-1.0, le=1.0)


class KnowledgePointScores(BaseModel):
    """Collection of knowledge point scores"""

    scores: list[KnowledgePointScore]
    average_score: float = Field(0.0, ge=0.0, le=1.0)
    strongest_areas: list[str] | None = None
    weakest_areas: list[str] | None = None


class LearningGap(BaseModel):
    """Identified learning gap for a student"""

    gap_id: str
    knowledge_point_id: str
    knowledge_point_name: str
    gap_severity: float = Field(0.5, ge=0.0, le=1.0)
    description: str
    suggested_resources: list[str]
    estimated_practice_time_hours: float = Field(1.0, ge=0.0)
    subject_area: str
    cognitive_level: str


class EngagementMetrics(BaseModel):
    """Student engagement metrics"""

    login_frequency: float = Field(0.0, ge=0.0, le=1.0)
    average_session_duration_minutes: float = Field(0.0, ge=0.0)
    questions_attempted_per_session: float = Field(0.0, ge=0.0)
    completion_rate: float = Field(0.0, ge=0.0, le=1.0)
    active_days_per_week: float = Field(0.0, ge=0.0, le=7.0)


class ClassAnalytics(BaseModel):
    """Analytics data for an entire class"""

    class_id: str
    total_students: int = Field(0, ge=0)
    average_accuracy: float = Field(0.0, ge=0.0, le=1.0)
    performance_distribution: dict[str, int] | None = (
        None  # TODO: Replace with concrete model
    )
    top_performers: list[str] | None = None
    struggling_students: list[str] | None = None
    common_learning_gaps: list[LearningGap] | None = None
    engagement_metrics: EngagementMetrics | None = None


class ProgressReport(BaseModel):
    """Student progress report"""

    student_id: str
    report_type: str
    generated_at: str
    overall_progress: float = Field(0.0, ge=0.0, le=1.0)
    subject_progress: dict[str, float] | None = (
        None  # TODO: Replace with concrete model
    )
    recent_achievements: list[str] | None = None
    areas_for_improvement: list[str] | None = None
    recommendations: list[str] | None = None


class PerformancePrediction(BaseModel):
    """Performance prediction data"""

    student_id: str
    prediction_timeframe: str
    predicted_accuracy: float = Field(0.0, ge=0.0, le=1.0)
    confidence_level: float = Field(0.5, ge=0.0, le=1.0)
    risk_factors: list[str] | None = None
    improvement_opportunities: list[str] | None = None
    historical_accuracy_trend: list[float] | None = None


class PerformanceMetrics(BaseModel):
    """Performance metrics for a student"""

    student_id: str
    overall_accuracy: float = Field(0.0, ge=0.0, le=1.0)
    total_attempts: int = Field(0, ge=0)
    correct_answers: int = Field(0, ge=0)
    average_time_seconds: float = Field(0.0, ge=0.0)
    improvement_trend: float = Field(0.0, ge=-1.0, le=1.0)
    knowledge_point_scores: KnowledgePointScores | None = None
    common_mistakes: list[MistakePattern] | None = None


class ToolParameters(BaseModel):
    """Generic tool parameters"""

    operation: str
    knowledge_point_ids: list[str] | None = None
    question_type: str | None = None
    question_text: str | None = None
    target_difficulty: float | None = None
    question_data: QuestionData | None = None


class ErrorResponse(BaseModel):
    """Error response"""

    error_type: str
    message: str
    details: ErrorDetails | None = None
