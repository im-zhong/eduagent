"""Quiz models for storing generated and extracted educational questions."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for quiz models."""


# ============ SQLAlchemy Models ============


class Quiz(Base):
    """Unified quiz table for all quiz sources."""

    __tablename__ = "quiz"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("source_document.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source: Mapped[Literal["extracted", "generated", "user_created"]] = mapped_column(
        String(20), nullable=False
    )
    question_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    quiz_references: Mapped[list["QuizReference"]] = relationship(
        "QuizReference", back_populates="quiz", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Quiz(id={self.id}, doc_id={self.doc_id}, source='{self.source}')>"


class QuizReference(Base):
    """Reference text association for RAG-sourced quizzes."""

    __tablename__ = "quiz_reference"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quiz_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("quiz.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reference_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int | None] = mapped_column(Integer, nullable=True)

    quiz: Mapped[Quiz] = relationship("Quiz", back_populates="quiz_references")

    def __repr__(self) -> str:
        return f"<QuizReference(id={self.id}, quiz_id={self.quiz_id})>"


# ============ Pydantic Models ============


class SingleChoiceOption(BaseModel):
    """A single option in a multiple choice question."""

    label: str = Field(..., description="Option label (A, B, C, D)")
    text: str = Field(..., description="Option text content")


class SingleChoiceQuestion(BaseModel):
    """A single-choice question with multiple options."""

    question: str = Field(..., description="The question text/stem")
    options: list[SingleChoiceOption] = Field(
        ..., min_length=4, max_length=4, description="Exactly 4 options"
    )
    correct_answer: Literal["A", "B", "C", "D"] = Field(
        ..., description="Label of the correct answer"
    )
    explanation: str = Field(..., description="Brief explanation of the correct answer")


class QuizGenerationRequest(BaseModel):
    """Schema for requesting quiz generation."""

    doc_id: int = Field(..., gt=0, description="Source document ID")
    topic: str = Field(..., min_length=1, description="Topic or query for question generation")
    count: int = Field(default=1, ge=1, le=5, description="Number of questions to generate")


class QuizGenerationResponse(BaseModel):
    """Schema for quiz generation response."""

    doc_id: int
    questions: list[SingleChoiceQuestion]
    quiz_ids: list[int]


class QuizResponse(BaseModel):
    """Schema for a quiz record."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    doc_id: int
    source: str
    question_json: str
    created_at: datetime


class QuizWithReferenceResponse(BaseModel):
    """Schema for a quiz with its reference text."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    doc_id: int
    source: str
    question_json: str
    references: list[str]
    created_at: datetime


class QuizListResponse(BaseModel):
    """Schema for listing quizzes for a document."""

    doc_id: int
    quizzes: list[QuizWithReferenceResponse]
