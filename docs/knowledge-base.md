# ClassFlow Knowledge Base

Last updated: 2026-07-27

## Project Goal

ClassFlow is a FastAPI and PostgreSQL backend for class-based academic coordination. The main product will support users, classrooms, memberships, courses, shared tasks, private tasks, announcements, resources, notifications, dashboards, and a future class-scoped RAG chatbot.

The project should be built in phases. The most important early milestone is a working non-AI MVP: authentication, classrooms, memberships, courses, tasks, and personalized feed.

## Current Backend Stack

- Python virtual environment: `myvenv`
- API framework: FastAPI
- Database: PostgreSQL
- ORM: SQLAlchemy async
- Migrations: Alembic
- Auth: JWT access tokens plus database-backed refresh tokens
- Password hashing: `pwdlib[argon2]`
- JWT library: `PyJWT`
- Testing: pytest

## Project Structure

```text
app/
  api/
    routes/        Feature route modules
    dependencies.py
    router.py
  core/            Settings, security, logging, exceptions, handlers
  database/        SQLAlchemy base/session and Alembic migrations
  models/          SQLAlchemy ORM models
  repositories/    Database query layer
  schemas/         Pydantic request/response schemas
  services/        Business logic
  ai/              Future RAG/chatbot integration
tests/
```

Structure decision:
- Routes should stay thin.
- Services own business rules.
- Repositories own database queries.
- Schemas control API input/output.
- Models map database tables.
- `ai/` is isolated so future RAG retrieval can stay class-scoped and permission-aware.

## Environment Settings

App settings use the `CLASSFLOW_` prefix to avoid collisions with global environment variables.

Important variables:

```env
CLASSFLOW_PROJECT_NAME=ClassFlow
CLASSFLOW_ENVIRONMENT=local
CLASSFLOW_DEBUG=true
CLASSFLOW_API_V1_PREFIX=/api/v1
CLASSFLOW_DATABASE_URL=postgresql+asyncpg://...
CLASSFLOW_SECRET_KEY=...
CLASSFLOW_JWT_ALGORITHM=HS256
CLASSFLOW_ACCESS_TOKEN_EXPIRE_MINUTES=30
CLASSFLOW_REFRESH_TOKEN_EXPIRE_DAYS=7
```

Never commit real `.env` secrets. Use `.env.example` for placeholders.

## Database And Migrations

Database schema is managed through Alembic. Do not use `Base.metadata.create_all(...)` in `main.py`.

Current migrations:

```text
9646011027a1_module_zero_baseline.py
ac57ddd31bea_create_users_table.py
f29de09fc869_create_refresh_tokens_table.py
```

Useful commands:

```powershell
alembic current
alembic history
alembic revision --autogenerate -m "message"
alembic upgrade head
alembic downgrade -1
```

Current DB session setup uses `NullPool`. This keeps local FastAPI `TestClient` checks stable with asyncpg by avoiding reuse of loop-bound pooled connections. Later, deployment can make pooling configurable.

## Module 0 Status

Completed:
- FastAPI application structure
- Environment settings
- PostgreSQL connection
- SQLAlchemy async session management
- Alembic setup
- Standardized error response handlers
- Logging setup
- Health endpoint
- Initial pytest setup

Verified:

```powershell
pytest
uvicorn app.main:app --reload
Invoke-RestMethod http://127.0.0.1:8000/health
```

Expected health response:

```json
{
  "status": "ok",
  "service": "ClassFlow",
  "environment": "local"
}
```

## Module 1 Status - Authentication

Implemented:
- `users` table
- `refresh_tokens` table
- User registration
- Password hashing
- Login with `OAuth2PasswordRequestForm`
- JWT access tokens
- Refresh token generation, storage, rotation, and revocation
- Logout through refresh-token revocation
- Protected current-user dependency
- `GET /api/v1/users/me`
- `PATCH /api/v1/users/me`

Current auth endpoints:

```text
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/refresh
POST /api/v1/auth/logout
GET  /api/v1/users/me
PATCH /api/v1/users/me
```

Auth behavior:
- Login returns an access token and refresh token.
- Access token is used for protected endpoints.
- Refresh token is stored in the database as a SHA-256 hash, not in plain text.
- Refresh endpoint rotates refresh tokens: the old refresh token becomes invalid and a new one is issued.
- Logout revokes the refresh token.
- JWT access tokens remain valid until expiry because they are stateless. The frontend should discard the access token on logout.

Swagger testing:
- Register first.
- Use `/auth/login` with form fields `username` and `password`.
- Click Swagger `Authorize`.
- Use the access token for `/users/me`.

## Important Decisions

- Refresh tokens were added during Module 1 instead of postponing them.
- Refresh tokens are opaque random strings, not JWTs.
- Only refresh-token hashes are stored in PostgreSQL.
- We are not blacklisting access tokens yet.
- `GET /users/me` is correct because it reads the authenticated user's profile.
- `PATCH /users/me` is correct for partial profile updates.
- `OAuth2PasswordRequestForm` is used so Swagger's `Authorize` flow works.
- `get_db_session()` lives in `app/database/session.py`, not inside auth-specific code.

## Verification Already Performed

Module 1 smoke flow passed:

```text
register 201
login 200
me 200
refresh 200
old_refresh_reuse 401
logout 200
refresh_after_logout 401
```

Pytest passed:

```text
2 passed
```

Alembic current head:

```text
f29de09fc869
```

## Next Recommended Module

Module 2 - Classrooms and Membership.

Recommended implementation order:

```text
models
migration
schemas
repositories
services
permission dependencies
routes
tests
manual Swagger checks
```

Core Module 2 scenario:

```text
User A creates a classroom.
User A automatically becomes approved representative.
User B requests to join.
User B cannot access class content while pending.
User A approves User B.
User B can access class content.
User B cannot use representative-only endpoints.
```

Likely tables:

```text
classrooms
class_memberships
```

Likely permission dependencies:

```text
get_membership()
get_approved_member()
get_class_representative()
```

Do not start courses/tasks until the full two-user classroom membership scenario works.
