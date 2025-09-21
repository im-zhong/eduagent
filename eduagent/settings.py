# settings
# conf file is way better than env variables, so we use toml


import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from eduagent.defs import defs


class ProjectConfig(BaseModel):
    api_version: str = "v1"


class LLMConfig(BaseModel):
    api_key: str = "NOKEY"
    api_base: str = "https://api.deepseek.com"


class DatabaseConfig(BaseModel):
    user: str = "ysu_keg"
    password: str = "123456789"
    host: str = "db.eduagent"
    port: int = 5432
    name: str = "eduagent"

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


# 总 Settings
# ------------------------
class Settings(BaseModel):
    project: ProjectConfig = Field(default_factory=ProjectConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)

    database: DatabaseConfig = Field(default_factory=DatabaseConfig)


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


def create_default_settings() -> Settings:
    if not defs.pathes.default_settings_file.exists():
        return Settings()
    return new_settings(defs.pathes.default_settings_file)


# 应该在有配置文件的时候读取配置文件，没有的话就用默认值
settings: Settings = create_default_settings()
