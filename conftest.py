# 文件: /home/runner/eduagent/conftest.py

from pathlib import Path

import pytest  # 导入 pytest 以便使用类型
from dotenv import load_dotenv


# 1. 把参数名从 _config 改回 config
def pytest_configure(config: pytest.Config) -> None:  # noqa: ARG001
    """
    在 pytest 启动时(收集测试之前)加载 .env 文件。
    """
    env_path: Path = Path(__file__).parent / ".env"

    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=True)
        # (为了CI日志简洁，你可以去掉下面的 print)
        print(f"\npytest: 成功从 {env_path} 加载了 .env 文件。")
    else:
        print(f"\npytest 警告: 未在 {env_path} 找到 .env 文件。")
