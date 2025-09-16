# 2025/9/16
# zhangzhong

from eduagent.defs import defs
from eduagent.settings import new_settings


def test_settings() -> None:
    settings = new_settings(defs.pathes.example_settings_file)
    print(settings)
