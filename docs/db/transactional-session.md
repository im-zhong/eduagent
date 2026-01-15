# Transactional Session Pattern

## Overview

This document describes the transactional session pattern used for handling database commits and rollbacks automatically via FastAPI's dependency injection.

## Problem

Without automatic transaction handling, every endpoint must manually call `session.commit()` and handle rollback on exceptions, leading to boilerplate and potential bugs:

```python
# BAD: Manual commit/rollback in every endpoint
async def create_endpoint(session: AsyncSession = Depends(get_async_session)):
    try:
        await create_quiz(session, ...)
        await create_quiz_references(session, ...)
        await session.commit()  # Boilerplate
    except Exception:
        await session.rollback()  # Easy to forget
        raise
```

## Solution: Transactional `get_async_session`

The `get_async_session` dependency is modified to auto-commit on success and auto-rollback on exception:

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def get_async_session() -> AsyncSession:
    """Dependency that provides a session with automatic commit/rollback."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()  # Auto-commit on success
        except Exception:
            await session.rollback()  # Auto-rollback on exception
            raise
```

## How It Works

| Scenario | Behavior |
|-----------|-----------|
| Endpoint completes successfully | `await session.commit()` is called automatically |
| Endpoint raises exception | `await session.rollback()` is called automatically, exception is re-raised |
| Multiple operations in endpoint | All committed together in one transaction |

## Usage

### Repository Functions (Simple CRUD)

Repository functions only add/flush data - no commit/rollback needed:

```python
# repository.py
async def create_quiz(session: AsyncSession, doc_id: int, source: str, question_json: str) -> Quiz:
    quiz = Quiz(doc_id=doc_id, source=source, question_json=question_json)
    session.add(quiz)
    await session.flush()  # Get ID if needed, but no commit
    return quiz
```

### Endpoints (Clean Transaction Handling)

No commit/rollback boilerplate - the dependency handles it:

```python
# endpoint.py
@router.post("/generate")
async def generate(
    request: QuizGenerationRequest,
    session: AsyncSession = Depends(get_async_session),  # Auto commit/rollback
):
    quiz = await create_quiz(session, ...)
    await create_quiz_references(session, quiz.id, references)
    return QuizGenerationResponse(...)  # Commits automatically
```

### Service Layer (Complex Operations)

For multi-step operations, all steps share the same transaction:

```python
# service.py
async def generate_quiz_with_references(session, doc_id, topic):
    # All operations share one transaction
    quiz = await create_quiz(session, doc_id, "generated", question_json)
    await create_quiz_references(session, quiz.id, reference_texts)
    return quiz

# Either both succeed (commit) or both fail (rollback)
```

## Edge Cases

### Manual Transaction Control

If you need multiple independent transactions in one endpoint, use manual commit within the session:

```python
async def complex_operation(session: AsyncSession = Depends(get_auto_commit_session)):
    # First transaction
    await do_thing1(session)
    await session.commit()  # Manual commit

    # Second transaction
    await do_thing2(session)
    # Will auto-commit on exit
```

For such cases, you can provide an alternative dependency that doesn't auto-commit:

```python
@asynccontextmanager
async def get_async_session_no_auto_commit() -> AsyncSession:
    """Session without auto-commit for manual transaction control."""
    async with async_session_maker() as session:
        yield session
```

### Read-Only Endpoints

For read-only operations, auto-commit is harmless (empty transaction), but you can optimize:

```python
@router.get("/documents")
async def list_documents(
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(select(Document))
    return result.scalars().all()
    # Auto-commit does nothing for read-only
```

## Benefits

1. **No Boilerplate** - Endpoints don't need try/except commit/rollback blocks
2. **Consistent Behavior** - All endpoints handle transactions the same way
3. **Fewer Bugs** - Impossible to forget rollback on exception
4. **Centralized Control** - Easy to add logging, metrics, retry logic later
5. **ACID Guarantees** - All operations in one request are atomic

## Implementation

See [eduagent/storage/engine.py](eduagent/storage/engine.py) for the implementation.
