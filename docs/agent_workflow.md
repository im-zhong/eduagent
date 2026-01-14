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

    I --> J[Quiz Generation Task]
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
    participant DocsSvc as Document Service
    participant Milvus as Milvus Vector Store

    Teacher->>Streamlit: Upload DOCX/PDF + metadata
    Streamlit->>FastAPI: POST /api/v1/quiz/upload (multipart form)
    FastAPI->>MinIO: store_file(file, metadata)
    MinIO-->>FastAPI: object_id / location
    FastAPI->>Repo: create_ingestion_job(subject, grade, payload)
    Repo-->>FastAPI: job record (status=pending)
    FastAPI-->>Teacher: 202 Accepted + ingestion job_id
    FastAPI->>DocsSvc: download & parse DOCX/PDF
    DocsSvc->>Milvus: embed chunks + store vectors
    DocsSvc-->>FastAPI: ingestion artifact ids
    FastAPI->>Repo: update_status(job_id, completed, result=document_job_id)
    Repo-->>FastAPI: updated job record
    FastAPI-->>Teacher: (via later status check) job marked completed with document_job_id

```

## Quiz Generation Workflow

```mermaid
flowchart TD
    Q[User Query]
    RQ[Rewrite Query - 规范化和消歧]
    SE[结构化提取: 题目要求 / 难度 / 知识点 / 数量 / 题型]
    ASK[补充提问: 无法提取则让用户细化需求]
    RET[检索: 用改写后的 Query + 结构化约束搜索知识库]
    GEN[生成题目: 结合检索结果与约束]
    EVAL[大模型评估: 是否满足原始需求]
    DONE[输出最终题目]
    REGEN[重新生成: 调整提示或约束后再生成]

    Q --> RQ --> SE
    SE -->|信息不足| ASK --> SE
    SE -->|信息充分| RET --> GEN --> EVAL
    EVAL -->|满足| DONE
    EVAL -->|不满足| REGEN --> GEN

```
