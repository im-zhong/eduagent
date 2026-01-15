# LangGraph vs Simple Service for Quiz Generation

## Overview

This document explains the choice of using a minimal LangGraph approach (linear, no branching) for Milestone 5 instead of a simple service class.

## Design Comparison

### Simple Service Class

```python
class QuizGenerationService:
    async def generate_single_choice_questions(self, session, request):
        hits = await self.retrieval_service.retrieve_relevant_chunks(...)
        questions = await self.llm.ainvoke(...)
        quiz_ids = await self.save_quizzes(...)
        return QuizGenerationResponse(...)
```

**Pros:**
- Simple, direct, easy to understand
- Fast to implement for MVP
- Minimal code overhead

**Cons:**
- Not extensible - hard to add intermediate steps
- No built-in tracing or state management
- Difficult to visualize workflow
- Hard to migrate to multi-agent systems later

### Minimal LangGraph (Linear, No Branching)

```python
# Linear workflow: retrieve_chunks → generate_questions → save_quizzes
class QuizGenerationState(TypedDict):
    doc_id: int
    topic: str
    count: int
    context_chunks: list[SearchHit]
    generated_questions: list[SingleChoiceQuestion]
    quiz_ids: list[int]

async def retrieve_chunks(state: QuizGenerationState) -> QuizGenerationState:
    hits = await retrieval_service.retrieve_relevant_chunks(...)
    return {"context_chunks": hits}

async def generate_questions(state: QuizGenerationState) -> QuizGenerationState:
    questions = await llm.ainvoke(...)
    return {"generated_questions": questions}

async def save_quizzes(state: QuizGenerationState) -> QuizGenerationState:
    quiz_ids = await save_quizzes(...)
    return {"quiz_ids": quiz_ids}

workflow = StateGraph(QuizGenerationState)
workflow.add_node("retrieve_chunks", retrieve_chunks)
workflow.add_node("generate_questions", generate_questions)
workflow.add_node("save_quizzes", save_quizzes)
workflow.add_edge("retrieve_chunks", "generate_questions")
workflow.add_edge("generate_questions", "save_quizzes")
workflow.set_entry_point("retrieve_chunks")
workflow.set_finish_point("save_quizzes")
```

**Pros:**
- Extensible - easy to add/remove nodes
- Built-in state management and tracing
- Easy to visualize workflow (native graph visualization)
- Easy to migrate to complex multi-agent systems
- LangSmith integration for debugging/monitoring

**Cons:**
- Slightly more complex initially
- LangGraph learning curve

## Decision: Minimal LangGraph

For Milestone 5, we use a **minimal LangGraph** approach with:
- Linear flow (no branching)
- No conditional logic
- No validation/retry nodes
- Simple state passing

### Why Minimal LangGraph?

1. **Future-Proof**: Built on LangGraph foundation makes it trivial to extend
2. **Minimal Complexity**: Linear graph has almost no overhead vs simple service
3. **Benefits Now**:
   - State management is explicit
   - Easy to add intermediate nodes later
   - Built-in tracing/debugging
   - Workflow visualization available

4. **Migration Path**: When adding complexity (validation, retry, quality check), just insert nodes:
   ```python
   # Before: Linear
   retrieve → generate → save

   # After: Insert validation
   retrieve → generate → validate → (retry?) → save
   ```

## Future Extension Path

As the system grows, LangGraph becomes more valuable:

| Milestone | Complexity | LangGraph Value |
|-----------|-----------|-----------------|
| M5 (Current) | Linear, no branches | ✅ Foundation |
| M6 | Validation nodes | ✅ Built-in |
| M8 | Conditional retry/branching | ✅ Native support |
| M10 | Multi-agent orchestration | ✅ Core strength |

## Example: Adding Validation Later

```python
# Insert new node between existing ones
async def validate_questions(state: QuizGenerationState) -> QuizGenerationState:
    # Validate each question
    for q in state["generated_questions"]:
        if not is_valid(q):
            return {"should_retry": True}
    return {"should_retry": False}

# Add conditional edge
workflow.add_node("validate_questions", validate_questions)
workflow.add_edge("generate_questions", "validate_questions")

# Add branching: retry if validation fails
workflow.add_conditional_edges(
    "validate_questions",
    {
        "should_retry": "generate_questions",  # Retry generation
        (END): "save_quizzes",  # Proceed if valid
    },
)
```

## Conclusion

**Choice**: Minimal LangGraph (linear, no branching)

**Rationale**:
- Almost no complexity overhead vs simple service
- Provides LangGraph foundation for future milestones
- Built-in tracing and visualization
- Easy migration path for complex workflows

**Alternative**: Simple service class would be faster for MVP but requires complete rewrite when adding complexity.
