import uuid
from datetime import datetime
from enum import Enum as PyEnum

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
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

# Association tables for many-to-many relationships
question_knowledge_point_association = Table(
    "question_knowledge_point",
    Base.metadata,
    Column("question_id", ForeignKey("questions.id"), primary_key=True),
    Column("knowledge_point_id", ForeignKey("knowledge_points.id"), primary_key=True),
)

exercise_question_association = Table(
    "exercise_question",
    Base.metadata,
    Column("exercise_id", ForeignKey("exercises.id"), primary_key=True),
    Column("question_id", ForeignKey("questions.id"), primary_key=True),
)

user_class_association = Table(
    "user_class",
    Base.metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column("class_id", ForeignKey("classes.id"), primary_key=True),
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

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    grade_level = Column(String(20))
    subject_interests = Column(ARRAY(String))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)

    # Relationships
    classes = relationship(
        "Class", secondary=user_class_association, back_populates="users"
    )
    exercises_created = relationship("Exercise", back_populates="creator")
    practice_sessions = relationship("PracticeSession", back_populates="student")
    answer_submissions = relationship("AnswerSubmission", back_populates="student")


class Class(Base):
    __tablename__ = "classes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    grade_level = Column(String(20))
    subject = Column(Enum(SubjectArea))
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    users = relationship(
        "User", secondary=user_class_association, back_populates="classes"
    )
    teacher = relationship("User", foreign_keys=[teacher_id])
    exercises = relationship("Exercise", back_populates="class_obj")


class Textbook(Base):
    __tablename__ = "textbooks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False)
    author = Column(String(100))
    publisher = Column(String(100))
    subject = Column(Enum(SubjectArea), nullable=False)
    grade_level = Column(String(20))
    file_path = Column(String(255))
    file_type = Column(String(10))
    extraction_status = Column(
        String(20), default="pending"
    )  # pending, processing, completed, failed
    extracted_data = Column(JSON)  # Raw extracted data from GLM
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime)

    # Relationships
    knowledge_points = relationship("KnowledgePoint", back_populates="textbook")


class KnowledgePoint(Base):
    __tablename__ = "knowledge_points"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    textbook_id = Column(UUID(as_uuid=True), ForeignKey("textbooks.id"))
    name = Column(String(200), nullable=False)
    description = Column(Text)
    chapter = Column(String(100))
    section = Column(String(100))
    subject = Column(Enum(SubjectArea))
    cognitive_level = Column(Enum(CognitiveLevel))
    importance_score = Column(Float, default=0.5)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    textbook = relationship("Textbook", back_populates="knowledge_points")
    ability_targets = relationship("AbilityTarget", back_populates="knowledge_point")
    common_mistakes = relationship("CommonMistake", back_populates="knowledge_point")
    questions = relationship(
        "Question",
        secondary=question_knowledge_point_association,
        back_populates="knowledge_points",
    )


class AbilityTarget(Base):
    __tablename__ = "ability_targets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    knowledge_point_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_points.id"))
    cognitive_level = Column(Enum(CognitiveLevel), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    knowledge_point = relationship("KnowledgePoint", back_populates="ability_targets")


class CommonMistake(Base):
    __tablename__ = "common_mistakes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    knowledge_point_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_points.id"))
    pattern_name = Column(String(100), nullable=False)
    description = Column(Text)
    frequency = Column(Float, default=0.0)
    severity = Column(Float, default=0.5)
    examples = Column(JSON)  # Example mistakes and corrections
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    knowledge_point = relationship("KnowledgePoint", back_populates="common_mistakes")
    distractor_patterns = relationship(
        "DistractorPattern", back_populates="common_mistake"
    )


