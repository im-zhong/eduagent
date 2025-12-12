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

## Ingestion Job

```mermaid
sequenceDiagram
    autonumber
    actor Teacher
    participant Streamlit as Streamlit UI
    participant FastAPI as FastAPI /quiz/upload
    participant MinIO as MinIO Storage
    participant Repo as QuizJobRepository
    participant Celery as Celery Worker
    participant DocsSvc as Document Service
    participant Milvus as Milvus Vector Store

    Teacher->>Streamlit: Upload DOCX/PDF + metadata
    Streamlit->>FastAPI: POST /api/v1/quiz/upload (multipart form)
    FastAPI->>MinIO: store_file(file, metadata)
    MinIO-->>FastAPI: object_id / location
    FastAPI->>Repo: create_ingestion_job(subject, grade, payload)
    Repo-->>FastAPI: job record (status=pending)
    FastAPI-->>Teacher: 202 Accepted + ingestion job_id
    FastAPI->>Celery: enqueue process_textbook_upload(job_id, object_id, metadata)

    Celery->>DocsSvc: download & parse DOCX/PDF
    DocsSvc->>Milvus: embed chunks + store vectors
    DocsSvc-->>Celery: ingestion artifact ids
    Celery->>Repo: update_status(job_id, completed, result=document_job_id)
    Repo-->>Celery: updated job record
    Celery-->>Teacher: (via later status check) job marked completed with document_job_id

```
