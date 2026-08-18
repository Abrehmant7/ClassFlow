# ClassFlow Knowledge Base

Last updated: 2026-08-11

## Project Goal

ClassFlow is a FastAPI and PostgreSQL backend for class-based academic coordination. The main product will support users, classrooms, memberships, courses, shared tasks, personal tasks, announcements, resources, notifications, dashboards, and a future class-scoped RAG chatbot.

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

Documentation convention:
- Repositories should usually avoid docstrings; method names should explain the query.
- Services should use short docstrings for public methods that encode business rules.
- Services may use brief comments for transaction boundaries, edge cases, or non-obvious product rules.
- Routes should usually avoid comments because endpoint names, schemas, and dependencies should explain the behavior.
- `docs/knowledge-base.md` should store module behavior, product decisions, endpoint lists, smoke flows, and cross-module rules.

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
00f7fc38ba77_create_courses_and_course_registrations.py
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

## Module 3 Status - Courses And Registrations

Implemented:
- `courses` table for the global course catalogue
- `class_courses` table for attaching catalogue courses to classrooms
- `course_registrations` table for student registrations
- Case-insensitive unique course name index through `LOWER(name)`
- Unique course code constraint
- Unique classroom/course constraint to prevent adding the same course twice to one class
- Unique membership/class-course registration constraint
- Course name normalization before saving
- Course code normalization before saving
- Searchable global course catalogue
- Class-scoped course management
- Default and optional class courses
- Student course registration, drop, and re-registration
- Automatic registration in default courses when a membership is approved
- Automatic registration of existing approved members when a representative adds a new default course

Current course catalogue endpoints:

```text
GET  /api/v1/courses
GET  /api/v1/courses/{course_id}
POST /api/v1/courses
```

Current class course endpoints:

```text
POST   /api/v1/classes/{class_id}/courses
GET    /api/v1/classes/{class_id}/courses
PATCH  /api/v1/class-courses/{class_course_id}
DELETE /api/v1/class-courses/{class_course_id}
```

Current course registration endpoints:

```text
POST   /api/v1/class-courses/{class_course_id}/register
DELETE /api/v1/class-courses/{class_course_id}/register
GET    /api/v1/classes/{class_id}/my-courses
```

Module 3 behavior:
- `GET /courses` supports optional search with `?search=database`.
- `POST /courses` requires the user to be an approved representative in at least one class.
- `POST /courses` rejects duplicate course codes and duplicate normalized course names.
- Course codes are stored uppercase with surrounding whitespace removed.
- Course names are stored with repeated whitespace collapsed.
- Representatives manage class courses only for classrooms where they are approved representatives.
- Approved class members can list class courses and their own registered courses.
- Pending members cannot register for courses.
- Students cannot add, update, or remove class courses.
- A membership from one classroom cannot register for a course attached to another classroom.
- Default courses mean auto-registered courses, not mandatory courses.
- Students can drop and re-register default courses the same way they can drop and re-register optional courses.
- Deleting a class course soft-removes it by setting `is_active=False`.
- Dropping a course registration sets `is_active=False` and stores `dropped_at`.
- Re-registering an already dropped course reactivates the existing registration instead of creating a duplicate row.

Important Module 3 files:

```text
app/models/course.py
app/schemas/course.py
app/repositories/course.py
app/services/course.py
app/api/routes/courses.py
app/api/routes/class_courses.py
app/repositories/membership.py
app/services/classroom.py
app/api/router.py
```

Manual Module 3 smoke flow:

```text
Representative searches the global catalogue.
Representative creates a missing catalogue course.
Representative adds default and optional courses to a class.
Student requests to join the class.
Representative approves the student's membership.
Default course registration is created automatically.
Student lists their class courses.
Student registers for an optional course.
Student drops the optional course.
Student re-registers for the optional course.
```

