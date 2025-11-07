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


# --- 工厂函数 ---
def new_settings(path: str | Path) -> Settings:
    path = Path(path)
    if not path.exists():
        msg = f"Config file not found: {path}"
        raise FileNotFoundError(msg)

    with path.open("rb") as f:
        data = tomllib.load(f)

    settings = Settings(**data)
    # 为了支持CICD，如果环境中存在变量API_KEY, 就会直接覆盖配置文件
    api_key_env = os.environ.get("API_KEY")

    if api_key_env:
        settings.llm.api_key = api_key_env
    return settings


def create_default_settings() -> Settings:
    if not defs.pathes.default_settings_file.exists():
        return Settings()
    return new_settings(defs.pathes.default_settings_file)


# 全局配置实例
settings: Settings = create_default_settings()
