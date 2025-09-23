# defs
# 不应该被配置的常量


from pathlib import Path


class Pathes:
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


class APIDefs:
    """API endpoint definitions for EduAgent system"""

    # Base API path
    BASE_PATH = "/api/v1"

    # Knowledge Extraction Endpoints
    TEXTBOOK_UPLOAD = f"{BASE_PATH}/textbook/upload"
    EXTRACTION_STATUS = f"{BASE_PATH}/knowledge/extraction/{{extraction_id}}"
    KNOWLEDGE_GRAPH = f"{BASE_PATH}/knowledge/graph/{{textbook_id}}"

    # Question Generation Endpoints
    GENERATE_QUESTIONS = f"{BASE_PATH}/questions/generate"
    CONTROL_DIFFICULTY = f"{BASE_PATH}/questions/difficulty/control"
    GENERATE_DISTRACTORS = f"{BASE_PATH}/questions/distractors/generate"

    # Assessment & Feedback Endpoints
    EVALUATE_ANSWERS = f"{BASE_PATH}/assessment/evaluate"
    PROVIDE_FEEDBACK = f"{BASE_PATH}/feedback/provide"

    # User Management Endpoints
    USER_REGISTER = f"{BASE_PATH}/users/register"
    USER_LOGIN = f"{BASE_PATH}/users/login"
    USER_PROFILE = f"{BASE_PATH}/users/{{user_id}}"

    # Exercise & Practice Endpoints
    CREATE_EXERCISE = f"{BASE_PATH}/exercises"
    GET_EXERCISE = f"{BASE_PATH}/exercises/{{exercise_id}}"
    START_PRACTICE = f"{BASE_PATH}/practice/session"

    # Analytics Endpoints
    PERFORMANCE_ANALYTICS = f"{BASE_PATH}/analytics/performance"
    MISTAKE_ANALYSIS = f"{BASE_PATH}/analytics/mistakes"
    CLASS_ANALYTICS = f"{BASE_PATH}/analytics/class/{{class_id}}"

    # System Endpoints
    HEALTH_CHECK = f"{BASE_PATH}/health"
    BATCH_GENERATE_QUESTIONS = f"{BASE_PATH}/batch/questions/generate"


class UIDefs:
    """UI-related constants and definitions"""

    # Page titles and icons
    TEACHER_DASHBOARD_TITLE = "EduAgent - Teacher Dashboard"
    STUDENT_DASHBOARD_TITLE = "EduAgent - Student Dashboard"
    PAGE_ICON = "📚"

    # Navigation options
    TEACHER_NAV_OPTIONS = [
        "🏠 Dashboard",
        "📖 Textbook Management",
        "❓ Question Generation",
        "📊 Analytics & Reports",
        "👥 Class Management",
        "⚙️ Settings"
    ]

    STUDENT_NAV_OPTIONS = [
        "🏠 Dashboard",
        "📚 Practice Exercises",
        "📈 Progress Tracking",
        "❓ Ask Questions",
        "⚙️ Settings"
    ]

    # Subject options
    SUBJECTS = [
        "Math", "Science", "History", "Language",
        "Physics", "Chemistry", "Biology", "Computer Science"
    ]

    # Grade levels
    GRADE_LEVELS = ["Elementary", "Middle School", "High School", "College"]

    # Question types
    QUESTION_TYPES = [
        "Multiple Choice", "True/False", "Short Answer",
        "Essay", "Calculation", "Fill in Blank"
    ]

    # Difficulty levels
    DIFFICULTY_LEVELS = ["Easy", "Medium", "Hard"]

    # Cognitive levels
    COGNITIVE_LEVELS = [
        "Memory", "Understanding", "Application",
        "Analysis", "Evaluation", "Creation"
    ]

    # Time periods for analytics
    TIME_PERIODS = ["7 days", "30 days", "90 days", "All time"]


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
