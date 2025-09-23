"""
Unit tests for API structure and schema definitions
"""

import pytest
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestAPIStructure:
    """Test class for API structure validation"""

    def test_api_modules_import(self):
        """Test that API modules can be imported successfully"""
        from eduagent.api.api import api
        from eduagent.api.schemas import (
            QuestionGenerationRequest,
            UserCreateRequest,
        )
        assert api is not None
        assert QuestionGenerationRequest is not None
        assert UserCreateRequest is not None

    def test_question_generation_request_schema(self):
        """Test QuestionGenerationRequest schema validation"""
        from eduagent.api.schemas import QuestionGenerationRequest

        request = QuestionGenerationRequest(
            knowledge_point_ids=["math_001", "math_002"],
            question_type="multiple_choice",
            difficulty="medium",
            num_questions=5
        )

        assert request.knowledge_point_ids == ["math_001", "math_002"]
        assert request.question_type == "multiple_choice"
        assert request.difficulty == "medium"
        assert request.num_questions == 5

    def test_user_create_request_schema(self):
        """Test UserCreateRequest schema validation"""
        from eduagent.api.schemas import UserCreateRequest

        request = UserCreateRequest(
            username="testuser",
            email="test@example.com",
            password="password123",
            role="student"
        )

        assert request.username == "testuser"
        assert request.email == "test@example.com"
        assert request.password == "password123"
        assert request.role == "student"

    def test_api_routes_configuration(self):
        """Test that API has routes configured"""
        from eduagent.api.api import api

        routes = list(api.routes)
        assert len(routes) > 0

    def test_important_routes_exist(self):
        """Test that important API routes exist"""
        from eduagent.api.api import api

        routes = list(api.routes)
        available_paths = [route.path for route in routes]

        important_paths = [
            "/api/v1/questions/generate",
            "/api/v1/assessment/evaluate",
            "/api/v1/textbook/upload",
            "/api/v1/users/register"
        ]

        for path in important_paths:
            assert any(p.startswith(path) for p in available_paths), f"Route {path} not found"

    def test_api_endpoints_methods(self):
        """Test that API endpoints have proper HTTP methods"""
        from eduagent.api.api import api

        routes = list(api.routes)
        api_routes = [route for route in routes if route.path.startswith("/api")]

        assert len(api_routes) > 0

        for route in api_routes:
            if hasattr(route, "methods"):
                assert len(route.methods) > 0, f"Route {route.path} has no methods"