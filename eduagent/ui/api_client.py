"""
API Client for EduAgent UI
Provides interface to communicate with the backend API
"""

from __future__ import annotations

import json
from collections.abc import Generator
from typing import Any

import requests

from eduagent.defs import defs

HTTP_SUCCESS_CODES = (200, 201, 202)


class EduAgentAPIClient:
    """Client for interacting with EduAgent API"""

    def __init__(
        self,
        base_url: str = "http://api.eduagent:8000",
        service_token: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.service_token = service_token
        self.timeout = 30

    def configure(self, base_url: str, service_token: str | None) -> None:
        self.base_url = base_url.rstrip("/")
        self.service_token = service_token

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self.service_token:
            headers["Authorization"] = f"Bearer {self.service_token}"
        return headers

    def _make_request(
        self,
        endpoint: str,
        method: str = "GET",
        json_data: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.request(
                method=method.upper(),
                url=url,
                json=json_data,
                data=data,
                files=files,
                headers=self._headers(),
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            return {"error": f"Request failed: {exc!s}"}

        if response.status_code in HTTP_SUCCESS_CODES:
            try:
                return response.json()
            except ValueError:
                return {"status": response.status_code}
        return {"error": f"HTTP {response.status_code}: {response.text}"}

    def health_check(self) -> dict[str, Any]:
        return self._make_request(defs.api.HEALTH_CHECK)

    def upload_ingestion_document(
        self, filename: str, file_bytes: bytes, subject: str, grade_level: str
    ) -> dict[str, Any]:
        files = {"file": (filename, file_bytes)}
        data = {"subject": subject, "grade_level": grade_level}
        return self._make_request(defs.api.QUIZ_UPLOAD, "POST", data=data, files=files)

    def get_quiz_job(self, job_id: str) -> dict[str, Any]:
        endpoint = defs.api.QUIZ_JOB_DETAIL.format(job_id=job_id)
        return self._make_request(endpoint)

    def request_quiz_generation(
        self,
        ingestion_job_id: str,
        subject: str | None,
        query: str | None,
        rules: dict[str, Any],
    ) -> dict[str, Any]:
        payload = {
            "ingestion_job_id": ingestion_job_id,
            "subject": subject,
            "query": query,
            "quiz_rules": rules,
        }
        return self._make_request(defs.api.QUIZ_GENERATE, "POST", json_data=payload)

    def request_quiz_evaluation(
        self, quiz_job_id: str, answers: list[dict[str, Any]]
    ) -> dict[str, Any]:
        payload = {"quiz_job_id": quiz_job_id, "answers": answers}
        return self._make_request(defs.api.QUIZ_EVALUATE, "POST", json_data=payload)

    def request_quiz_scoring(
        self,
        quiz_job_id: str,
        questions: list[dict[str, Any]],
        rules: dict[str, Any] | None,
    ) -> dict[str, Any]:
        payload = {
            "quiz_job_id": quiz_job_id,
            "questions": questions,
            "rules": rules,
        }
        return self._make_request(defs.api.QUIZ_SCORE, "POST", json_data=payload)

    def run_quiz_workflow(self, ingestion_job_id: str, prompt: str) -> dict[str, Any]:
        payload = {"ingestion_job_id": ingestion_job_id, "prompt": prompt}
        return self._make_request(defs.api.QUIZ_WORKFLOW, "POST", json_data=payload)

    def stream_quiz_workflow(
        self, ingestion_job_id: str, prompt: str
    ) -> Generator[dict[str, Any]]:
        url = f"{self.base_url}{defs.api.QUIZ_WORKFLOW_STREAM}"
        payload = {"ingestion_job_id": ingestion_job_id, "prompt": prompt}
        try:
            with requests.post(
                url,
                json=payload,
                headers=self._headers(),
                timeout=None,
                stream=True,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    if not line.startswith("data: "):
                        continue
                    data = line.replace("data: ", "", 1)
                    if not data.strip():
                        continue
                    try:
                        yield json.loads(data)
                    except json.JSONDecodeError:
                        yield {
                            "phase": "error",
                            "payload": {"message": "Unable to parse server event data"},
                        }
                        return
        except requests.RequestException as exc:
            yield {"phase": "error", "payload": {"message": str(exc)}}

    def get_performance_analytics(
        self, student_id: str, time_period: str
    ) -> dict[str, Any]:
        data = {"student_id": student_id, "time_period": time_period}
        return self._make_request(
            defs.api.PERFORMANCE_ANALYTICS, "POST", json_data=data
        )

    def get_class_analytics(self, class_id: str, time_period: str) -> dict[str, Any]:
        endpoint = defs.api.CLASS_ANALYTICS.format(class_id=class_id)
        data = {"time_period": time_period}
        return self._make_request(endpoint, "POST", json_data=data)

    def analyze_mistakes(self, student_id: str, subject: str) -> dict[str, Any]:
        data = {"student_id": student_id, "subject": subject}
        return self._make_request(defs.api.MISTAKE_ANALYSIS, "POST", json_data=data)
