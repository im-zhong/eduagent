Here’s a clear, practical comparison of asyncio vs trio vs anyio, from mental model → semantics → ecosystem → when to choose what.

⸻

1. One-sentence intuition

Library Core idea
asyncio Python’s standard, lowest-level async runtime
trio A strict, structured-concurrency async runtime designed for correctness
anyio A compatibility layer that lets you write code that runs on asyncio or trio

⸻

1. asyncio

What it is
 • Python’s official async framework (stdlib since 3.4)
 • Event-loop–centric
 • Foundation for FastAPI, aiohttp, SQLAlchemy async, asyncpg, etc.

Key characteristics
 • 🔹 Manual task lifecycle (create_task, cancellation is cooperative but messy)
 • 🔹 Error propagation is implicit and easy to miss
 • 🔹 Backwards compatibility → legacy design constraints
 • 🔹 Single event loop per thread

Example

async def main():
    task = asyncio.create_task(worker())
    await asyncio.sleep(1)
    task.cancel()

Strengths

✅ Standard library
✅ Massive ecosystem
✅ Excellent tooling & performance
✅ Required for many frameworks

Weaknesses

❌ Unstructured concurrency
❌ Cancellation is fragile
❌ Easy to leak tasks
❌ Complex mental model for large systems

⸻

1. trio

What it is
 • A clean-slate async runtime
 • Enforces structured concurrency (inspired by modern OS theory)

Key idea: “Tasks must live inside a scope”

No orphan tasks. Ever.

Example

import trio

async def main():
    async with trio.open_nursery() as nursery:
        nursery.start_soon(worker)
        nursery.start_soon(worker)

If one task fails → all tasks are cancelled.

Strengths

✅ Predictable cancellation
✅ Strong error propagation
✅ No background task leaks
✅ Clear, elegant mental model
✅ Excellent for research & correctness-critical systems

Weaknesses

❌ Not stdlib
❌ Smaller ecosystem
❌ Most frameworks don’t run on it directly

⸻

1. anyio

What it is
 • A unified async API
 • Runs on asyncio or trio
 • Used by FastAPI, Starlette, SQLAlchemy async

“Write once, choose runtime later.”

Example

import anyio

async def main():
    async with anyio.create_task_group() as tg:
        tg.start_soon(worker)

Works on:
 • asyncio backend
 • trio backend

Strengths

✅ Structured concurrency like trio
✅ Compatible with asyncio ecosystem
✅ Runtime-agnostic libraries
✅ Production-proven

Weaknesses

❌ Thin abstraction → some runtime-specific features hidden
❌ Debugging can feel indirect
❌ Still depends on asyncio under the hood (in most apps)

⸻

1. Feature comparison

Feature asyncio trio anyio
Stdlib ✅ ❌ ❌
Structured concurrency ❌ ✅ ✅
Task groups ❌ ✅ ✅
Cancellation safety ⚠️ ✅ ✅
Ecosystem size ⭐⭐⭐⭐⭐ ⭐⭐ ⭐⭐⭐⭐
FastAPI support Native ❌ Native
Learning curve Medium Low (but different) Low
Research friendliness ⚠️ ⭐⭐⭐⭐⭐ ⭐⭐⭐⭐

⸻

1. Cancellation semantics (this matters)

asyncio

task.cancel()  # maybe cancelled, maybe ignored

 • Cancellation = exception
 • Can be swallowed
 • Parent doesn’t know if children died

trio / anyio

async with create_task_group():
    ...

# guaranteed cleanup

 • Cancellation is structured
 • Fail fast
 • No zombie tasks

⸻

1. Ecosystem reality (2026)

Area Dominant choice
Web APIs asyncio + anyio
FastAPI / Starlette anyio
Async DB drivers asyncio
Research / correctness trio
Libraries anyio
Production infra asyncio

⸻

1. When should you use what?

Use asyncio if:
 • You need maximum compatibility
 • You’re writing low-level async infra
 • You integrate heavily with existing async libs

Use trio if:
 • You care about correctness over compatibility
 • You’re doing research, prototyping, or new async designs
 • You want the cleanest mental model

Use anyio if:
 • You’re building libraries
 • You’re using FastAPI / Starlette
 • You want structured concurrency without ecosystem pain
 • You want future-proof async code

⸻

1. Practical recommendation (honest take)

In real systems (FastAPI, SQLAlchemy, etc.):

 • Think in trio semantics
 • Code in anyio
 • Run on asyncio

That’s exactly what modern Python async frameworks do.

⸻

1. Mental model summary

asyncio  → "event loop & tasks"
trio     → "lifetimes & scopes"
anyio    → "structured async, portable runtime"

⸻

If you want, I can also:
 • 🔍 Compare performance
 • 🧠 Show common asyncio bugs trio avoids
 • 🏗️ Map this to FastAPI lifespan / request scopes
 • 🧪 Explain testing async code across all three

Just tell me where you want to go next.