class Question(Base):
    __tablename__ = "questions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_text = Column(Text, nullable=False)
    question_type = Column(Enum(QuestionType), nullable=False)
    difficulty = Column(Enum(DifficultyLevel), default=DifficultyLevel.MEDIUM)
    cognitive_level = Column(Enum(CognitiveLevel))
    subject = Column(Enum(SubjectArea))
    options = Column(
        JSON
    )  # For multiple choice: [{text: str, correct: bool, mistake_pattern: str?}]
    correct_answer = Column(Text)
    explanation = Column(Text)
    solution_steps = Column(JSON)  # Step-by-step solution for complex problems
    estimated_difficulty = Column(Float, default=0.5)
    source_textbook_id = Column(UUID(as_uuid=True), ForeignKey("textbooks.id"))
    generated_by_ai = Column(Boolean, default=True)
    reviewed_by_teacher = Column(Boolean, default=False)
    review_notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    knowledge_points = relationship(
        "KnowledgePoint",
        secondary=question_knowledge_point_association,
        back_populates="questions",
    )
    source_textbook = relationship("Textbook")
    exercises = relationship(
        "Exercise", secondary=exercise_question_association, back_populates="questions"
    )
    answer_submissions = relationship("AnswerSubmission", back_populates="question")
    distractor_patterns = relationship("DistractorPattern", back_populates="question")


class DistractorPattern(Base):
    __tablename__ = "distractor_patterns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id = Column(UUID(as_uuid=True), ForeignKey("questions.id"))
    common_mistake_id = Column(UUID(as_uuid=True), ForeignKey("common_mistakes.id"))
    distractor_text = Column(Text, nullable=False)
    effectiveness_score = Column(Float, default=0.5)
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    question = relationship("Question", back_populates="distractor_patterns")
    common_mistake = relationship("CommonMistake", back_populates="distractor_patterns")


class Exercise(Base):
    __tablename__ = "exercises"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    subject = Column(Enum(SubjectArea))
    difficulty = Column(Enum(DifficultyLevel))
    class_id = Column(UUID(as_uuid=True), ForeignKey("classes.id"))
    creator_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    time_limit_minutes = Column(Integer)
    is_published = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    questions = relationship(
        "Question", secondary=exercise_question_association, back_populates="exercises"
    )
    class_obj = relationship("Class", back_populates="exercises")
    creator = relationship("User", back_populates="exercises_created")
    practice_sessions = relationship("PracticeSession", back_populates="exercise")


class PracticeSession(Base):
    __tablename__ = "practice_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    exercise_id = Column(UUID(as_uuid=True), ForeignKey("exercises.id"))
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    time_limit_minutes = Column(Integer)
    completed = Column(Boolean, default=False)
    total_score = Column(Float, default=0.0)
    accuracy = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    student = relationship("User", back_populates="practice_sessions")
    exercise = relationship("Exercise", back_populates="practice_sessions")
    answer_submissions = relationship(
        "AnswerSubmission", back_populates="practice_session"
    )


class AnswerSubmission(Base):
    __tablename__ = "answer_submissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    question_id = Column(UUID(as_uuid=True), ForeignKey("questions.id"))
    practice_session_id = Column(UUID(as_uuid=True), ForeignKey("practice_sessions.id"))
    answer_text = Column(Text)
    is_correct = Column(Boolean)
    score = Column(Float, default=0.0)
    time_taken_seconds = Column(Float)
    ai_feedback = Column(Text)
    mistake_pattern_id = Column(UUID(as_uuid=True), ForeignKey("common_mistakes.id"))
    submitted_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    student = relationship("User", back_populates="answer_submissions")
    question = relationship("Question", back_populates="answer_submissions")
    practice_session = relationship(
        "PracticeSession", back_populates="answer_submissions"
    )
    mistake_pattern = relationship("CommonMistake")


class AnalyticsSnapshot(Base):
    __tablename__ = "analytics_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    class_id = Column(UUID(as_uuid=True), ForeignKey("classes.id"))
    snapshot_type = Column(
        String(50)
    )  # daily, weekly, monthly, knowledge_point, overall
    data_period_start = Column(DateTime)
    data_period_end = Column(DateTime)
    analytics_data = Column(JSON)  # Comprehensive analytics data
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    student = relationship("User")
    class_obj = relationship("Class")
