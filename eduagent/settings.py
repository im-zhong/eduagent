import os
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
    api_base: str = "https://api.deepseek.com"
    model_name: str = "glm-4.5"
    embedding_model_name: str = "embedding_model"


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
    def celery_result_backend(self) -> str:
        """Create Celery compatible SQLAlchemy backend DSN"""
        return f"db+postgresql+psycopg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

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


class RabbitMQConfig(BaseModel):
    host: str = "eduagent-rabbitmq"
    port: int = 5672
    username: str = "eduagent"
    password: str = "eduagent"
    vhost: str = "/"

    @property
    def amqp_url(self) -> str:
        return f"amqp://{self.username}:{self.password}@{self.host}:{self.port}{self.vhost}"


class MilvusConfig(BaseModel):
    """Milvus 向量数据库配置"""

    host: str = "eduagent-milvus"
    port: int = 19530
    username: str | None = None
    password: str | None = None
    database: str = "default"
    collection: str = "eduagent_quiz_chunks"
    timeout: int = 30


class MinioConfig(BaseModel):
    """MinIO 对象存储配置"""

    endpoint: str = "eduagent-minio:9000"
    access_key: str = "minioadmin"
    secret_key: str = "minioadmin"
    secure: bool = False
    bucket: str = "eduagent"


class CeleryConfig(BaseModel):
    """Celery 分布式任务队列配置"""

    broker_url: str | None = None
    result_backend: str | None = None
    default_queue: str = "eduagent.quizzes"
    task_time_limit: int = 600
    result_expires: int = 3600


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
    rabbitmq: RabbitMQConfig = Field(default_factory=RabbitMQConfig)
    milvus: MilvusConfig = Field(default_factory=MilvusConfig)
    minio: MinioConfig = Field(default_factory=MinioConfig)
    celery: CeleryConfig = Field(default_factory=CeleryConfig)

    def model_post_init(self, __context: object, /) -> None:
        if not self.celery.broker_url:
            self.celery.broker_url = self.rabbitmq.amqp_url
        if not self.celery.result_backend:
            self.celery.result_backend = self.database.celery_result_backend


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
    settings = create_default_settings_ignore_env()

    # 为了支持CICD，如果环境中存在变量API_KEY, 就会直接覆盖配置文件
    api_key_env = os.environ.get("API_KEY")

    if api_key_env:
        settings.llm.api_key = api_key_env
    return settings


# 全局配置实例
settings: Settings = create_default_settings()
