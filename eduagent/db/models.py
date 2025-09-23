import uuid
from datetime import UTC, datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    ARRAY,
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)

if TYPE_CHECKING:
    pass


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models using 2.0 style"""


# Association tables for many-to-many relationships
question_knowledge_point_association = Table(
    "question_knowledge_point",
    Base.metadata,
    Column(
        "question_id", UUID(as_uuid=True), ForeignKey("questions.id"), primary_key=True
    ),
    Column(
        "knowledge_point_id",
        UUID(as_uuid=True),
        ForeignKey("knowledge_points.id"),
        primary_key=True,
    ),
)

exercise_question_association = Table(
    "exercise_question",
    Base.metadata,
    Column(
        "exercise_id", UUID(as_uuid=True), ForeignKey("exercises.id"), primary_key=True
    ),
    Column(
        "question_id", UUID(as_uuid=True), ForeignKey("questions.id"), primary_key=True
    ),
)

user_class_association = Table(
    "user_class",
    Base.metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True),
    Column("class_id", UUID(as_uuid=True), ForeignKey("classes.id"), primary_key=True),
)


class UserRole(PyEnum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"


class DifficultyLevel(PyEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class QuestionType(PyEnum):
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    SHORT_ANSWER = "short_answer"
    ESSAY = "essay"
    FILL_IN_BLANK = "fill_in_blank"
    CALCULATION = "calculation"


class CognitiveLevel(PyEnum):
    MEMORY = "memory"
    UNDERSTANDING = "understanding"
    APPLICATION = "application"
    ANALYSIS = "analysis"
    EVALUATION = "evaluation"
    CREATION = "creation"


class SubjectArea(PyEnum):
    MATH = "math"
    SCIENCE = "science"
    HISTORY = "history"
    LANGUAGE = "language"
    COMPUTER_SCIENCE = "computer_science"
    PHYSICS = "physics"
    CHEMISTRY = "chemistry"
    BIOLOGY = "biology"
    GENERAL = "general"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    grade_level: Mapped[str | None] = mapped_column(String(20))
    subject_interests: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )
    last_login: Mapped[datetime | None] = mapped_column(DateTime)

    # Relationships
    classes: Mapped[list["Class"]] = relationship(
        "Class", secondary=user_class_association, back_populates="users"
    )
    exercises_created: Mapped[list["Exercise"]] = relationship(
        "Exercise", back_populates="creator"
    )
    practice_sessions: Mapped[list["PracticeSession"]] = relationship(
        "PracticeSession", back_populates="student"
    )
    answer_submissions: Mapped[list["AnswerSubmission"]] = relationship(
        "AnswerSubmission", back_populates="student"
    )


class Class(Base):
    __tablename__ = "classes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    grade_level: Mapped[str | None] = mapped_column(String(20))
    subject: Mapped[SubjectArea | None] = mapped_column(Enum(SubjectArea))
    teacher_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )

    # Relationships
    users: Mapped[list["User"]] = relationship(
        "User", secondary=user_class_association, back_populates="classes"
    )
    teacher: Mapped["User | None"] = relationship("User", foreign_keys=[teacher_id])
    exercises: Mapped[list["Exercise"]] = relationship(
        "Exercise", back_populates="class_obj"
    )


class Textbook(Base):
    __tablename__ = "textbooks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    author: Mapped[str | None] = mapped_column(String(100))
    publisher: Mapped[str | None] = mapped_column(String(100))
    subject: Mapped[SubjectArea] = mapped_column(Enum(SubjectArea), nullable=False)
    grade_level: Mapped[str | None] = mapped_column(String(20))
    file_path: Mapped[str | None] = mapped_column(String(255))
    file_type: Mapped[str | None] = mapped_column(String(10))
    extraction_status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # pending, processing, completed, failed
    extracted_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON
    )  # Raw extracted data from GLM
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Relationships
    knowledge_points: Mapped[list["KnowledgePoint"]] = relationship(
        "KnowledgePoint", back_populates="textbook"
    )


class KnowledgePoint(Base):
    __tablename__ = "knowledge_points"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    textbook_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("textbooks.id"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    chapter: Mapped[str | None] = mapped_column(String(100))
    section: Mapped[str | None] = mapped_column(String(100))
    subject: Mapped[SubjectArea | None] = mapped_column(Enum(SubjectArea))
    cognitive_level: Mapped[CognitiveLevel | None] = mapped_column(Enum(CognitiveLevel))
    importance_score: Mapped[float] = mapped_column(Float, default=0.5)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )

    # Relationships
    textbook: Mapped["Textbook | None"] = relationship(
        "Textbook", back_populates="knowledge_points"
    )
    ability_targets: Mapped[list["AbilityTarget"]] = relationship(
        "AbilityTarget", back_populates="knowledge_point"
    )
    common_mistakes: Mapped[list["CommonMistake"]] = relationship(
        "CommonMistake", back_populates="knowledge_point"
    )
    questions: Mapped[list["Question"]] = relationship(
        "Question",
        secondary=question_knowledge_point_association,
        back_populates="knowledge_points",
    )


class AbilityTarget(Base):
    __tablename__ = "ability_targets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    knowledge_point_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_points.id")
    )
    cognitive_level: Mapped[CognitiveLevel] = mapped_column(
        Enum(CognitiveLevel), nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )

    # Relationships
    knowledge_point: Mapped["KnowledgePoint"] = relationship(
        "KnowledgePoint", back_populates="ability_targets"
    )


class CommonMistake(Base):
    __tablename__ = "common_mistakes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    knowledge_point_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_points.id")
    )
    pattern_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    frequency: Mapped[float] = mapped_column(Float, default=0.0)
    severity: Mapped[float] = mapped_column(Float, default=0.5)
    examples: Mapped[dict[str, Any] | None] = mapped_column(
        JSON
    )  # Example mistakes and corrections
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )

    # Relationships
    knowledge_point: Mapped["KnowledgePoint"] = relationship(
        "KnowledgePoint", back_populates="common_mistakes"
    )
    distractor_patterns: Mapped[list["DistractorPattern"]] = relationship(
        "DistractorPattern", back_populates="common_mistake"
    )


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[QuestionType] = mapped_column(
        Enum(QuestionType), nullable=False
    )
    difficulty: Mapped[DifficultyLevel] = mapped_column(
        Enum(DifficultyLevel), default=DifficultyLevel.MEDIUM
    )
    cognitive_level: Mapped[CognitiveLevel | None] = mapped_column(Enum(CognitiveLevel))
    subject: Mapped[SubjectArea | None] = mapped_column(Enum(SubjectArea))
    options: Mapped[dict[str, Any] | None] = mapped_column(
        JSON
    )  # For multiple choice: [{text: str, correct: bool, mistake_pattern: str?}]
    correct_answer: Mapped[str | None] = mapped_column(Text)
    explanation: Mapped[str | None] = mapped_column(Text)
    solution_steps: Mapped[dict[str, Any] | None] = mapped_column(
        JSON
    )  # Step-by-step solution for complex problems
    estimated_difficulty: Mapped[float] = mapped_column(Float, default=0.5)
    source_textbook_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("textbooks.id")
    )
    generated_by_ai: Mapped[bool] = mapped_column(Boolean, default=True)
    reviewed_by_teacher: Mapped[bool] = mapped_column(Boolean, default=False)
    review_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )

    # Relationships
    knowledge_points: Mapped[list["KnowledgePoint"]] = relationship(
        "KnowledgePoint",
        secondary=question_knowledge_point_association,
        back_populates="questions",
    )
    source_textbook: Mapped["Textbook | None"] = relationship("Textbook")
    exercises: Mapped[list["Exercise"]] = relationship(
        "Exercise", secondary=exercise_question_association, back_populates="questions"
    )
    answer_submissions: Mapped[list["AnswerSubmission"]] = relationship(
        "AnswerSubmission", back_populates="question"
    )
    distractor_patterns: Mapped[list["DistractorPattern"]] = relationship(
        "DistractorPattern", back_populates="question"
    )


class DistractorPattern(Base):
    __tablename__ = "distractor_patterns"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    question_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("questions.id"))
    common_mistake_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("common_mistakes.id")
    )
    distractor_text: Mapped[str] = mapped_column(Text, nullable=False)
    effectiveness_score: Mapped[float] = mapped_column(Float, default=0.5)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )

    # Relationships
    question: Mapped["Question"] = relationship(
        "Question", back_populates="distractor_patterns"
    )
    common_mistake: Mapped["CommonMistake"] = relationship(
        "CommonMistake", back_populates="distractor_patterns"
    )


class Exercise(Base):
    __tablename__ = "exercises"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    subject: Mapped[SubjectArea | None] = mapped_column(Enum(SubjectArea))
    difficulty: Mapped[DifficultyLevel | None] = mapped_column(Enum(DifficultyLevel))
    class_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("classes.id"))
    creator_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    time_limit_minutes: Mapped[int | None] = mapped_column(Integer)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )

    # Relationships
    questions: Mapped[list["Question"]] = relationship(
        "Question", secondary=exercise_question_association, back_populates="exercises"
    )
    class_obj: Mapped["Class | None"] = relationship(
        "Class", back_populates="exercises"
    )
    creator: Mapped["User | None"] = relationship(
        "User", back_populates="exercises_created"
    )
    practice_sessions: Mapped[list["PracticeSession"]] = relationship(
        "PracticeSession", back_populates="exercise"
    )


class PracticeSession(Base):
    __tablename__ = "practice_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    exercise_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exercises.id"))
    start_time: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )
    end_time: Mapped[datetime | None] = mapped_column(DateTime)
    time_limit_minutes: Mapped[int | None] = mapped_column(Integer)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    total_score: Mapped[float] = mapped_column(Float, default=0.0)
    accuracy: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )

    # Relationships
    student: Mapped["User"] = relationship("User", back_populates="practice_sessions")
    exercise: Mapped["Exercise"] = relationship(
        "Exercise", back_populates="practice_sessions"
    )
    answer_submissions: Mapped[list["AnswerSubmission"]] = relationship(
        "AnswerSubmission", back_populates="practice_session"
    )


class AnswerSubmission(Base):
    __tablename__ = "answer_submissions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    question_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("questions.id"))
    practice_session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("practice_sessions.id")
    )
    answer_text: Mapped[str | None] = mapped_column(Text)
    is_correct: Mapped[bool | None] = mapped_column(Boolean)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    time_taken_seconds: Mapped[float | None] = mapped_column(Float)
    ai_feedback: Mapped[str | None] = mapped_column(Text)
    mistake_pattern_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("common_mistakes.id")
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )

    # Relationships
    student: Mapped["User"] = relationship("User", back_populates="answer_submissions")
    question: Mapped["Question"] = relationship(
        "Question", back_populates="answer_submissions"
    )
    practice_session: Mapped["PracticeSession | None"] = relationship(
        "PracticeSession", back_populates="answer_submissions"
    )
    mistake_pattern: Mapped["CommonMistake | None"] = relationship("CommonMistake")


class AnalyticsSnapshot(Base):
    __tablename__ = "analytics_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    student_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    class_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("classes.id"))
    snapshot_type: Mapped[str] = mapped_column(
        String(50)
    )  # daily, weekly, monthly, knowledge_point, overall
    data_period_start: Mapped[datetime | None] = mapped_column(DateTime)
    data_period_end: Mapped[datetime | None] = mapped_column(DateTime)
    analytics_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON
    )  # Comprehensive analytics data
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )

    # Relationships
    student: Mapped["User | None"] = relationship("User")
    class_obj: Mapped["Class | None"] = relationship("Class")
