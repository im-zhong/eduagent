# 文件: /home/Yunx/eduagent/conftest.py

from pathlib import Path  # <-- 1. 导入 Path 用于处理路径

import pytest  # <-- 2. 导入 pytest 用于类型注解
from dotenv import load_dotenv


def pytest_configure(_config: pytest.Config) -> None:
    """
    在 pytest 启动时(收集测试之前)加载 .env 文件。
    """
    # 4. 使用 pathlib.Path 替代 os.path (修复所有 PTH... 错误)
    env_path: Path = Path(__file__).parent / ".env"

    if env_path.exists():  # <-- 4. (续) 使用 .exists()
        # load_dotenv 接受 Path 对象
        load_dotenv(dotenv_path=env_path, override=True)
        print(f"\npytest: 成功从 {env_path} 加载了 .env 文件。")
    else:
        print(f"\npytest 警告: 未在 {env_path} 找到 .env 文件。")
