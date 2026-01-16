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
- **Comment density for AI-generated code**: AI-generated code should include comments for every several lines (2-5 lines) to explain the purpose and flow, making it easier to understand quickly without reading line-by-line

## Testing Strategy

- **Early development stage**: Focus on integration tests and API endpoint tests
- Skip unit tests for Pydantic model validation in early development (less flexible, high maintenance overhead)
- Add unit tests for business logic only after the feature stabilizes

### Integration Test Principles

Integration tests verify that multiple components work together correctly. They differ from unit tests in that they test real interactions between services rather than isolated functions.

**Core Principles:**

1. **Self-Contained Setup**
   - Each test must create its own test data (documents, chunks, etc.)
   - Never assume external data exists in the database or Milvus
   - Use fixtures to set up and tear down test data
   - Example: Create a test document, parse it, index in Milvus, then test

2. **End-to-End Testing**
   - Test complete workflows, not individual components
   - Verify data flows through all layers: API → Service → Graph → Database
   - Example: `POST /api/v1/quiz/generate` → retrieve chunks → generate questions → save to DB

3. **No Mocking**
   - Use real database sessions via `get_async_session()`
   - Use real Milvus for retrieval tests
   - Use real LLM for generation tests
   - This catches real integration issues that mocks would miss

4. **Cleanup**
   - Tests must clean up their own data after execution
   - Use try-finally or pytest fixtures with cleanup
   - Delete test documents, chunks, and quizzes from database and Milvus
   - Log cleanup errors but don't fail the test

**Example Structure:**

```python
@pytest.fixture
async def setup_test_document(db_session) -> int:
    """Set up test document in database and Milvus."""
    # Create document record
    doc = SourceDocument(filename="test.txt", ...)
    db_session.add(doc)
    await db_session.flush()
    doc_id = doc.id

    # Index chunks in Milvus
    await doc_service.parse_and_store_document(...)

    yield doc_id  # Provide to test

    # Cleanup
    await delete_quizzes_by_doc(db_session, doc_id)
    await retrieval.delete_document_chunks(doc_id)
    await db_session.delete(doc)

@pytest.mark.integration
@pytest.mark.asyncio
async def test_quiz_generation_end_to_end(
    setup_test_document: int,
    db_session
):
    """Test complete workflow with real services."""
    request = QuizGenerationRequest(doc_id=doc_id, topic="Python", count=2)
    response = await run_quiz_generation_workflow(request, db_session)

    assert len(response.questions) > 0
    assert len(response.quiz_ids) > 0
```

**What NOT to Do:**

- ❌ Assume `doc_id=1` exists in the database
- ❌ Mock the Milvus client or LLM
- ❌ Test individual nodes in isolation (that's unit test territory)
- ❌ Skip cleanup and leave test data in database

**When to Use Integration Tests:**

- Verifying LangGraph workflows with real database checkpointer
- Testing RAG pipelines with real Milvus embeddings
- End-to-end API testing with real HTTP calls
- Multi-service workflows (quiz = retrieval + LLM + database)
