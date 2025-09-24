import uuid
from datetime import UTC, datetime

from fastapi import APIRouter

from eduagent.api.schemas import (
    CognitiveLevel,
    DifficultyLevel,
    ExerciseCreateRequest,
    ExerciseResponse,
    GeneratedQuestion,
    PracticeSessionRequest,
    PracticeSessionResponse,
    QuestionType,
    SubjectArea,
)

router = APIRouter()


@router.post("/exercises")
async def create_exercise(request: ExerciseCreateRequest) -> ExerciseResponse:
    """
    Create a new exercise with specific constraints
    """
    # Mock implementation
    return ExerciseResponse(
        id=str(uuid.uuid4()),
        title=request.title,
        description=request.description,
        subject=request.subject,
        difficulty=request.difficulty,
        question_ids=[str(uuid.uuid4()) for _ in range(request.num_questions)],
        created_at=datetime.now(UTC),
        created_by="teacher_123",
    )


@router.post("/practice/session")
async def start_practice_session(
    request: PracticeSessionRequest,
) -> PracticeSessionResponse:
    """
    Start a new practice session for students
    """
    # Mock implementation
    questions = [
        GeneratedQuestion(
            id=str(uuid.uuid4()),
            question_text=f"Practice question {i + 1}",
            question_type=QuestionType.MULTIPLE_CHOICE,
            difficulty=request.difficulty,
            cognitive_level=CognitiveLevel.UNDERSTANDING,
            knowledge_point_ids=request.knowledge_point_ids or ["kp_123"],
            estimated_difficulty=0.6,
            options=None,
            correct_answer=None,
            explanation=None,
            solution_steps=None,
        )
        for i in range(request.num_questions)
    ]

    return PracticeSessionResponse(
        session_id=str(uuid.uuid4()),
        questions=questions,
        started_at=datetime.now(UTC),
        time_limit=30,
    )


@router.get("/exercises/{exercise_id}")
async def get_exercise(exercise_id: str) -> ExerciseResponse:
    """
    Get exercise details
    """
    # Mock implementation
    return ExerciseResponse(
        id=exercise_id,
        title="Sample Exercise",
        description="Sample exercise description",
        subject=SubjectArea.MATH,
        difficulty=DifficultyLevel.MEDIUM,
        question_ids=[str(uuid.uuid4()) for _ in range(10)],
        created_at=datetime.now(UTC),
        created_by="teacher_123",
    )
