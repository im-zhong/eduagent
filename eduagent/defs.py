# defs
# 不应该被配置的常量


from pathlib import Path


class Pathes:
    @property
    def log_dir(self) -> Path:
        return self._ensure_dir(Path("logs"))

    @property
    def etc_dir(self) -> Path:
        return self._ensure_dir(Path("etc"))

    @property
    def default_settings_file(self) -> Path:
        return Path("eduagent.toml")

    @property
    def example_settings_file(self) -> Path:
        return Path("example.eduagent.toml")

    def _ensure_dir(self, path: Path) -> Path:
        path.mkdir(parents=True, exist_ok=True)
        return path


class APIDefs:
    """API endpoint definitions for EduAgent system"""

    # Base API path
    BASE_PATH = "/api/v1"

    # TODO(zhangzhong): move module-specific API defs into their own modules and
    # aggregate here to reduce coupling (e.g., documents, retrieval).

    # Quiz Pipeline Endpoints
    QUIZ_BASE = f"{BASE_PATH}/quiz"
    QUIZ_UPLOAD = f"{QUIZ_BASE}/upload"
    QUIZ_JOB_DETAIL = f"{QUIZ_BASE}/jobs/{{job_id}}"
    QUIZ_INGESTION_LIST = f"{QUIZ_BASE}/ingestions"
    QUIZ_WORKFLOW = f"{QUIZ_BASE}/workflow"
    QUIZ_WORKFLOW_STREAM = f"{QUIZ_BASE}/workflow/stream"
    QUIZ_RAG_CHAT_STREAM = f"{QUIZ_BASE}/rag/chat/stream"
    QUIZ_GENERATE = f"{QUIZ_BASE}/generate"
    QUIZ_EVALUATE = f"{QUIZ_BASE}/evaluate"
    QUIZ_SCORE = f"{QUIZ_BASE}/score"

    # Analytics Endpoints
    PERFORMANCE_ANALYTICS = f"{BASE_PATH}/analytics/performance"
    MISTAKE_ANALYSIS = f"{BASE_PATH}/analytics/mistakes"
    CLASS_ANALYTICS = f"{BASE_PATH}/analytics/class/{{class_id}}"

    # System Endpoints
    HEALTH_CHECK = f"{BASE_PATH}/health"
    VERSION = f"{BASE_PATH}/version"

    # Document Endpoints
    DOCUMENTS_PARSE = f"{BASE_PATH}/documents/parse"

    # Retrieval Endpoints
    INDEX_CHUNKS = f"{BASE_PATH}/index/chunks/{{doc_id}}"
    SEARCH_CHUNKS = f"{BASE_PATH}/search/chunks"
    SEARCH_CHUNKS_DENSE = f"{BASE_PATH}/search/chunks/dense"
    SEARCH_CHUNKS_HYBRID = f"{BASE_PATH}/search/chunks/hybrid"


class Defs:
    @property
    def pathes(self) -> Pathes:
        return Pathes()

    @property
    def api(self) -> APIDefs:
        return APIDefs()

    # @property
    # def ui(self) -> UIDefs:
    #     return UIDefs()


def new_defs() -> Defs:
    return Defs()


defs: Defs = new_defs()
