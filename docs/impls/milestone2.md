# Milestone 2 Implementation: Document Upload and List

## Overview

Implementation of **Milestone 2: Document Upload and List** from the PLAN.md project roadmap.

## Goals Achieved

- Support uploading educational documents to the system
- Display uploaded documents in a list view in the UI
- Store files in MinIO object storage
- Persist document metadata in PostgreSQL database

## Documentation Created

### MinIO Research Documents

Created two research documents in [`docs/minio/`](../docs/minio/):

1. **[`minio-object-naming.md`](../docs/minio/minio-object-naming.md)** - MinIO Object Naming Best Practices
   - Safe characters and naming conventions
   - Hierarchical organization patterns
   - Metadata strategies for preserving original filenames

2. **[`minio-async-python.md`](../docs/minio/minio-async-python.md)** - MinIO Async Python SDK Research
   - Official SDK is synchronous only
   - Recommended approach: `run_in_executor` for blocking operations
   - Alternative: `aiobotocore` (async S3-compatible SDK)

## Backend Implementation

### 1. MinIO Storage Client

**File:** [`eduagent/storage/minio_client.py`](../../eduagent/storage/minio_client.py)

Key components:

- `MinIOConfig`: Pydantic model for MinIO configuration (no dependency on `settings`)
- `MinIOStorage`: Async wrapper using `run_in_executor` for blocking MinIO operations
  - `ensure_bucket_exists()`: Create bucket if not exists
  - `generate_object_name()`: Generate timestamped object names
  - `upload_file()`: Upload file to MinIO
  - `download_file()`: Download file from MinIO
  - `delete_file()`: Delete file from MinIO
  - `file_exists()`: Check if file exists in MinIO

**Design principle:** MinIO client does NOT depend on `eduagent.settings`, following the module design principle of "less dependency is much better".

### 2. Documents API Endpoint

**File:** [`eduagent/api/endpoints/documents.py`](../../eduagent/api/endpoints/documents.py)

API endpoints implemented:

- `POST /api/v1/documents` - Upload document
  - Accepts multipart file upload
  - Saves to MinIO using `MinIOStorage`
  - Creates database record in `source_document` table
  - Returns: `DocumentResponse` with metadata

- `GET /api/v1/documents` - List all documents
  - Returns list sorted by creation date (newest first)
  - Returns: `list[DocumentResponse]`

- `GET /api/v1/documents/{document_id}` - Get specific document
  - Returns single document by ID
  - Returns: `DocumentResponse` or 404 if not found

### 3. Database Models

**File:** [`eduagent/documents/models.py`](../../eduagent/documents/models.py)

Models defined (pre-existing, extended):

- `Base`: SQLAlchemy declarative base for document models
- `SourceDocument`: Database table with fields:
  - `id`: Primary key
  - `filename`: Original filename (indexed)
  - `storage_path`: MinIO object name
  - `file_size`: File size in bytes
  - `content_type`: MIME content type
  - `created_at`: Creation timestamp
  - `updated_at`: Last update timestamp
- `DocumentResponse`: Pydantic model for API responses
- `DocumentCreate`: Pydantic model for input validation

### 4. API Router Registration

**File:** [`eduagent/api/endpoints/__init__.py`](../../eduagent/api/endpoints/__init__.py)

Added `documents_router` to `api_routers` list.

### 5. API Lifespan Update

**File:** [`eduagent/api/api.py`](../../eduagent/api/api.py)

Updated `lifespan()` function to:
- Import `DocumentsBase` from documents module
- Create database tables on startup using `create_tables_for_module(DocumentsBase)`

## Frontend Implementation

### 1. API Client Extension

**File:** [`eduagent/ui/api_client.py`](../../eduagent/ui/api_client.py)

Added methods:
- `upload_document(filename, file_bytes)`: Upload document to API
- `list_documents()`: List all documents
- `get_document(document_id)`: Get specific document

### 2. Documents Page

**File:** [`eduagent/ui/pages/documents.py`](../../eduagent/ui/pages/documents.py)

New page with two tabs:

**Upload Tab:**
- File uploader supporting: PDF, DOCX, TXT, Markdown
- Displays file info (name, size) before upload
- Upload button with spinner and success/error feedback

**List Tab:**
- Refresh button to reload document list
- Displays documents in expandable accordions
- Shows metadata: filename, size (humanized), content type, timestamps
- Empty state message when no documents

### 3. UI Main Navigation Update

**File:** [`eduagent/ui/main.py`](../../eduagent/ui/main.py)

**Refactoring done:**
- Combined `TEACHER_NAV_OPTIONS` and `PAGE_HANDLERS` into `TEACHER_PAGES`
- Eliminated duplication by defining page name and handler together
- Added "文档管理" to navigation options
- Updated `__init__.py` to export new page renders

**Changed structure:**
```python
# Before (duplicate definitions)
TEACHER_NAV_OPTIONS = ["总览", "文档管理", ...]
PAGE_HANDLERS = {"总览": overview.render, "文档管理": documents.render, ...}

# After (single source of truth)
TEACHER_PAGES = [
    ("总览", overview.render),
    ("文档管理", documents.render),
    ...
]
TEACHER_NAV_OPTIONS = [name for name, _ in TEACHER_PAGES]
```

**Benefits:**
- Single source of truth for page definitions
- Prevents mismatch between nav options and handlers
- More maintainable

## Technical Decisions & Principles Applied

### From CLAUDE.md

1. **Module Design Principle: Self-contained modules**
   - Document models stay in `eduagent/documents/`
   - Each module owns its database models

2. **Module Design Principle: Less dependency is much better**
   - `MinIOConfig` accepts config instead of importing `settings`
   - MinIO storage client is independent of settings module

3. **Prefer Pydantic models over dict/list**
   - Used `MinIOConfig` for type-safe configuration
   - Used `DocumentResponse` for API responses

4. **Async/Blocking I/O handling**
   - MinIO operations wrapped in `run_in_executor` to avoid blocking event loop
   - Maintains async compatibility in FastAPI application

## Next Steps

### Immediate
- Run `ruff` and `pyright` static checks to verify code quality
- Test document upload and list functionality with actual API

### Future Milestones
- Milestone 3: Document parsing and chunking with Pandoc
- Milestone 4: Embedding generation and Milvus indexing
- Milestone 5: Question generation with RAG retrieval

## Acceptance Criteria Met

- [x] Upload documents via API
- [x] Store files in MinIO with object storage
- [x] Persist metadata in PostgreSQL database
- [x] List uploaded documents in UI
- [ ] Test with actual file uploads (manual testing)
- [ ] Static analysis checks (ruff, pyright) pending
