# defs
# 不应该被配置的常量


import os
from pathlib import Path
from typing import ClassVar


class Pathes:
    _UPLOADS_ENV: ClassVar[str] = "EDUAGENT_UPLOADS_DIR"

    @property
    def log_dir(self) -> Path:
        path = Path("logs")
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def etc_dir(self) -> Path:
        path = Path("etc")
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def default_settings_file(self) -> Path:
        return Path("eduagent.toml")

    @property
    def example_settings_file(self) -> Path:
        return Path("example.eduagent.toml")

    def _ensure_dir(self, path: Path) -> Path:
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def uploads_dir(self) -> Path:
        candidates: list[Path] = []
        override = os.getenv(self._UPLOADS_ENV)
        if override:
            candidates.append(Path(override))
        candidates.extend(
            [
                Path("data") / "uploads",
                Path("var") / "uploads",
                Path.home() / ".cache" / "eduagent" / "uploads",
            ]
        )
        for candidate in candidates:
            try:
                return self._ensure_dir(candidate)
            except PermissionError:
                continue
        msg = "Unable to create a writable uploads directory"
        raise RuntimeError(msg)


class APIDefs:
    """API endpoint definitions for EduAgent system"""

    # Base API path
    BASE_PATH = "/api/v1"

    # Quiz Pipeline Endpoints
    QUIZ_BASE = f"{BASE_PATH}/quiz"
    QUIZ_UPLOAD = f"{QUIZ_BASE}/upload"
    QUIZ_JOB_DETAIL = f"{QUIZ_BASE}/jobs/{{job_id}}"
    QUIZ_WORKFLOW = f"{QUIZ_BASE}/workflow"
    QUIZ_GENERATE = f"{QUIZ_BASE}/generate"
    QUIZ_EVALUATE = f"{QUIZ_BASE}/evaluate"
    QUIZ_SCORE = f"{QUIZ_BASE}/score"

    # Analytics Endpoints
    PERFORMANCE_ANALYTICS = f"{BASE_PATH}/analytics/performance"
    MISTAKE_ANALYSIS = f"{BASE_PATH}/analytics/mistakes"
    CLASS_ANALYTICS = f"{BASE_PATH}/analytics/class/{{class_id}}"

    # System Endpoints
    HEALTH_CHECK = f"{BASE_PATH}/health"


class UIDefs:
    """UI-related constants and definitions"""

    # Page titles and icons
    TEACHER_DASHBOARD_TITLE = "EduAgent - Teacher Dashboard"
    STUDENT_DASHBOARD_TITLE = "EduAgent - Student Dashboard"
    PAGE_ICON = "📚"

    # Navigation options
    TEACHER_NAV_OPTIONS: ClassVar[list[str]] = [
        "Overview",
        "Ingestion Lab",
        "Workflow Runner",
        "Async Pipeline",
        "Scoring Studio",
        "Analytics Monitor",
    ]

    STUDENT_NAV_OPTIONS: ClassVar[list[str]] = []

    # Subject options
    SUBJECTS: ClassVar[list[str]] = [
        "Math",
        "Science",
        "History",
        "Language",
        "Physics",
        "Chemistry",
        "Biology",
        "Computer Science",
    ]

    # Grade levels
    GRADE_LEVELS: ClassVar[list[str]] = [
        "Elementary",
        "Middle School",
        "High School",
        "College",
    ]

    # Question types
    QUESTION_TYPES: ClassVar[list[str]] = [
        "Multiple Choice",
        "True/False",
        "Short Answer",
        "Essay",
        "Calculation",
        "Fill in Blank",
    ]

    # Difficulty levels
    DIFFICULTY_LEVELS: ClassVar[list[str]] = ["Easy", "Medium", "Hard"]

    # Cognitive levels
    COGNITIVE_LEVELS: ClassVar[list[str]] = [
        "Memory",
        "Understanding",
        "Application",
        "Analysis",
        "Evaluation",
        "Creation",
    ]

    # Time periods for analytics
    TIME_PERIODS: ClassVar[list[str]] = ["7 days", "30 days", "90 days", "All time"]


class Defs:
    @property
    def pathes(self) -> Pathes:
        return Pathes()

    @property
    def api(self) -> APIDefs:
        return APIDefs()

    @property
    def ui(self) -> UIDefs:
        return UIDefs()


def new_defs() -> Defs:
    return Defs()


defs: Defs = new_defs()
