import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from eduagent.defs import defs


class RedisConfig(BaseModel):
    """Redis 数据库配置"""

    host: str = "eduagent-redis"
    port: int = 6379
    db: int = 0


class ApiConfig(BaseModel):
    """API 相关配置,例如 JWT 密钥"""

    secret_key: str = "a_very_secret_key_that_should_be_changed"


class ProjectConfig(BaseModel):
    """项目通用配置"""

    api_version: str = "v1"


class LLMConfig(BaseModel):
    """大语言模型(LLM)相关配置"""

    api_key: str = "NOKEY"
    api_base: str = "https://open.bigmodel.cn/api/paas/v4/"
    model_name: str = "glm-4.6"
    embedding_model_name: str = "embedding-3"
    temperature: float = 0.0


class DatabaseConfig(BaseModel):
    """PostgreSQL 数据库配置"""

    user: str = "ysu_keg"
    password: str = "123456789"
    host: str = "db.eduagent"
    port: int = 5432
    name: str = "eduagent"

    @property
    def sqlalchemy_url(self) -> str:
        """生成 SQLAlchemy 使用的数据库连接 URL"""
        return f"postgresql+psycopg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

    @property
    def db_dict(self) -> dict[str, Any]:
        """以字典形式返回数据库连接参数"""
        return {
            "user": self.user,
            "password": self.password,
            "host": self.host,
            "port": self.port,
            "database": self.name,
        }


class PGVectorSettings(BaseModel):
    host: str = "db.eduagent"
    port: int = 5432
    user: str = "ysu_keg"
    password: str = "123456789"
    dbname: str = "eduagent"
    collection_name: str = "demo_for_rag"

    @property
    def connection_string(self) -> str:
        return f"postgresql+psycopg://{self.user}:{self.password}@{self.host}:{self.port}/{self.dbname}"


class MilvusConfig(BaseModel):
    """Milvus 向量数据库配置"""

    host: str = "eduagent-milvus"
    port: int = 19530
    username: str | None = None
    password: str | None = None
    database: str = "default"
    collection: str = "eduagent_quiz_chunks"
    timeout: int = 30
    dim: int = 1536


class MinioConfig(BaseModel):
    """MinIO 对象存储配置"""

    endpoint: str = "eduagent-minio:9000"
    access_key: str = "minioadmin"
    secret_key: str = "minioadmin"
    secure: bool = False
    bucket: str = "eduagent"


class ServiceAuthConfig(BaseModel):
    """Service-to-service authentication settings."""

    secret_key: str = "change_me_service_secret"
    issuer: str = "nextjs-service"
    audience: str = "eduagent-api"
    algorithm: str = "HS256"
    leeway_seconds: int = Field(default=10, ge=0)


class QuizWorkflowSettings(BaseModel):
    """ReAct 流水线相关配置。"""

    default_language: str = "zh"
    retrieval_limit: int = 5
    max_iterations: int = 3


# --- 总的 Settings 类 ---
class Settings(BaseModel):
    """
    应用总配置,聚合所有子配置项。
    """

    project: ProjectConfig = Field(default_factory=ProjectConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    pg_vector: PGVectorSettings = Field(default_factory=PGVectorSettings)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    api: ApiConfig = Field(default_factory=ApiConfig)
    milvus: MilvusConfig = Field(default_factory=MilvusConfig)
    minio: MinioConfig = Field(default_factory=MinioConfig)
    service_auth: ServiceAuthConfig = Field(default_factory=ServiceAuthConfig)
    quiz_workflow: QuizWorkflowSettings = Field(default_factory=QuizWorkflowSettings)


# --- 工厂函数 ---
def new_settings(path: str | Path) -> Settings:
    path = Path(path)
    if not path.exists():
        msg = f"Config file not found: {path}"
        raise FileNotFoundError(msg)

    with path.open("rb") as f:
        data = tomllib.load(f)

    return Settings(**data)


def create_default_settings_ignore_env() -> Settings:
    if not defs.pathes.default_settings_file.exists():
        return Settings()
    return new_settings(defs.pathes.default_settings_file)


def create_default_settings() -> Settings:
    return create_default_settings_ignore_env()


# 全局配置实例
settings: Settings = create_default_settings()
