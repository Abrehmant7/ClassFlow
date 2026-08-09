# ClassFlow Knowledge Base

Last updated: 2026-07-30

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
85d87d97c121_create_classrooms_and_class_memberships.py
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

## Module 2 Status - Classrooms And Memberships

Implemented:
- `classrooms` table
- `class_memberships` table
- Classroom creation with generated unique join codes
- Automatic approved representative membership for the classroom creator
- Classroom read/update/list-mine endpoints
- Join-class requests using a join code
- Membership statuses: `pending`, `approved`, `rejected`, `removed`
- Membership roles: `representative`, `student`
- Representative-only approval and rejection of join requests
- Representative-only member removal
- Protection against removing the class creator
- Approved-member checks for class access
- Reusable class membership permission dependencies

Current classroom endpoints:

```text
POST   /api/v1/classes
GET    /api/v1/classes/mine
GET    /api/v1/classes/{class_id}
PATCH  /api/v1/classes/{class_id}
POST   /api/v1/classes/{class_id}/join
GET    /api/v1/classes/{class_id}/requests
GET    /api/v1/classes/{class_id}/members
```

Current membership endpoints:

```text
PATCH  /api/v1/memberships/{membership_id}/approve
PATCH  /api/v1/memberships/{membership_id}/reject
DELETE /api/v1/memberships/{membership_id}
```

Module 2 behavior:
- When a user creates a classroom, the service creates both the classroom and creator membership in one transaction.
- The creator membership is created with role `representative` and status `approved`.
- Users join a classroom through `POST /classes/{class_id}/join` with the correct `join_code`.
- Existing approved users cannot send another join request.
- Existing pending users cannot duplicate their join request.
- Rejected or removed users may request to join again.
- Pending users cannot access `GET /classes/{class_id}` because it requires approved membership.
- Only approved representatives can update a classroom, list join requests, approve requests, reject requests, or remove members.
- Membership approval/rejection/removal verifies that the acting representative belongs to the same class as the target membership.

Permission dependencies:

```text
get_membership()
get_approved_membership()
require_representative()
```

Compatibility aliases currently exist:

```text
get_approved_member = get_approved_membership
get_class_representative = require_representative
```

Important Module 2 files:

```text
app/models/classroom.py
app/schemas/classroom.py
app/repositories/classroom.py
app/repositories/membership.py
app/services/classroom.py
app/api/dependencies.py
app/api/routes/classes.py
app/api/routes/memberships.py
```

Manual Module 2 smoke flow:

```text
User A registers and logs in.
User A creates a classroom.
User A automatically becomes approved representative.
User B registers and logs in.
User B requests to join using the class join code.
User B cannot access the class while pending.
User A lists pending requests.
User A approves User B's membership request.
User B can now access the class.
User B cannot access representative-only routes.
```

Swagger testing notes:
- Use `/auth/login` and Swagger `Authorize` separately for User A and User B.
- Copy the `join_code` from User A's created classroom response.
- Use User B's token when calling `POST /classes/{class_id}/join`.
- Use User A's token when calling representative-only endpoints.
- Switch back to User B's token to confirm approved-member access works but representative access fails.

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
85d87d97c121
```

## Next Recommended Module

Module 3 - Courses.

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

Module 3 should build on Module 2 permissions. Course creation and management should be class-scoped and should use the existing membership dependencies:

```text
get_approved_membership()
require_representative()
```

Do not create course behavior that bypasses classroom membership checks. Class content should require approved membership, and representative-only course actions should require `require_representative()`.

Likely next tables:

```text
courses
```

Likely next endpoints:

```text
POST   /classes/{class_id}/courses
GET    /classes/{class_id}/courses
GET    /courses/{course_id}
PATCH  /courses/{course_id}
DELETE /courses/{course_id}
```
