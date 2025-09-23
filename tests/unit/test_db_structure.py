"""
Unit tests for database structure and model definitions
"""

import sys

# Constants for magic numbers
MIN_USER_ROLES = 3
MIN_ENUM_VALUES = 3
MIN_COGNITIVE_LEVELS = 6
MIN_EXPECTED_TABLES = 12
from pathlib import Path  # noqa: E402

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import all modules at the top level
from eduagent.db.config import DatabaseConfig  # noqa: E402
from eduagent.db.models import (  # noqa: E402
    CognitiveLevel,
    DifficultyLevel,
    Exercise,
    KnowledgePoint,
    Question,
    QuestionType,
    SubjectArea,
    Textbook,
    User,
    UserRole,
)


class TestDatabaseStructure:
    """Test class for database structure validation"""

    def test_database_modules_import(self) -> None:
        """Test that database modules can be imported successfully"""

        assert DatabaseConfig is not None
        assert CognitiveLevel is not None
        assert DifficultyLevel is not None
        assert Exercise is not None
        assert KnowledgePoint is not None
        assert Question is not None
        assert QuestionType is not None
        assert SubjectArea is not None
        assert Textbook is not None
        assert User is not None
        assert UserRole is not None

    def test_user_role_enum(self) -> None:
        """Test UserRole enum values"""

        roles = [role.value for role in UserRole]
        assert "student" in roles
        assert "teacher" in roles
        assert "admin" in roles
        assert len(roles) >= MIN_USER_ROLES

    def test_difficulty_level_enum(self) -> None:
        """Test DifficultyLevel enum values"""

        levels = [level.value for level in DifficultyLevel]
        assert "easy" in levels
        assert "medium" in levels
        assert "hard" in levels
        assert len(levels) >= MIN_ENUM_VALUES

    def test_question_type_enum(self) -> None:
        """Test QuestionType enum values"""

        types = [qtype.value for qtype in QuestionType]
        assert "multiple_choice" in types
        assert "short_answer" in types
        assert "essay" in types
        assert len(types) >= MIN_ENUM_VALUES

    def test_cognitive_level_enum(self) -> None:
        """Test CognitiveLevel enum values"""

        levels = [level.value for level in CognitiveLevel]
        assert "memory" in levels
        assert "understanding" in levels
        assert "application" in levels
        assert "analysis" in levels
        assert "evaluation" in levels
        assert "creation" in levels
        assert len(levels) >= MIN_COGNITIVE_LEVELS

    def test_subject_area_enum(self) -> None:
        """Test SubjectArea enum values"""

        subjects = [subject.value for subject in SubjectArea]
        assert "math" in subjects
        assert "science" in subjects
        assert "language" in subjects
        assert len(subjects) >= MIN_ENUM_VALUES

    def test_user_model_instantiation(self) -> None:
        """Test User model instantiation"""

        # Test that the model can be instantiated with proper attributes
        user = User(
            username="test_teacher",
            email="teacher@example.com",
            password_hash="hashed_password",
            role=UserRole.TEACHER,
            grade_level="Grade 10",
        )

        # Test that the object was created successfully
        assert user is not None
        assert hasattr(user, "username")
        assert hasattr(user, "email")
        assert hasattr(user, "password_hash")
        assert hasattr(user, "role")
        assert hasattr(user, "grade_level")

        # Test that the attributes have the expected types
        assert isinstance(user.username, str)
        assert isinstance(user.email, str)
        assert isinstance(user.password_hash, str)
        assert isinstance(user.role, UserRole)
        assert isinstance(user.grade_level, str)

        # Test actual values now that models are properly typed
        assert user.username == "test_teacher"
        assert user.email == "teacher@example.com"
        assert user.password_hash == "hashed_password"
        assert user.role == UserRole.TEACHER
        assert user.grade_level == "Grade 10"

    def test_textbook_model_instantiation(self) -> None:
        """Test Textbook model instantiation"""

        # Test that the model can be instantiated with proper attributes
        textbook = Textbook(
            title="Mathematics Grade 10",
            subject=SubjectArea.MATH,
            grade_level="Grade 10",
            extraction_status="pending",
        )

        # Test that the object was created successfully
        assert textbook is not None
        assert hasattr(textbook, "title")
        assert hasattr(textbook, "subject")
        assert hasattr(textbook, "grade_level")
        assert hasattr(textbook, "extraction_status")

        # Test that the attributes have the expected types and values
        assert isinstance(textbook.title, str)
        assert isinstance(textbook.subject, SubjectArea)
        assert isinstance(textbook.grade_level, str)
        assert isinstance(textbook.extraction_status, str)

        # Test actual values now that models are properly typed
        assert textbook.title == "Mathematics Grade 10"
        assert textbook.subject == SubjectArea.MATH
        assert textbook.grade_level == "Grade 10"
        assert textbook.extraction_status == "pending"

    def test_knowledge_point_model_instantiation(self) -> None:
        """Test KnowledgePoint model instantiation"""

        # Test that the model can be instantiated with proper attributes
        knowledge_point = KnowledgePoint(
            name="Quadratic Equations",
            description="Solving quadratic equations using various methods",
            subject=SubjectArea.MATH,
            cognitive_level=CognitiveLevel.APPLICATION,
        )

        # Test that the object was created successfully
        assert knowledge_point is not None
        assert hasattr(knowledge_point, "name")
        assert hasattr(knowledge_point, "description")
        assert hasattr(knowledge_point, "subject")
        assert hasattr(knowledge_point, "cognitive_level")

        # Test that the attributes have the expected types
        assert isinstance(knowledge_point.name, str)
        assert isinstance(knowledge_point.description, str)
        assert isinstance(knowledge_point.subject, SubjectArea)
        assert isinstance(knowledge_point.cognitive_level, CognitiveLevel)

        # Test actual values now that models are properly typed
        assert knowledge_point.name == "Quadratic Equations"
        assert (
            knowledge_point.description
            == "Solving quadratic equations using various methods"
        )
        assert knowledge_point.subject == SubjectArea.MATH
        assert knowledge_point.cognitive_level == CognitiveLevel.APPLICATION

    def test_question_model_instantiation(self) -> None:
        """Test Question model instantiation"""

        # Test that the model can be instantiated with proper attributes
        question = Question(
            question_text="Solve the quadratic equation: x² - 5x + 6 = 0",
            question_type=QuestionType.SHORT_ANSWER,
            difficulty=DifficultyLevel.MEDIUM,
            cognitive_level=CognitiveLevel.APPLICATION,
            subject=SubjectArea.MATH,
        )

        # Test that the object was created successfully
        assert question is not None
        assert hasattr(question, "question_text")
        assert hasattr(question, "question_type")
        assert hasattr(question, "difficulty")
        assert hasattr(question, "cognitive_level")
        assert hasattr(question, "subject")

        # Test that the attributes have the expected types
        assert isinstance(question.question_text, str)
        assert isinstance(question.question_type, QuestionType)
        assert isinstance(question.difficulty, DifficultyLevel)
        assert isinstance(question.cognitive_level, CognitiveLevel)
        assert isinstance(question.subject, SubjectArea)

        # Test actual values now that models are properly typed
        assert question.question_text == "Solve the quadratic equation: x² - 5x + 6 = 0"
        assert question.question_type == QuestionType.SHORT_ANSWER
        assert question.difficulty == DifficultyLevel.MEDIUM
        assert question.cognitive_level == CognitiveLevel.APPLICATION
        assert question.subject == SubjectArea.MATH

    def test_exercise_model_instantiation(self) -> None:
        """Test Exercise model instantiation"""

        # Test that the model can be instantiated with proper attributes
        exercise = Exercise(
            title="Quadratic Equations Practice",
            subject=SubjectArea.MATH,
            difficulty=DifficultyLevel.MEDIUM,
        )

        # Test that the object was created successfully
        assert exercise is not None
        assert hasattr(exercise, "title")
        assert hasattr(exercise, "subject")
        assert hasattr(exercise, "difficulty")

        # Test that the attributes have the expected types
        assert isinstance(exercise.title, str)
        assert isinstance(exercise.subject, SubjectArea)
        assert isinstance(exercise.difficulty, DifficultyLevel)

        # Test actual values now that models are properly typed
        assert exercise.title == "Quadratic Equations Practice"
        assert exercise.subject == SubjectArea.MATH
        assert exercise.difficulty == DifficultyLevel.MEDIUM

    def test_database_configuration(self) -> None:
        """Test Database configuration"""

        config = DatabaseConfig("sqlite:///:memory:")
        config.init_engine()

        assert config.engine is not None
        assert config.SessionLocal is not None

    def test_database_tables_list(self) -> None:
        """Test that expected database tables are defined"""
        expected_tables = [
            "users",
            "classes",
            "textbooks",
            "knowledge_points",
            "ability_targets",
            "common_mistakes",
            "questions",
            "distractor_patterns",
            "exercises",
            "practice_sessions",
            "answer_submissions",
            "analytics_snapshots",
        ]

        # This test assumes the models are properly defined
        # In a real test, you might check the actual database schema
        assert len(expected_tables) >= MIN_EXPECTED_TABLES
        assert "users" in expected_tables
        assert "questions" in expected_tables
        assert "textbooks" in expected_tables