Module 3 verification notes:
- Duplicate catalogue course code should return `409`.
- Duplicate normalized course name should return `409`.
- Adding the same course twice to one classroom should return `409` while active.
- Pending members should receive `403` for registration.
- Students should receive `403` for class-course management endpoints.
- Cross-class registration should receive `403`.
- If Swagger shows `relation "courses" does not exist`, run `alembic upgrade head` and confirm `alembic current` shows the Module 3 migration.

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
00f7fc38ba77
```

## Module 4 Backend Status - Tasks, Progress And Attachments

Implemented backend behavior:
- Shared tasks created and managed by approved class representatives.
- Personal tasks created, updated, completed, reopened, archived, and manually deleted by their creator only.
- Personal tasks may have no class, may be linked to a classroom, or may be linked to a registered class course.
- Shared-task progress stored per approved member through `task_progress`; missing progress rows mean pending.
- Supporting task attachments stored by internal `storage_key`, with download routed through permission-checked API endpoints.
- Attachment upload validates extension, content type, size, empty files, and path traversal.
- Attachment storage failures do not create database records.
- Database failures after file storage remove the uploaded file.

Current task endpoints:

```text
POST   /api/v1/classes/{class_id}/tasks
GET    /api/v1/classes/{class_id}/tasks
POST   /api/v1/tasks
GET    /api/v1/tasks
GET    /api/v1/tasks/{task_id}
PATCH  /api/v1/tasks/{task_id}
DELETE /api/v1/tasks/{task_id}
PUT    /api/v1/tasks/{task_id}/progress
POST   /api/v1/tasks/{task_id}/attachments
GET    /api/v1/tasks/{task_id}/attachments
GET    /api/v1/attachments/{attachment_id}/download
DELETE /api/v1/attachments/{attachment_id}
```

Important Module 4 backend files:

```text
app/models/task.py
app/schemas/task.py
app/repositories/task.py
app/services/task.py
app/api/routes/tasks.py
app/database/migrations/versions/f2659f4668ac_create_tasks_progress_and_attachments.py
app/database/migrations/versions/b7428b2d4f91_make_personal_tasks_classroom_optional.py
```

Module 4 visibility and management rules:
- Approved representatives can view and manage all shared tasks in their classroom.
- Representatives cannot view another user's personal task.
- Students can view shared class-wide tasks for classes where they are approved members.
- Students can view shared course tasks only when they have an active registration for that class course.
- Personal tasks are visible and manageable only by their creator.
- Completing a personal task sets `status=completed` and `completed_at`; it does not delete the task.
- Shared tasks cannot be marked completed directly; students complete them through progress.
- Cancelled and archived shared tasks cannot receive progress updates.
- Only personal tasks can be hard-deleted.
- Shared attachments can be managed by approved representatives only.
- Personal attachments can be managed by the personal-task creator only.
- Anyone who can view the task can list or download its attachments.

## Next Recommended Module

Module 5 - Personalized Feed, Filtering And Search.

Implemented backend behavior:
- `GET /api/v1/feed` returns the authenticated user's authorized academic feed.
- `GET /api/v1/feed/summary` returns dashboard summary counts using the same visibility and completion rules.
- `GET /api/v1/feed/filter-options` returns approved classrooms and active registered courses for filters.
- `POST /api/v1/personal-tasks` creates personal tasks without accepting visibility or ownership from the client.
- `PUT /api/v1/personal-tasks/{task_id}/complete` completes a personal task without deleting it.
- `PUT /api/v1/personal-tasks/{task_id}/reopen` reopens a personal task and clears `completed_at`.
- Feed inclusion is query-based; no feed table/model is stored.
- Personal tasks are included only for their creator.
- Shared class-wide tasks are included for approved class members.
- Shared course tasks are included only for active course registrations.
- Representatives do not receive every shared course task in their personal feed unless they are also registered.
- Feed items expose normalized `my_completion_status` and lifecycle `task_status`.
- Feed items derive `is_overdue`, `due_group`, `context_type`, permissions, context, creator, and attachment count.
- Feed supports pagination, view filtering, visibility filtering, classroom/course filters, task type, priority, due filters, and authorization-safe search.
- Search trims the term, limits it to 100 characters, and uses database-side case-insensitive matching across task, classroom, and course fields.
- Feed ordering groups overdue, today, upcoming, later, no-deadline, and completed records with priority and stable ID tie-breakers.
- Summary counts overdue, due today, upcoming seven days, no deadline, and completed this week.
- IANA timezones are accepted for feed and summary date boundaries; UTC is the fallback.

Current feed endpoints:

```text
GET /api/v1/feed
GET /api/v1/feed/summary
GET /api/v1/feed/filter-options
POST /api/v1/personal-tasks
PUT /api/v1/personal-tasks/{task_id}/complete
PUT /api/v1/personal-tasks/{task_id}/reopen
```

Supported query parameters:

```text
view=active|completed|archived|all
visibility=all|personal|shared
classroom_id=<id>
class_course_id=<id>
task_type=assignment|quiz|lab|project|presentation|exam|other
priority=low|medium|high|urgent
due=overdue|today|week|later|no_deadline
search=<term>
timezone=UTC
page=1
page_size=20
```

Important Module 5 backend files so far:

```text
app/schemas/feed.py
app/repositories/feed.py
app/services/feed.py
app/api/routes/feed.py
tests/test_feed.py
```

Remaining Module 5 work:
- Backend test expansion for feed summary/filter options and personal-task action endpoints.
- Frontend personal-feed dashboard, filters, cards, quick-add, and summary cards.
