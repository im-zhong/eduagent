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
        return self.etc_dir / Path("eduagent.toml")

    @property
    def example_settings_file(self) -> Path:
        return Path("example.eduagent.toml")


class Defs:
    @property
    def pathes(self) -> Pathes:
        return Pathes()


def new_defs() -> Defs:
    return Defs()


defs: Defs = new_defs()
