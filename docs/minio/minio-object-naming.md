# MinIO Object Naming Best Practices

## Overview

This document outlines best practices for naming objects in MinIO for the EduAgent project, focusing on document upload functionality.

## Key Findings

### Does MinIO Support User-Provided UUIDs?

**Yes**, MinIO fully supports custom object names including user-provided UUIDs. When uploading to MinIO, you explicitly specify the object key (filename), allowing you to use any valid string including UUIDs.

### Is Using User-Provided UUIDs a Best Practice?

**Yes**, it is considered a good practice for several reasons:

- **Deterministic naming**: You can predict and reference the object name before/after upload
- **Avoids duplicates**: UUIDs prevent naming conflicts
- **Metadata linkage**: The UUID in your database can directly map to the MinIO object name

## Object Naming Conventions

### Safe Characters

- Lowercase letters (a-z)
- Numbers (0-9)
- Hyphens (-)
- Underscores (_)
- Forward slashes (/) - for hierarchical organization
- Periods (.)

### Character Limits

- Maximum: 1024 UTF-8 encoded characters
- Recommended: 255 characters for optimal compatibility

### What to Avoid

- Spaces (use hyphens or underscores instead)
- Special characters: `# % & { } | \ < > * ? " '`
- Control characters
- Names longer than 1024 characters
- Multiple consecutive slashes
- Names starting with `.` (hidden files)
- Leading or trailing spaces

## Recommended Naming Patterns

### 1. Hierarchical Organization

Use forward slashes to create logical folder structures:

```
documents/user-12345/2024-01-15_contract.pdf
uploads/year=2024/month=01/invoice-10023.pdf
images/abc123-456def-789ghi.jpg
```

### 2. Common Naming Strategies

**Timestamp-based:**
- `20240115_143022_invoice.pdf`
- `2024-01-15/orders-2024-01-15.json`

**UUID-based:**
- `550e8400-e29b-41d4-a716-446655440000/photo.jpg`

**Hash-based:**
- `a1b2c3d4e5f6/document.pdf`

**Composite keys:**
- `{tenant-id}/{user-id}/{doc-id}/{version}.ext`
- `user-12345-profile-picture.jpg`
- `app-v2.3.0/config.json`

### Good vs Bad Examples

```
✅ Good:
- documents/user-12345/2024-01-15_contract.pdf
- images/abc123-456def-789ghi.jpg
- uploads/2024/01/15/inv-10023.pdf

❌ Bad:
- documents/User 12345/Contract (Final)!.pdf (spaces, special chars)
- uploads/My File #1.pdf
- .hidden-file.txt
```

## Upload with Custom Names

### JavaScript/Node.js SDK Example

```javascript
const metaData = {
  'Content-Type': 'application/pdf',
  'X-Amz-Meta-Original-Filename': 'My Original File.pdf',
  'X-Amz-Meta-Tenant-ID': 'tenant-123',
  'X-Amz-Meta-Uploaded-By': 'user@example.com'
};

await minioClient.putObject(
  bucketName,
  'uploads/2024/01/user-12345-document-v2.pdf',  // Custom object key
  stream,
  size,
  metaData
);
```

## Additional Recommendations

### 1. Store Original Filename in Metadata

If you need to preserve the original filename, store it in the `X-Amz-Meta-Original-Filename` header for display purposes.

### 2. Implement Consistent Patterns

Use the same naming convention across your entire application for maintainability.

### 3. Consider Lifecycle Management

Hierarchical naming helps with configuring lifecycle rules for old/expired objects.

### 4. Use Multipart Uploads

For files larger than 5MB, use multipart uploads for better reliability.

## EduAgent Project Implementation

### Recommended Pattern

For the EduAgent document upload feature, use a hybrid approach:

```python
# Option 1: Use UUID from database as the MinIO object name
object_name = f"documents/{document_id}/{original_filename}"

# Option 2: Use a new UUID for each upload
object_name = f"uploads/{timestamp}/{uuid.uuid4()}.pdf"
```

### Metadata Strategy

Store additional context in object metadata:

```python
metadata = {
    'Content-Type': 'application/pdf',
    'X-Amz-Meta-Original-Filename': original_filename,
    'X-Amz-Meta-Uploaded-By': user_id,
    'X-Amz-Meta-Document-Type': 'textbook'
}
```

## References

- [MinIO Best Practices - Object Naming Conventions](https://docs.min.io/docs/minio-best-practices.html)
- [MinIO Object Storage Naming Conventions & Best Practices](https://min.io/resources/docs/minio-object-naming-conventions.pdf)
- [Stack Overflow: MinIO Upload with Custom Object Name](https://stackoverflow.com/questions/78965432/minio-upload-with-custom-object-name)
- [MinIO Production Deployment Guide - Object Naming](https://min.io/docs/minio/linux/operations/install-deploy-manage/deploy-minio-single-node-single-drive.html)
