# settings
# conf file is way better than env variables, so we use toml


import tomllib
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


# ------------------------
# 枚举
# ------------------------
class LLMType(StrEnum):
    QWEN = "qwen"
    DEEPSEEK = "deepseek"


# ------------------------
# 配置块
# ------------------------
class ProjectConfig(BaseModel):
    name: str = "Education Agent"
    version: str = "1.0.0"
    api_v1_str: str = "v1"


class DeepSeekConfig(BaseModel):
    api_key: str = "NOKEY"
    api_base: str = "https://api.deepseek.com"


class DatabaseConfig(BaseModel):
    user: str = "root"
    password: str = "123456"
    host: str = "localhost"
    port: int = 5432
    name: str = "education"

    @property
    def sqlalchemy_url(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

    @property
    def db_dict(self) -> dict[str, Any]:
        return {
            "user": self.user,
            "password": self.password,
            "host": self.host,
            "port": self.port,
            "database": self.name,
        }


class LLMConfig(BaseModel):
    base_llm: LLMType = LLMType.QWEN


# ------------------------
# 总 Settings
# ------------------------
class Settings(BaseModel):
    project: ProjectConfig = Field(default_factory=ProjectConfig)
    deepseek: DeepSeekConfig = Field(default_factory=DeepSeekConfig)

    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)

    # ------------------------
    # LLM 配置方法
    # ------------------------
    def get_base_llm(self) -> LLMType:
        return self.llm.base_llm


# ------------------------
# 工厂函数
# ------------------------
def new_settings(path: str | Path) -> Settings:
    path = Path(path)
    if not path.exists():
        msg = f"Config file not found: {path}"
        raise FileNotFoundError(msg)

    with path.open("rb") as f:
        data = tomllib.load(f)

    return Settings(**data)


# TODO(zhangzhong): 做CICD的时候怎么生成一个配置文件？
# settings: Settings = new_settings(path=defs.pathes.default_settings_file)
