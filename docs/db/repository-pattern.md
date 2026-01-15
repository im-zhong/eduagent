# Database Repository Pattern: Functions vs Classes

## Overview

This document explains the choice of module-level functions over class-based repositories for database operations in this project.

## FastAPI `Depends` Execution Model

```python
async def get_async_session() -> AsyncSession:
    async with async_session_maker() as session:
        yield session  # FastAPI injects this to the endpoint

async def my_endpoint(
    session: AsyncSession = Depends(get_async_session)  # Each request gets a NEW session
):
    ...
```

### What Happens Per Request

1. **Request arrives**
2. **`Depends(get_async_session)` is called** - creates a NEW generator
3. **Generator executes up to `yield`** - new `AsyncSession` created
4. **Endpoint receives this session** - unique to this request
5. **Endpoint completes**
6. **Generator resumes after `yield`** - cleanup runs
7. **Session is closed** - connection returned to pool

### Key Points

| Aspect | Behavior |
|--------|----------|
| `Depends` function | Called **once per request** |
| Returned value | Fresh instance each time |
| Lifecycle | Request-scoped |
| Thread-safety | Each request gets its own session |

---

## Comparison: Functions vs Classes

### Module-Level Functions (CHOSEN PATTERN)

```python
# repository.py
async def create_quiz(session: AsyncSession, doc_id: int, source: str, question_json: str) -> Quiz:
    quiz = Quiz(doc_id=doc_id, source=source, question_json=question_json)
    session.add(quiz)
    await session.flush()
    return quiz

# endpoint.py
@router.post("/generate")
async def generate(
    request: QuizGenerationRequest,
    session: AsyncSession = Depends(get_async_session),
):
    return await create_quiz(session, request.doc_id, "generated", "...",)
```

**Advantages:**
- Clean, direct API
- No redundant object creation per request
- Matches Pythonic functional style
- Consistent with SQLAlchemy 2.0 patterns
- Clearer intent: `create_quiz(session, ...)` vs `QuizRepository(session).create(...)`

### Class-Based Repository (REJECTED PATTERN)

```python
# repository.py
class QuizRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, doc_id: int, source: str, question_json: str) -> Quiz:
        quiz = Quiz(doc_id=doc_id, source=source, question_json=question_json)
        self.session.add(quiz)
        await self.session.flush()
        return quiz

# endpoint.py
@router.post("/generate")
async def generate(
    request: QuizGenerationRequest,
    session: AsyncSession = Depends(get_async_session),
):
    repo = QuizRepository(session)  # New instance per request = pointless
    return await repo.create(request.doc_id, "generated", "...",)
```

**Problems:**
- Repository is recreated every request anyway
- Just a wrapper around the session with no added value
- Verbose: `QuizRepository(session).create(...)` vs `create_quiz(session, ...)`
- Illusion of statefulness where there is none

---

## When Would a Class Make Sense?

A class-based repository is justified ONLY when you need **stateful behavior**:

1. **Caching** - Repository maintains in-memory cache
2. **Connection-specific configuration** - Different settings per instance
3. **Complex business logic** - Multiple related operations sharing internal state
4. **Method organization** - Large number of operations benefit from grouping

Example where class makes sense:

```python
class CachedDocumentRepository:
    def __init__(self, session: AsyncSession, cache_ttl: int = 300):
        self.session = session
        self.cache: dict[int, Document] = {}
        self.cache_ttl = cache_ttl

    async def get_with_cache(self, doc_id: int) -> Document | None:
        if doc_id in self.cache:
            return self.cache[doc_id]
        doc = await get_document(self.session, doc_id)
        self.cache[doc_id] = doc
        return doc
```

---

## Recommended Pattern for This Project

For simple CRUD operations without stateful behavior:

```python
# repository.py - module-level functions
async def create_quiz(session: AsyncSession, doc_id: int, source: str, question_json: str) -> Quiz:
    ...

async def create_quiz_with_references(
    session: AsyncSession,
    doc_id: int,
    source: str,
    question_json: str,
    reference_texts: list[tuple[str, int | None]],
) -> Quiz:
    ...

async def get_quizzes_by_document(session: AsyncSession, doc_id: int) -> Sequence[Quiz]:
    ...

async def delete_quiz(session: AsyncSession, quiz_id: int) -> bool:
    ...
```

This pattern is:
- Used in [eduagent/documents/repository.py](eduagent/documents/repository.py)
- Consistent with SQLAlchemy 2.0 async patterns
- Clean and maintainable
- Request-scoped by design via `Depends`
