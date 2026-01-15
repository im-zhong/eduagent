# flush() vs commit() in SQLAlchemy

## Overview

This document explains the difference between `session.flush()` and `session.commit()` and when to use each.

## The Mental Model

```
PostgreSQL Database
       ↑
    TCP Connection
       ↑
   Connection Pool
       ↑
   AsyncEngine (singleton)
       ↑
   AsyncSession (short-lived)
       ↑
   Identity Map (Python objects in memory)
```

## session.flush()

**Sends pending changes to database BUT doesn't commit the transaction.**

```python
quiz = Quiz(doc_id=1, source="generated", question_json="{...}")
session.add(quiz)
await session.flush()  # Executes INSERT, gets ID from DB

print(quiz.id)  # NOW available! (None before flush)

# Transaction is still open - can roll back
await session.rollback()  # Quiz would be removed from DB
```

### What Happens Internally

1. Executes SQL (INSERT/UPDATE/DELETE)
2. Gets generated IDs, default values, etc.
3. **Transaction remains open**
4. Can still be rolled back

### When to Use `flush()`

| Scenario | Reason |
|-----------|---------|
| Need auto-generated ID | `quiz.id` is `None` until flush |
| Creating related records | Child records need parent's ID |
| Database-assigned values | Triggers, defaults, computed columns |
| Batch operations | Execute multiple SQL in one transaction |
| Validation errors | Catch DB errors before final commit |

### Example: Creating Parent-Child Records

```python
# quiz/repository.py
async def create_quiz_with_references(session, doc_id, source, question_json, reference_texts):
    quiz = Quiz(doc_id=doc_id, source=source, question_json=question_json)
    session.add(quiz)
    await session.flush()  # Flush to get quiz.id

    # Now quiz.id is available for creating QuizReference
    for ref_text, chunk_idx in reference_texts:
        ref = QuizReference(quiz_id=quiz.id, reference_text=ref_text, chunk_index=chunk_idx)
        session.add(ref)

    return quiz
```

Without `flush()`, `quiz.id` would be `None`, and we couldn't create the `QuizReference` records.

## session.commit()

**Persists changes permanently - transaction is closed.**

```python
quiz = Quiz(doc_id=1, source="generated", question_json="{...}")
session.add(quiz)
await session.commit()  # Executes INSERT AND commits transaction

# Transaction closed - cannot roll back
print(quiz.id)  # Available after commit
```

### What Happens Internally

1. Executes SQL (if not already flushed)
2. **Commits transaction** (permanent)
3. Closes transaction
4. Connection returned to pool

### When to Use `commit()`

| Scenario | Reason |
|-----------|---------|
| Finalize changes | Make changes permanent |
| End of transaction | Release database connection |
| Explicit transaction boundary | Control when data is persisted |

## Transactional Session Pattern

In this project, `get_async_session()` handles commit automatically:

```python
# storage/engine.py
@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async session with automatic commit/rollback."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()  # Auto-commit on success
        except Exception:
            await session.rollback()  # Auto-rollback on exception
            raise
```

Repository functions use `flush()` to get IDs, and the dependency handles `commit()`:

```python
# repository.py - just add/flush
async def create_quiz(session, doc_id, source, question_json):
    quiz = Quiz(doc_id=doc_id, source=source, question_json=question_json)
    session.add(quiz)
    await session.flush()  # Get ID, but don't commit
    return quiz

# endpoint.py - no commit needed
@router.post("/generate")
async def generate(request, session = Depends(get_async_session)):
    quiz = await create_quiz(session, ...)
    # Auto-committed by get_async_session
```

## Summary Table

| Operation | SQL Sent | Transaction | ID Available | Rollback Possible |
|-----------|-----------|--------------|---------------|------------------|
| `session.add()` | No | Open | No | Yes |
| `await session.flush()` | Yes | Open | Yes | Yes |
| `await session.commit()` | Yes | Closed | Yes | No |

## Common Patterns

### Pattern 1: Simple Create

```python
quiz = Quiz(...)
session.add(quiz)
await session.commit()
```

### Pattern 2: Create with Relations (needs flush)

```python
quiz = Quiz(...)
session.add(quiz)
await session.flush()  # Get ID for relations

ref = QuizReference(quiz_id=quiz.id, ...)
session.add(ref)

await session.commit()
```

### Pattern 3: Batch Operations (one transaction)

```python
for item in items:
    obj = Item(**item)
    session.add(obj)
    await session.flush()  # Validate each, get IDs

await session.commit()  # All or nothing
```

### Pattern 4: Transactional Session (this project)

```python
# Repository: flush only
async def create_quiz(session, ...):
    quiz = Quiz(...)
    session.add(quiz)
    await session.flush()
    return quiz

# Dependency: handles commit
@asynccontextmanager
async def get_async_session():
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()  # Once per request
        except Exception:
            await session.rollback()
            raise
```
