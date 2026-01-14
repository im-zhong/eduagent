# MinIO Async Python SDK Research

## Overview

This document researches async support for MinIO in Python, specifically for integrating with FastAPI and async frameworks.

## Key Findings

### Official MinIO Python SDK

The official `minio` Python SDK:
- **Synchronous only**: Uses blocking I/O operations based on `requests`
- **No official async SDK**: As of 2025, there is no official async MinIO Python SDK
- Documentation: [MinIO Python SDK](https://docs.min.io/docs/python-client-quickstart-guide.html)

### Async Support Options

#### 1. Use `run_in_executor` (Recommended for Simplicity)

Run blocking MinIO operations in a thread pool using `asyncio.loop.run_in_executor()`.

**Advantages:**
- Simple wrapper around official SDK
- No additional dependencies
- Easy to maintain
- Good for most use cases

**Pattern:**
```python
import asyncio
from functools import partial
from minio import Minio

async def upload_to_minio(bucket: str, object_name: str, data: bytes) -> None:
    client = Minio(endpoint, access_key, secret_key, secure=False)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,  # Use default thread pool
        partial(client.put_object, bucket, object_name, data, len(data))
    )
```

#### 2. Use `aiobotocore` (More Robust)

`aiobotocore` is an async S3 SDK that works with MinIO (S3-compatible API).

**Advantages:**
- Mature async implementation
- Native async/await support
- Better for high-concurrency scenarios

**Pattern:**
```python
import asyncio
from aiobotocore.session import AioSession

async def upload_with_aiobotocore():
    session = AioSession()
    async with session.create_client(
        's3',
        endpoint_url='http://localhost:9000',
        aws_access_key_id='access_key',
        aws_secret_access_key='secret_key',
    ) as client:
        await client.put_object(
            Bucket='my-bucket',
            Key='my-object',
            Body=b'data'
        )
```

#### 3. Community Async Wrappers (Use with Caution)

Third-party packages like `minio-async` exist, but:
- Check maintenance status before using
- May have limited features compared to official SDK
- Verify compatibility with MinIO API version

## EduAgent Project Recommendation

For the EduAgent project, **use `run_in_executor`** approach because:

1. **Simplicity**: No additional dependencies beyond official MinIO SDK
2. **Maintainability**: Code is easy to understand and debug
3. **Adequate Performance**: Thread pool is sufficient for typical document upload workloads
4. **Future Compatibility**: Can be upgraded to aiobotocore if needed later

## Implementation Pattern

### MinIO Client Wrapper

```python
from functools import partial
from minio import Minio
from sqlalchemy.ext.asyncio import AsyncSession

class MinIOStorage:
    def __init__(self, endpoint: str, access_key: str, secret_key: str, bucket: str):
        self.client = Minio(endpoint, access_key, secret_key, secure=False)
        self.bucket = bucket

    async def upload_file(
        self,
        file_data: bytes,
        object_name: str,
        content_type: str,
        loop: asyncio.AbstractEventLoop | None = None,
    ) -> None:
        """Upload file to MinIO using thread executor."""
        loop = loop or asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            partial(
                self.client.put_object,
                self.bucket,
                object_name,
                file_data,
                len(file_data),
                content_type=content_type,
            ),
        )

    async def download_file(self, object_name: str) -> bytes:
        """Download file from MinIO using thread executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            partial(self.client.get_object, self.bucket, object_name).read,
        )
```

### FastAPI Integration

```python
from fastapi import FastAPI, UploadFile
from fastapi.concurrency import run_in_threadpool

@router.post("/documents")
async def upload_document(file: UploadFile):
    # Read file content
    content = await file.read()

    # Upload to MinIO (blocking operation in thread pool)
    await run_in_threadpool(
        storage.client.put_object,
        bucket_name,
        object_name,
        content,
        len(content),
    )

    # Save metadata to database
    # ...
```

## Performance Considerations

### Thread Pool Size

The default `ThreadPoolExecutor` may need tuning for high-volume uploads:

```python
import concurrent.futures

# Create custom thread pool
executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)

# Use custom executor
await loop.run_in_executor(executor, ...)
```

### Large File Uploads

For files larger than 5MB, consider:
- Using MinIO's multipart upload API
- Implementing progress tracking
- Configuring appropriate timeouts

## References

- [MinIO Python SDK Documentation](https://docs.min.io/docs/python-client-quickstart-guide.html)
- [AsyncIO Thread Executors](https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.loop.run_in_executor)
- [FastAPI Concurrency](https://fastapi.tiangolo.com/tutorial/async/#async-and-await)
- [aiobotocore Documentation](https://aiobotocore.readthedocs.io/)
