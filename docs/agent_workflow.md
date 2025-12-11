# Agent Workflow Diagram

```mermaid
flowchart TD
    A[User Uploads DOCX] --> B[Textbook Ingestion Task]
    B --> C[DocxIngestionService parses & chunks]
    C --> D[ChunkEmbeddingService embeds + stores in Milvus]
    D --> E[DocumentRepository stores metadata & artifacts]

    E --> F{Quiz Workflow Trigger}
    F --> G[QuizWorkflowRunner]
    G --> H[ReAct Agent (plan → act → evaluate → finalize)]
    H --> I[QuizArtifact persisted]

    I --> J[Quiz Generation Celery Task]
    J --> K[Quiz Evaluation Task]
    J --> L[Quiz Scoring Task]
    K --> M[Evaluation Result stored]
    L --> N[Quality Score stored]

    style B fill:#fce5cd
    style D fill:#d9ead3
    style H fill:#d0e0e3
    style L fill:#f4cccc
```
