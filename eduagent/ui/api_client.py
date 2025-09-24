"""
API Client for EduAgent UI
Provides interface to communicate with the backend API
"""

from typing import Any

import requests

from eduagent.defs import defs

HTTP_STATUS_OK = 200


class EduAgentAPIClient:
    """Client for interacting with EduAgent API"""

    def __init__(self, base_url: str = "http://api.eduagent:8000") -> None:
        self.base_url = base_url

    def _make_request(
        self, endpoint: str, method: str = "GET", data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Make HTTP request to API"""
        url = f"{self.base_url}{endpoint}"
        try:
            if method.upper() == "GET":
                response = requests.get(url)
            elif method.upper() == "POST":
                response = requests.post(url, json=data)
            elif method.upper() == "PUT":
                response = requests.put(url, json=data)
            else:
                return {"error": f"Unsupported HTTP method: {method}"}

            if response.status_code == HTTP_STATUS_OK:
                return response.json()
            return {"error": f"HTTP {response.status_code}: {response.text}"}  # noqa: TRY300

        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {e!s}"}

    def health_check(self) -> dict[str, Any]:
        """Check API health"""
        return self._make_request(defs.api.HEALTH_CHECK)

    def upload_textbook(
        self, filename: str, subject: str, grade_level: str
    ) -> dict[str, Any]:
        """Upload textbook for knowledge extraction"""
        data = {"filename": filename, "subject": subject, "grade_level": grade_level}
        return self._make_request(defs.api.TEXTBOOK_UPLOAD, "POST", data)

    def get_extraction_status(self, extraction_id: str) -> dict[str, Any]:
        """Get status of knowledge extraction"""
        endpoint = defs.api.EXTRACTION_STATUS.format(extraction_id=extraction_id)
        return self._make_request(endpoint)

    def generate_questions(
        self,
        knowledge_point_ids: list[str],
        question_type: str,
        difficulty: str,
        num_questions: int,
    ) -> dict[str, Any]:
        """Generate educational questions"""
        data = {
            "knowledge_point_ids": knowledge_point_ids,
            "question_type": question_type,
            "difficulty": difficulty,
            "num_questions": num_questions,
        }
        return self._make_request(defs.api.GENERATE_QUESTIONS, "POST", data)

    def control_question_difficulty(
        self, question_text: str, target_difficulty: float
    ) -> dict[str, Any]:
        """Control question difficulty"""
        data = {"question_text": question_text, "target_difficulty": target_difficulty}
        return self._make_request(defs.api.CONTROL_DIFFICULTY, "POST", data)

    def generate_distractors(
        self, question_text: str, knowledge_point_id: str
    ) -> dict[str, Any]:
        """Generate distractors for multiple choice questions"""
        data = {
            "question_text": question_text,
            "knowledge_point_id": knowledge_point_id,
        }
        return self._make_request(defs.api.GENERATE_DISTRACTORS, "POST", data)

    def start_practice_session(
        self, knowledge_point_ids: list[str], num_questions: int, difficulty: str
    ) -> dict[str, Any]:
        """Start a practice session"""
        data = {
            "knowledge_point_ids": knowledge_point_ids,
            "num_questions": num_questions,
            "difficulty": difficulty,
        }
        return self._make_request(defs.api.START_PRACTICE, "POST", data)

    def get_performance_analytics(
        self, student_id: str, time_period: str
    ) -> dict[str, Any]:
        """Get student performance analytics"""
        data = {"student_id": student_id, "time_period": time_period}
        return self._make_request(defs.api.PERFORMANCE_ANALYTICS, "POST", data)

    def get_class_analytics(self, class_id: str, time_period: str) -> dict[str, Any]:
        """Get class analytics"""
        endpoint = defs.api.CLASS_ANALYTICS.format(class_id=class_id)
        data = {"time_period": time_period}
        return self._make_request(endpoint, "POST", data)

    def analyze_mistakes(self, student_id: str, subject: str) -> dict[str, Any]:
        """Analyze student mistake patterns"""
        data = {"student_id": student_id, "subject": subject}
        return self._make_request(defs.api.MISTAKE_ANALYSIS, "POST", data)
