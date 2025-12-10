# Service-to-Service JWT Authentication

EduAgent no longer exposes public authentication routes. Next.js (or any trusted
frontend) is responsible for authenticating end users and calling the FastAPI
backend with a short-lived service JWT.

## Token Format

- **Algorithm**: HS256 (configurable via `service_auth.algorithm`)
- **Claims**:
  - `iss`: issuer identifier, default `nextjs-service`
  - `aud`: audience identifier, default `eduagent-api`
  - `sub`: upstream user identifier
  - `exp`/`iat`: short lifetime (30–120 seconds recommended)
  - Optional scopes/roles inside additional claims

## Key Management

1. Generate a 256-bit secret:
   ```bash
   openssl rand -base64 32
   ```
2. Store the secret in both Next.js and FastAPI (e.g., `SERVICE_JWT_SECRET` env
   var). Rotate secrets by supporting both a current and previous secret.
3. Update `eduagent.toml` / `example.eduagent.toml` under `[service_auth]` for
   local development.

## Request Flow

```
Browser -> Next.js (auth) -> FastAPI (/api/v1/...)
               |
               `-- signs Authorization: Bearer <jwt>
```

FastAPI validates the JWT via `require_service_token` (HTTP Bearer dependency)
before executing any router logic.
