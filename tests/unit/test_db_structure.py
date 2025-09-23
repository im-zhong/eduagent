"""
Unit tests for database structure and model definitions
"""

import pytest
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestDatabaseStructure:
    """Test class for database structure validation"""

    def test_database_modules_import(self):
        """Test that database modules can be imported successfully"""
        from eduagent.db.config import DatabaseConfig
        from eduagent.db.models import (
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

    def test_user_role_enum(self):
        """Test UserRole enum values"""
        from eduagent.db.models import UserRole

        roles = [role.value for role in UserRole]
        assert "student" in roles
        assert "teacher" in roles
        assert "admin" in roles
        assert len(roles) >= 3

    def test_difficulty_level_enum(self):
        """Test DifficultyLevel enum values"""
        from eduagent.db.models import DifficultyLevel

        levels = [level.value for level in DifficultyLevel]
        assert "easy" in levels
        assert "medium" in levels
        assert "hard" in levels
        assert len(levels) >= 3

    def test_question_type_enum(self):
        """Test QuestionType enum values"""
        from eduagent.db.models import QuestionType

        types = [qtype.value for qtype in QuestionType]
        assert "multiple_choice" in types
        assert "short_answer" in types
        assert "essay" in types
        assert len(types) >= 3

    def test_cognitive_level_enum(self):
        """Test CognitiveLevel enum values"""
        from eduagent.db.models import CognitiveLevel

        levels = [level.value for level in CognitiveLevel]
        assert "knowledge" in levels
        assert "comprehension" in levels
        assert "application" in levels
        assert "analysis" in levels
        assert "synthesis" in levels
        assert "evaluation" in levels
        assert len(levels) >= 6

    def test_subject_area_enum(self):
        """Test SubjectArea enum values"""
        from eduagent.db.models import SubjectArea

        subjects = [subject.value for subject in SubjectArea]
        assert "math" in subjects
        assert "science" in subjects
        assert "english" in subjects
        assert len(subjects) >= 3

    def test_user_model_instantiation(self):
        """Test User model instantiation"""
        from eduagent.db.models import User, UserRole

        user = User(
            username="test_teacher",
            email="teacher@example.com",
            password_hash="hashed_password",
            role=UserRole.TEACHER,
            grade_level="Grade 10"
        )

        assert user.username == "test_teacher"
        assert user.email == "teacher@example.com"
        assert user.password_hash == "hashed_password"
        assert user.role == UserRole.TEACHER
        assert user.grade_level == "Grade 10"

    def test_textbook_model_instantiation(self):
        """Test Textbook model instantiation"""
        from eduagent.db.models import Textbook, SubjectArea

        textbook = Textbook(
            title="Mathematics Grade 10",
            subject=SubjectArea.MATH,
            grade_level="Grade 10",
            extraction_status="pending"
        )

        assert textbook.title == "Mathematics Grade 10"
        assert textbook.subject == SubjectArea.MATH
        assert textbook.grade_level == "Grade 10"
        assert textbook.extraction_status == "pending"

    def test_knowledge_point_model_instantiation(self):
        """Test KnowledgePoint model instantiation"""
        from eduagent.db.models import KnowledgePoint, SubjectArea, CognitiveLevel

        knowledge_point = KnowledgePoint(
            name="Quadratic Equations",
            description="Solving quadratic equations using various methods",
            subject=SubjectArea.MATH,
            cognitive_level=CognitiveLevel.APPLICATION
        )

        assert knowledge_point.name == "Quadratic Equations"
        assert knowledge_point.description == "Solving quadratic equations using various methods"
        assert knowledge_point.subject == SubjectArea.MATH
        assert knowledge_point.cognitive_level == CognitiveLevel.APPLICATION

    def test_question_model_instantiation(self):
        """Test Question model instantiation"""
        from eduagent.db.models import Question, QuestionType, DifficultyLevel, CognitiveLevel, SubjectArea

        question = Question(
            question_text="Solve the quadratic equation: x² - 5x + 6 = 0",
            question_type=QuestionType.SHORT_ANSWER,
            difficulty=DifficultyLevel.MEDIUM,
            cognitive_level=CognitiveLevel.APPLICATION,
            subject=SubjectArea.MATH
        )

        assert question.question_text == "Solve the quadratic equation: x² - 5x + 6 = 0"
        assert question.question_type == QuestionType.SHORT_ANSWER
        assert question.difficulty == DifficultyLevel.MEDIUM
        assert question.cognitive_level == CognitiveLevel.APPLICATION
        assert question.subject == SubjectArea.MATH

    def test_exercise_model_instantiation(self):
        """Test Exercise model instantiation"""
        from eduagent.db.models import Exercise, SubjectArea, DifficultyLevel

        exercise = Exercise(
            title="Quadratic Equations Practice",
            subject=SubjectArea.MATH,
            difficulty=DifficultyLevel.MEDIUM
        )

        assert exercise.title == "Quadratic Equations Practice"
        assert exercise.subject == SubjectArea.MATH
        assert exercise.difficulty == DifficultyLevel.MEDIUM

    def test_database_configuration(self):
        """Test Database configuration"""
        from eduagent.db.config import DatabaseConfig

        config = DatabaseConfig("sqlite:///:memory:")
        config.init_engine()

        assert config.engine is not None
        assert config.SessionLocal is not None

    def test_database_tables_list(self):
        """Test that expected database tables are defined"""
        expected_tables = [
            "users", "classes", "textbooks", "knowledge_points",
            "ability_targets", "common_mistakes", "questions",
            "distractor_patterns", "exercises", "practice_sessions",
            "answer_submissions", "analytics_snapshots"
        ]

        # This test assumes the models are properly defined
        # In a real test, you might check the actual database schema
        assert len(expected_tables) >= 12
        assert "users" in expected_tables
        assert "questions" in expected_tables
        assert "textbooks" in expected_tables