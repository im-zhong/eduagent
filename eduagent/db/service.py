import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Protocol, TypeVar

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload, sessionmaker

from .models import (
    AnalyticsSnapshot,
    AnswerSubmission,
    Base,
    CommonMistake,
    DifficultyLevel,
    Exercise,
    KnowledgePoint,
    PracticeSession,
    Question,
    QuestionType,
    SubjectArea,
    Textbook,
    User,
    UserRole,
)

if TYPE_CHECKING:
    pass


class ModelWithId(Protocol):
    id: uuid.UUID


T = TypeVar("T", bound=Base)


class DatabaseService:
    """
    Abstract database service class that provides high-level operations
    for the educational AI system, encapsulating SQLAlchemy operations.
    """

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    # ============ Generic CRUD Operations ============

    def create(self, model_instance: Base) -> Base:
        """Create a new database record"""
        with self.session_factory() as session:
            try:
                session.add(model_instance)
                session.commit()
                session.refresh(model_instance)
            except SQLAlchemyError:
                session.rollback()
                raise
            return model_instance

    def get_all(
        self, model_class: type[T], limit: int = 100, offset: int = 0
    ) -> list[T]:
        """Retrieve all records of a type with pagination"""
        with self.session_factory() as session:
            return session.query(model_class).limit(limit).offset(offset).all()

    def update(self, model_instance: Base) -> Base:
        """Update an existing record"""
        with self.session_factory() as session:
            try:
                session.merge(model_instance)
                session.commit()
                session.refresh(model_instance)
            except SQLAlchemyError:
                session.rollback()
                raise
            return model_instance

    def delete(self, model_instance: Base) -> bool:
        """Delete a record"""
        with self.session_factory() as session:
            try:
                session.delete(model_instance)
                session.commit()
            except SQLAlchemyError:
                session.rollback()
                raise
            return True

    # ============ User Management Operations ============

    def get_user_by_username(self, username: str) -> User | None:
        """Find user by username"""
        with self.session_factory() as session:
            return session.query(User).filter(User.username == username).first()

    def get_user_by_email(self, email: str) -> User | None:
        """Find user by email"""
        with self.session_factory() as session:
            return session.query(User).filter(User.email == email).first()

    def get_users_by_role(self, role: UserRole, limit: int = 100) -> list[User]:
        """Get all users with a specific role"""
        with self.session_factory() as session:
            return session.query(User).filter(User.role == role).limit(limit).all()

    def update_user_last_login(self, user_id: uuid.UUID) -> None:
        """Update user's last login timestamp"""
        with self.session_factory() as session:
            try:
                session.query(User).filter(User.id == user_id).update(
                    {User.last_login: datetime.now(UTC)}
                )
                session.commit()
            except SQLAlchemyError:
                session.rollback()
                raise

    # ============ Textbook & Knowledge Operations ============

    def get_textbook_by_subject(
        self, subject: SubjectArea, grade_level: str | None = None
    ) -> list[Textbook]:
        """Get textbooks by subject and optionally grade level"""
        with self.session_factory() as session:
            query = session.query(Textbook).filter(Textbook.subject == subject)
            if grade_level:
                query = query.filter(Textbook.grade_level == grade_level)
            return query.all()

    def get_knowledge_points_by_textbook(
        self, textbook_id: uuid.UUID
    ) -> list[KnowledgePoint]:
        """Get all knowledge points for a textbook"""
        with self.session_factory() as session:
            return (
                session.query(KnowledgePoint)
                .filter(KnowledgePoint.textbook_id == textbook_id)
                .all()
            )

    def get_knowledge_point_with_relationships(
        self, knowledge_point_id: uuid.UUID
    ) -> KnowledgePoint | None:
        """Get knowledge point with ability targets and common mistakes"""
        with self.session_factory() as session:
            return (
                session.query(KnowledgePoint)
                .options(
                    joinedload(KnowledgePoint.ability_targets),
                    joinedload(KnowledgePoint.common_mistakes),
                )
                .filter(KnowledgePoint.id == knowledge_point_id)
                .first()
            )

    def update_textbook_extraction_status(
        self, textbook_id: uuid.UUID, status: str
    ) -> None:
        """Update textbook extraction status"""
        with self.session_factory() as session:
            try:
                if status == "completed":
                    session.query(Textbook).filter(Textbook.id == textbook_id).update(
                        {
                            Textbook.extraction_status: status,
                            Textbook.processed_at: datetime.now(UTC),
                        }
                    )
                else:
                    session.query(Textbook).filter(Textbook.id == textbook_id).update(
                        {Textbook.extraction_status: status}
                    )
                session.commit()
            except SQLAlchemyError:
                session.rollback()
                raise

    # ============ Question Operations ============

    def get_questions_by_knowledge_points(
        self,
        knowledge_point_ids: list[uuid.UUID],
        difficulty: DifficultyLevel | None = None,
        question_type: QuestionType | None = None,
    ) -> list[Question]:
        """Get questions associated with specific knowledge points"""
        with self.session_factory() as session:
            query = (
                session.query(Question)
                .join(Question.knowledge_points)
                .filter(KnowledgePoint.id.in_(knowledge_point_ids))
            )

            if difficulty:
                query = query.filter(Question.difficulty == difficulty)
            if question_type:
                query = query.filter(Question.question_type == question_type)

            return query.all()

    def get_ai_generated_questions(
        self, *, reviewed: bool | None = None
    ) -> list[Question]:
        """Get AI-generated questions, optionally filtered by review status"""
        with self.session_factory() as session:
            query = session.query(Question).filter(Question.generated_by_ai)
            if reviewed is not None:
                query = query.filter(Question.reviewed_by_teacher == reviewed)
            return query.all()

    def mark_question_reviewed(
        self, question_id: uuid.UUID, notes: str | None = None
    ) -> None:
        """Mark a question as reviewed by teacher"""
        with self.session_factory() as session:
            try:
                session.query(Question).filter(Question.id == question_id).update(
                    {
                        Question.reviewed_by_teacher: True,
                        Question.review_notes: notes,
                    }
                )
                session.commit()
            except SQLAlchemyError:
                session.rollback()
                raise

    # ============ Exercise & Practice Operations ============

    def create_exercise_with_questions(
        self, exercise_data: dict[str, Any], question_ids: list[uuid.UUID]
    ) -> Exercise:
        """Create an exercise and associate questions with it"""
        with self.session_factory() as session:
            try:
                exercise = Exercise(**exercise_data)
                session.add(exercise)
                session.flush()  # Get the exercise ID

                # Associate questions
                for question_id in question_ids:
                    session.execute(
                        text(
                            "INSERT INTO exercise_question (exercise_id, question_id) VALUES (:ex_id, :q_id)"
                        ),
                        {"ex_id": exercise.id, "q_id": question_id},
                    )

                session.commit()
                session.refresh(exercise)
            except SQLAlchemyError:
                session.rollback()
                raise
            return exercise

    def get_exercise_with_questions(self, exercise_id: uuid.UUID) -> Exercise | None:
        """Get exercise with all associated questions"""
        with self.session_factory() as session:
            return (
                session.query(Exercise)
                .options(joinedload(Exercise.questions))
                .filter(Exercise.id == exercise_id)
                .first()
            )

    def start_practice_session(
        self, student_id: uuid.UUID, exercise_id: uuid.UUID
    ) -> PracticeSession:
        """Start a new practice session for a student"""
        with self.session_factory() as session:
            try:
                exercise = (
                    session.query(Exercise).filter(Exercise.id == exercise_id).first()
                )
                if not exercise:
                    raise ValueError

                session_obj = PracticeSession(
                    student_id=student_id,
                    exercise_id=exercise_id,
                    time_limit_minutes=exercise.time_limit_minutes,
                )
                session.add(session_obj)
                session.commit()
                session.refresh(session_obj)
            except SQLAlchemyError:
                session.rollback()
                raise
            return session_obj

    def complete_practice_session(
        self, session_id: uuid.UUID, total_score: float, accuracy: float
    ) -> None:
        """Mark practice session as completed with results"""
        with self.session_factory() as session:
            try:
                session.query(PracticeSession).filter(
                    PracticeSession.id == session_id
                ).update(
                    {
                        PracticeSession.end_time: datetime.now(UTC),
                        PracticeSession.completed: True,
                        PracticeSession.total_score: total_score,
                        PracticeSession.accuracy: accuracy,
                    }
                )
                session.commit()
            except SQLAlchemyError:
                session.rollback()
                raise

    # ============ Assessment & Analytics Operations ============

    def submit_answer(self, submission_data: dict[str, Any]) -> AnswerSubmission:
        """Submit student answer and get AI assessment"""
        with self.session_factory() as session:
            try:
                submission = AnswerSubmission(**submission_data)
                session.add(submission)
                session.commit()
                session.refresh(submission)
            except SQLAlchemyError:
                session.rollback()
                raise
            return submission

    def get_student_performance(
        self,
        student_id: uuid.UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, Any]:
        """Get comprehensive performance data for a student"""
        with self.session_factory() as session:
            query = session.query(AnswerSubmission).filter(
                AnswerSubmission.student_id == student_id
            )

            if start_date:
                query = query.filter(AnswerSubmission.submitted_at >= start_date)
            if end_date:
                query = query.filter(AnswerSubmission.submitted_at <= end_date)

            submissions = query.all()

            if not submissions:
                return {"total_attempts": 0, "accuracy": 0.0, "average_score": 0.0}

            total_attempts = len(submissions)
            correct_attempts = sum(1 for s in submissions if s.is_correct)
            average_score = sum(s.score for s in submissions) / total_attempts

            return {
                "total_attempts": total_attempts,
                "accuracy": correct_attempts / total_attempts,
                "average_score": average_score,
                "submission_count": total_attempts,
            }

    def get_common_mistakes_by_knowledge_point(
        self, knowledge_point_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        """Get common mistakes and their frequency for a knowledge point"""
        with self.session_factory() as session:
            result = (
                session.query(
                    CommonMistake.pattern_name,
                    CommonMistake.description,
                    CommonMistake.frequency,
                )
                .filter(CommonMistake.knowledge_point_id == knowledge_point_id)
                .all()
            )

            return [
                {"pattern": r[0], "description": r[1], "frequency": r[2]}
                for r in result
            ]

    def save_analytics_snapshot(
        self, snapshot_data: dict[str, Any]
    ) -> AnalyticsSnapshot:
        """Save analytics snapshot for reporting"""
        with self.session_factory() as session:
            try:
                snapshot = AnalyticsSnapshot(**snapshot_data)
                session.add(snapshot)
                session.commit()
                session.refresh(snapshot)
            except SQLAlchemyError:
                session.rollback()
                raise
            return snapshot

    # ============ Advanced Query Operations ============

    def search_questions(
        self, search_criteria: dict[str, Any], limit: int = 50
    ) -> list[Question]:
        """Advanced search for questions with multiple criteria"""
        with self.session_factory() as session:
            query = session.query(Question)

            if "subject" in search_criteria:
                query = query.filter(Question.subject == search_criteria["subject"])
            if "difficulty" in search_criteria:
                query = query.filter(
                    Question.difficulty == search_criteria["difficulty"]
                )
            if "question_type" in search_criteria:
                query = query.filter(
                    Question.question_type == search_criteria["question_type"]
                )
            if "cognitive_level" in search_criteria:
                query = query.filter(
                    Question.cognitive_level == search_criteria["cognitive_level"]
                )
            if "reviewed" in search_criteria:
                query = query.filter(
                    Question.reviewed_by_teacher == search_criteria["reviewed"]
                )

            return query.limit(limit).all()

    def get_knowledge_graph_data(self, textbook_id: uuid.UUID) -> dict[str, Any]:
        """Get complete knowledge graph data for a textbook"""
        with self.session_factory() as session:
            knowledge_points = (
                session.query(KnowledgePoint)
                .filter(KnowledgePoint.textbook_id == textbook_id)
                .all()
            )

            graph_data: dict[str, list[dict[str, str]]] = {"nodes": [], "links": []}

            for kp in knowledge_points:
                graph_data["nodes"].append(
                    {
                        "id": str(kp.id),
                        "name": kp.name,
                        "type": "knowledge_point",
                        "subject": kp.subject.value if kp.subject else "",
                    }
                )

            return graph_data

    # ============ Batch Operations ============

    def batch_create_questions(
        self, questions_data: list[dict[str, Any]]
    ) -> list[Question]:
        """Batch create multiple questions"""
        with self.session_factory() as session:
            try:
                questions: list[Question] = []
                for data in questions_data:
                    question = Question(**data)
                    session.add(question)
                    questions.append(question)

                session.commit()

                # Refresh all questions to get their IDs
                for question in questions:
                    session.refresh(question)

            except SQLAlchemyError:
                session.rollback()
                raise
            return questions

    def batch_associate_questions_knowledge_points(
        self, associations: list[dict[str, uuid.UUID]]
    ) -> None:
        """Batch associate questions with knowledge points"""
        with self.session_factory() as session:
            try:
                for assoc in associations:
                    session.execute(
                        text(
                            "INSERT INTO question_knowledge_point (question_id, knowledge_point_id) VALUES (:q_id, :kp_id)"
                        ),
                        {
                            "q_id": assoc["question_id"],
                            "kp_id": assoc["knowledge_point_id"],
                        },
                    )
                session.commit()
            except SQLAlchemyError:
                session.rollback()
                raise
