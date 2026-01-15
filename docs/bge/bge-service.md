# BGE Service

A production-ready FastAPI service for BGE-M3 embeddings and BGE-Reranker-V2 inference, supporting dense, sparse, and hybrid retrieval workflows.

## Features

- **BGE-M3 Embeddings**: Multi-lingual embedding model with dense, sparse, and ColBERT-style multi-vector retrieval
- **BGE-Reranker-V2**: Cross-encoder reranker for precise query-document relevance scoring
- **Hybrid Retrieval Support**: Generate both dense and sparse embeddings in a single API call
- **Production-Safe Design**: Single-process, GPU-bound inference with proper resource management
- **FastAPI**: Modern async web framework with automatic OpenAPI documentation

## Architecture

### Models

| Model | Size | Use Case |
|-------|------|----------|
| **BAAI/bge-m3** | ~568M | Dense/sparse/multi-vector embeddings |
| **BAAI/bge-reranker-v2-m3** | ~568M | Cross-encoder reranking |

### Retrieval Pipeline

The service supports the industry-standard two-stage retrieval pipeline:

```
Query → Bi-Encoder (BGE-M3) → Top-K Candidates → Cross-Encoder (Reranker) → Final Ranking
```

1. **Bi-Encoder Stage** ([`/v1/embeddings`](app/main.py#L67), [`/v1/embeddings/hybrid`](app/main.py#L136))
   - Fast retrieval over large document collections
   - Supports dense, sparse, and hybrid search

2. **Cross-Encoder Stage** ([`/v1/rerank`](app/main.py#L89))
   - Expensive but accurate pairwise scoring
   - Applied only to candidate subsets (typically 20-100 passages)

## Installation

### Prerequisites

- Python 3.12+
- CUDA-capable GPU
- [uv](https://github.com/astral-sh/uv) package manager

### Setup

```bash
# Install dependencies
uv sync

# Models will be downloaded automatically on first run from HuggingFace
# BAAI/bge-m3 and BAAI/bge-reranker-v2-m3
```

## Running the Service

```bash
# Start the server (default: http://0.0.0.0:12214)
./run.sh
```

The service runs with `--workers 1` by design. Each worker process loads its own copy of the models on GPU, and multi-worker setups require proper GPU sharding (e.g., 1 worker per GPU).

## API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:12214/docs
- **ReDoc**: http://localhost:12214/redoc

## API Endpoints

### Health Check

```http
GET /health
```

### Dense Embeddings

Generate dense embeddings for semantic search.

```http
POST /v1/embeddings
```

**Request:**
```json
{
  "texts": ["What is BGE M3?", "Transformers are neural networks."]
}
```

**Response:**
```json
{
  "embeddings": [[0.123, 0.456, ...], [0.789, 0.012, ...]]
}
```

### Sparse Embeddings

Generate sparse lexical embeddings (learned BM25-style) for precise term matching.

```http
POST /v1/embeddings/sparse
```

**Request:**
```json
{
  "texts": ["What is BGE M3?"]
}
```

**Response (Milvus-compatible):**
```json
{
  "sparse_embeddings": [
    {"indices": [1042, 5831, 12905], "values": [0.523, 0.841, 0.236]}
  ]
}
```

### Hybrid Embeddings

Generate both dense and sparse embeddings in one call.

```http
POST /v1/embeddings/hybrid
```

**Request:**
```json
{
  "texts": ["What is BGE M3?"]
}
```

**Response:**
```json
{
  "dense_embeddings": [[0.123, 0.456, ...]],
  "sparse_embeddings": [
    {"indices": [1042, 5831, 12905], "values": [0.523, 0.841, 0.236]}
  ]
}
```

### Reranking

Re-rank passages for a query using cross-encoder scoring.

```http
POST /v1/rerank
```

**Request:**
```json
{
  "query": "What is BGE M3?",
  "passages": [
    "BGE M3 is a multilingual embedding model.",
    "BM25 is a traditional lexical algorithm.",
    "Transformers use self-attention."
  ],
  "normalize": true
}
```

**Response:**
```json
{
  "scores": [0.9876, 0.0234, 0.0456]
}
```

## Usage Examples

### Python Client

```python
import requests

# Dense embeddings
response = requests.post("http://localhost:12214/v1/embeddings", json={
    "texts": ["Hello world", "BGE M3 model"]
})
embeddings = response.json()["embeddings"]

# Reranking
response = requests.post("http://localhost:12214/v1/rerank", json={
    "query": "What is BGE M3?",
    "passages": ["Passage 1", "Passage 2", "Passage 3"],
    "normalize": True
})
scores = response.json()["scores"]
ranked_passages = sorted(zip(passages, scores), key=lambda x: -x[1])
```

### Hybrid Retrieval Pipeline

```python
# Step 1: Generate hybrid embeddings for documents
response = requests.post("http://localhost:12214/v1/embeddings/hybrid", json={
    "texts": documents
})
dense = response.json()["dense_embeddings"]
sparse = response.json()["sparse_embeddings"]

# Step 2: Index in Milvus (or similar vector DB)

# Step 3: Retrieve top-K candidates

# Step 4: Rerank candidates
response = requests.post("http://localhost:12214/v1/rerank", json={
    "query": query,
    "passages": candidates,
    "normalize": True
})
final_scores = response.json()["scores"]
```

## Implementation Details

### Production Safety

The service includes critical environment variables to ensure production safety ([`app/main.py`](app/main.py#L1-L6)):

```python
os.environ["FLAG_EMBEDDING_DISABLE_MULTIPROCESS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
```

These prevent multiprocessing issues in containerized environments and ensure thread-safe GPU inference.

### Model Loading

Models are loaded once at startup using FastAPI's lifespan context manager ([`app/main.py`](app/main.py#L30-L50)):

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.embedding_service = BGEEmbeddingService()
    app.state.reranker_service = BGERerankerService()
    yield
```

### Synchronous Endpoints

All inference endpoints use **synchronous** (`def`) not async (`async def`) handlers by design. GPU inference is compute-bound, not I/O-bound, so asyncio provides no benefit and may increase latency.

## Background

### BGE-M3 Sparse Retrieval

BGE-M3 introduces learned sparse embeddings that combine the precision of BM25 with semantic understanding. Unlike traditional TF-IDF, sparse weights are learned via a linear + ReLU projection of transformer hidden states.

See [app/README.md](app/README.md) for detailed explanation of sparse retrieval mechanics.

### Bi-Encoder vs Cross-Encoder

| Aspect | Bi-Encoder | Cross-Encoder |
|--------|-----------|---------------|
| Input | Single text | Query + passage pair |
| Output | Embedding vector | Relevance score |
| Use Case | Retrieval over large corpora | Reranking top-K results |
| Speed | Fast (pre-indexable) | Slow (pairwise inference) |

## Project Structure

```
bge-service/
├── app/
│   ├── main.py              # FastAPI application & endpoints
│   ├── models/
│   │   ├── embedding.py     # BGE-M3 wrapper
│   │   └── reranker.py      # BGE-Reranker wrapper
│   ├── schemas.py           # Pydantic request/response models
│   └── settings.py          # Configuration
├── run_bge_me.py            # Standalone BGE-M3 example
├── run_bge_reranker.py      # Standalone reranker example
├── run.sh                   # Server startup script
├── pyproject.toml           # Project dependencies
└── README.md                # This file
```

## License

See [LICENSE](LICENSE) file.

## References

- [BGE-M3 Paper](https://arxiv.org/abs/2402.03216)
- [BGE-Reranker-V2 Documentation](https://bge-model.com/Introduction/reranker.html)
- [FlagEmbedding GitHub](https://github.com/FlagOpen/FlagEmbedding)
