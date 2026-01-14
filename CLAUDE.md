# CLAUDE MEMORY

## General Technical Guidelines

- I am using uv in this project, so when you want to run a command like pytest xxx, you should use uv pytest xxx
- This project is in running in the dev container, make sure you check the conf files in the @.devcontainer/devcontainer.json folder and @dev.Dockerfile and @dev.docker-compose.yaml
- you should not fix the ruff or pyright check by anno it!
- you should not use *args and **kwargs at all!
- use morden type hint like: int | str, not Union[int, str]
- you should not fix the pyright errors by using anno # type: ignore to fix it
- I use SQLAlchemy 2.0 style, so you should not use the old style.
- I use pydantic v2, so you should not use the old style.
-
- when you modify a file, do not forget to use ruff and pyright to check that file.
- prefer pydantic model to define the data structure, do not use dict or list directly.

## Development Workflow

- Follow **write-test-commit** iterative loop for feature development
- Use **conventional commit** messages (feat:, fix:, refactor:, etc.)
- Do not add "Co-Authored-By: Claude Sonnet" to commit messages
- Run static checks (ruff, pyright) after completing a feature, not during development
- Test organization: mirror app module structure (e.g., `tests/unit/documents/` for `eduagent/documents/`)

## Module Design Principles

- **Self-contained modules**: Each service owns its own database models and CRUD implementations
- **Common infrastructure**: Only shared components (like async engine) go in common modules
- Example: Database table definitions and CRUD logic should be in the specific module (e.g., `eduagent/documents/`), not a shared models directory
- Generic table creation function (`create_tables_for_module()`) should be in the common storage module

## Testing Strategy

- **Early development stage**: Focus on integration tests and API endpoint tests
- Skip unit tests for Pydantic model validation in early development (less flexible, high maintenance overhead)
- Add unit tests for business logic only after the feature stabilizes
