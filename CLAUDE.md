# CLAUDE MEMORY

- I am using uv in this project, so when you want to run a command like pytest xxx, you should use uv pytest xxx
- This project is in running in the dev container, make sure you check the conf files in the @.devcontainer/devcontainer.json folder and @dev.Dockerfile and @dev.docker-compose.yaml
- you should not fix the ruff or pyright check by anno it!
- you should not use *args and **kwargs at all!
- use morden type hint like: int | str, not Union[int, str]
- you should not fix the pyright errors by using anno # type: ignore to fix it
- I use SQLAlchemy 2.0 style, so you should not use the old style.
- I use pydantic v2, so you should not use the old style.
- when you modify a file, do not forget to use ruff and pyright to check that file.
- prefer pydantic model to define the data structure, do not use dict or list directly.
