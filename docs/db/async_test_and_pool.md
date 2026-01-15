Below is a focused, bug-oriented notes summary distilled only from the problems you actually hit, with emphasis on async tests, AsyncEngine, AsyncSession, and connection pooling.
This is meant to be a post-mortem + future checklist.

⸻

Async SQLAlchemy + FastAPI — Bug-Oriented Notes

1. Two Different Classes of Bugs (Don’t Mix Them)

Bug Class A — Event loop conflicts
 • Caused by:
 • global async engine
 • multiple event loops (AnyIO, pytest-anyio)
 • Symptom:

RuntimeError / event loop mismatch

 • Fix:
 • Use one async model consistently (asyncio or anyio)
 • Or create engine per test
 • Or use NullPool

⸻

Bug Class B — Concurrent connection usage (what you’re hitting now)
 • Caused by:
 • pooled connections
 • parallel tests or concurrent requests
 • asyncpg strict connection rules
 • Symptom:

asyncpg.InterfaceError:
cannot perform operation: another operation is in progress

 • Fix:
 • Disable pooling in tests
 • Or isolate DB per test / per worker

⸻

1. Async Test Framework Rules (Critical)

pytest-asyncio
 • One shared event loop for all tests
 • Requires:

@pytest.mark.asyncio

 • Async fixtures must use:

@pytest_asyncio.fixture

pytest-anyio
 • New event loop per test
 • Exposes global async state bugs
 • Async fixtures use:

@pytest.fixture

❌ Never mix asyncio + anyio in the same test file

⸻

1. Async Fixture Gotcha (You Hit This)

Wrong

@pytest.fixture
async def async_client():
    ...

Correct (asyncio tests)

@pytest_asyncio.fixture
async def async_client():
    ...

If wrong:
 • pytest injects an async_generator
 • leads to:

AttributeError: 'async_generator' object has no attribute 'post'

⸻

1. AsyncEngine Scope Rule (Non-Negotiable)

Production

engine = create_async_engine(...)

 • One engine per worker
 • Pooling enabled

Tests

engine = create_async_engine(
    TEST_DB_URL,
    poolclass=NullPool,
)

Why:
 • asyncpg connections are:
 • event-loop bound
 • single-operation only

⸻

1. AsyncSession ≠ Connection (Core Misconception)

What you assumed

One session owns one connection

Reality
 • Session borrows a connection only while executing SQL
 • Connection is returned to pool immediately after each DB operation
 • Another session can reuse it before the first session commits

This causes overlapping DB usage.

⸻

1. Why Pool Size Does NOT Prevent Collisions

Even with:

pool_size = 5

Collisions still happen because:
 • connections are reused over time
 • not reserved per request
 • commit/flush can interleave across sessions

⸻

1. asyncpg Strictness (Why You See This Error)

asyncpg enforces:
 • One operation at a time per connection
 • No implicit serialization

Hence:

cannot perform operation: another operation is in progress

This is a feature, not a bug.

⸻

1. Why Tests Are the Worst Case

Tests:
 • Are extremely fast
 • Run concurrently
 • Reuse the same engine
 • Hit commit/flush at nearly the same time
 • Amplify timing windows

What “works in prod” often fails in tests.

⸻

1. The Golden Test Configuration (Safe Baseline)

from sqlalchemy.pool import NullPool

engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=NullPool,
)

Guarantees:
 • No connection reuse
 • No concurrent access
 • No loop issues
 • Deterministic behavior

⸻

1. pytest-xdist (Parallel Tests)

If running:

pytest -n auto

You must have one of:
 • NullPool
 • separate DB per worker
 • or disable parallelism

⸻

1. What NOT to Do (Checklist)

❌ Share AsyncSession
❌ Store session globally
❌ Cache session with @lru_cache
❌ Assume pool size = request isolation
❌ Mix anyio and asyncio
❌ Use pooled engine in async integration tests

⸻

1. Mental Model to Remember (One Line)

AsyncSession borrows connections temporarily; pooling + concurrency can cause overlapping DB usage unless pooling is disabled in tests.

⸻

1. Final Takeaway
 • Switching to asyncio only fixed event-loop bugs
 • You then correctly uncovered connection-level concurrency bugs
 • The correct fix is test-safe engine isolation, not more asyncio changes

⸻

If you want next, I can:
 • turn this into a team-wide testing guideline
 • audit your get_async_session dependency
 • design a parallel-safe test DB strategy

Just tell me.
