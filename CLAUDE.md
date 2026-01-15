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
- Dev container tests should call real microservices directly; avoid fake clients or mocked network calls
- Prefer pytest asyncio (`@pytest.mark.asyncio`) for async tests unless told otherwise

## Localization and Language

- **System Language**: This project is designed for Chinese users
- **Prompts and UI text**: All LLM prompts, user-facing messages, and documentation should be in Chinese
- **Code Comments**: Technical comments in code should be in English for maintainability, but prompt content in the code should be in Chinese
- **Example**: LLM prompt templates must use Chinese, but variable names and logic explanation remain English

## Module Design Principles

- **Self-contained modules**: Each service owns its own database models and CRUD implementations
- **Common infrastructure**: Only shared components (like async engine) go in common modules
- **Avoid fake commons**: If a "common" module is only used by one feature/module, move it into that module to reduce coupling
- **Purposeful comments**: New code should include brief comments at key points to explain intent/purpose, not restate obvious operations
- Example: Database table definitions and CRUD logic should be in the specific module (e.g., `eduagent/documents/`), not a shared models directory
- Generic table creation function (`create_tables_for_module()`) should be in the common storage module

## Testing Strategy

- **Early development stage**: Focus on integration tests and API endpoint tests
- Skip unit tests for Pydantic model validation in early development (less flexible, high maintenance overhead)
- Add unit tests for business logic only after the feature stabilizes
