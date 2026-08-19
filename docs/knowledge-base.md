# ClassFlow Knowledge Base

Last updated: 2026-08-19

## Project Goal

ClassFlow is an academic coordination platform for students and class representatives. The near-term product is a working non-AI MVP with authentication, classrooms, memberships, courses, tasks, attachments, and a personal academic feed. Later modules will add announcements, resources, notifications, dashboards, and a class-scoped RAG chatbot.

The product should stay permission-aware. Class content must remain scoped to approved classroom members, course-specific content must remain scoped to registered students, and personal tasks must remain private to their creator even when linked to a class or course.

## Current Stack

Backend:

- FastAPI
- PostgreSQL
- SQLAlchemy async ORM
- Alembic migrations
- Pydantic v2 schemas
- JWT access tokens
- Database-backed refresh tokens
- `pwdlib[argon2]` password hashing
- pytest

Frontend:

- Vite
- React
- React Router
- Axios
- Tailwind CSS

## Project Structure

```text
app/
  api/
    routes/        Feature route modules
    dependencies.py
    router.py
  core/            Settings, security helpers, exceptions, handlers
  database/        SQLAlchemy base/session and Alembic migrations
  models/          SQLAlchemy ORM models
  repositories/    Database query layer
  schemas/         Pydantic request/response schemas
  services/        Business logic
  ai/              Future RAG/chatbot integration
frontend/
  src/
    api/           Axios API wrappers
    components/    Shared UI components
    contexts/      Auth/session context
    layouts/       Protected app shell
    pages/         Route screens
    styles/        Global styles
tests/
```

Architecture decisions:

- Routes stay thin.
- Services own permission and business rules.
- Repositories own database queries.
- Schemas define API input/output.
- Models map database tables.
- Future RAG work must be class-scoped and permission-aware.

## Environment Settings

Settings use the `CLASSFLOW_` prefix.

Important variables:

```env
CLASSFLOW_PROJECT_NAME=ClassFlow
CLASSFLOW_ENVIRONMENT=local
CLASSFLOW_DEBUG=true
CLASSFLOW_API_V1_PREFIX=/api/v1
CLASSFLOW_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/classflow
CLASSFLOW_SECRET_KEY=change-me-in-local-env
CLASSFLOW_JWT_ALGORITHM=HS256
CLASSFLOW_ACCESS_TOKEN_EXPIRE_MINUTES=30
CLASSFLOW_REFRESH_TOKEN_EXPIRE_DAYS=7
CLASSFLOW_CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
CLASSFLOW_OPENAI_API_KEY=
CLASSFLOW_GEMINI_API_KEY=
CLASSFLOW_VECTOR_STORE_PROVIDER=pgvector
```

Task attachment settings in the backend task module:

```env
CLASSFLOW_TASK_ATTACHMENT_STORAGE_DIR=storage/task_attachments
CLASSFLOW_TASK_ATTACHMENT_MAX_SIZE_BYTES=10485760
```

Never commit real `.env` secrets.

## Database And Migrations

Database schema is managed through Alembic. Do not call `Base.metadata.create_all(...)` in `main.py`.

Useful commands:

```powershell
.\myvenv\Scripts\python.exe -m alembic current
.\myvenv\Scripts\python.exe -m alembic history
.\myvenv\Scripts\python.exe -m alembic revision --autogenerate -m "message"
.\myvenv\Scripts\python.exe -m alembic upgrade head
.\myvenv\Scripts\python.exe -m alembic downgrade -1
```

Current migration sequence:

```text
9646011027a1_module_zero_baseline.py
ac57ddd31bea_create_users_table.py
f29de09fc869_create_refresh_tokens_table.py
85d87d97c121_create_classrooms_and_class_memberships.py
00f7fc38ba77_create_courses_and_course_registrations.py
f2659f4668ac_create_tasks_progress_and_attachments.py
b7428b2d4f91_make_personal_tasks_classroom_optional.py
```

Important task migration note:

- `f2659f4668ac` created `tasks.classroom_id` as `NOT NULL`.
- `b7428b2d4f91` makes `tasks.classroom_id` nullable so independent personal tasks can exist.
- If creating a personal task with no class fails at the database level, run `alembic upgrade head`.

The async DB engine currently uses `NullPool` to avoid event-loop issues during local testing.

## Module 0 - Foundation

Implemented:

- FastAPI application structure
- Environment settings
- PostgreSQL connection
- SQLAlchemy async session management
- Alembic setup
- Standardized exception handlers
- Logging setup
- Health endpoint
- Initial pytest setup

Endpoints:

```text
GET /health
GET /api/v1/health
```

## Module 1 - Authentication

Implemented:

- `users` table
- `refresh_tokens` table
- User registration
- Password hashing
- Login with `OAuth2PasswordRequestForm`
- JWT access tokens
- Refresh token generation, hashing, storage, rotation, and revocation
- Logout through refresh-token revocation
- Protected current-user dependency
- Current-user profile read/update

Endpoints:

```text
POST  /api/v1/auth/register
POST  /api/v1/auth/login
POST  /api/v1/auth/refresh
POST  /api/v1/auth/logout
GET   /api/v1/users/me
PATCH /api/v1/users/me
```

Auth behavior:

- Login returns an access token and refresh token.
- Access token is used with protected endpoints.
- Refresh tokens are stored as SHA-256 hashes.
- Refresh rotates tokens: the old refresh token becomes invalid.
- Logout revokes the refresh token.
- JWT access tokens remain valid until expiry because they are stateless.

## Module 2 - Classrooms And Memberships

Implemented:

- `classrooms` table
- `class_memberships` table
- Classroom creation with unique join codes
- Automatic approved representative membership for classroom creator
- Classroom read/update/list-mine endpoints
- Join requests using join codes
- Membership statuses: `pending`, `approved`, `rejected`, `removed`
- Membership roles: `representative`, `student`
- Representative-only request approval/rejection
- Representative-only member removal
- Protection against removing the class creator
- Reusable membership permission dependencies

Endpoints:

```text
POST   /api/v1/classes
GET    /api/v1/classes/mine
GET    /api/v1/classes/{class_id}
PATCH  /api/v1/classes/{class_id}
POST   /api/v1/classes/{class_id}/join
GET    /api/v1/classes/{class_id}/requests
GET    /api/v1/classes/{class_id}/members
PATCH  /api/v1/memberships/{membership_id}/approve
PATCH  /api/v1/memberships/{membership_id}/reject
DELETE /api/v1/memberships/{membership_id}
```

Core rules:

- Classroom creator becomes an approved representative.
- Pending members cannot access class content.
- Existing approved users cannot create duplicate join requests.
- Pending users cannot duplicate a join request.
- Rejected or removed users may request to join again.
- Only approved representatives can update classrooms, list requests, approve/reject requests, and remove members.

## Module 3 - Courses And Registrations

Implemented:

- `courses` table for global catalogue courses
- `class_courses` table for classroom-specific courses
- `course_registrations` table for student registration
- Catalogue search/list/detail/create endpoints
- Representative-managed class course assignment
- Student registration/drop/re-registration
- Automatic default-course registration when membership is approved
- Automatic registration of existing approved members when a representative adds a default course
- Course code normalization to uppercase
- Duplicate protection for catalogue and class-course records
- Dropped class courses are soft-deactivated. Course-linked tasks are hidden rather than closed.

Endpoints:

```text
GET    /api/v1/courses
GET    /api/v1/courses/{course_id}
POST   /api/v1/courses
POST   /api/v1/classes/{class_id}/courses
GET    /api/v1/classes/{class_id}/courses
PATCH  /api/v1/class-courses/{class_course_id}
DELETE /api/v1/class-courses/{class_course_id}
POST   /api/v1/class-courses/{class_course_id}/register
DELETE /api/v1/class-courses/{class_course_id}/register
GET    /api/v1/classes/{class_id}/my-courses
```

Core rules:

- Only approved representatives can create catalogue courses.
- Only representatives of the same class can add/update/remove class courses.
- Only approved class members can view/register/drop class courses.
- Pending members cannot register for courses.
- Cross-class course registration is blocked.
- When a class course is dropped/deactivated, tasks linked to that class course disappear from task lists, feed queries, summaries, and direct task reads. The task rows are not automatically cancelled or archived.

## Module 4 - Tasks, Progress, And Attachments

Implemented:

- `tasks` table
- `task_progress` table
- `task_attachments` table
- Shared class-wide tasks
- Shared course-specific tasks
- Personal tasks with nullable class/course relationships
- Personal task completion/reopen without deletion
- Per-student progress for shared tasks
- Attachment upload/list/download/delete
- File extension, content type, size, and storage-key validation
- Permission checks before attachment download

Task model:

```text
Task
- id
- classroom_id nullable
- class_course_id nullable
- created_by_user_id
- title
- description
- task_type
- visibility shared | personal
- priority
- status
- deadline
- completed_at
- created_at
- updated_at
```

Valid task relationship combinations:

```text
shared   + classroom required + class_course optional
personal + classroom optional + class_course optional
```

If `class_course_id` is present, `classroom_id` must also be present and must match the `ClassCourse.classroom_id`.

Endpoints:

```text
POST   /api/v1/classes/{class_id}/tasks
POST   /api/v1/personal-tasks
GET    /api/v1/classes/{class_id}/tasks
GET    /api/v1/tasks
GET    /api/v1/tasks/{task_id}
PATCH  /api/v1/tasks/{task_id}
DELETE /api/v1/tasks/{task_id}
PUT    /api/v1/tasks/{task_id}/progress
PUT    /api/v1/personal-tasks/{task_id}/complete
PUT    /api/v1/personal-tasks/{task_id}/reopen
POST   /api/v1/tasks/{task_id}/attachments
GET    /api/v1/tasks/{task_id}/attachments
GET    /api/v1/attachments/{attachment_id}/download
DELETE /api/v1/attachments/{attachment_id}
```

Shared task rules:

- Shared tasks require a classroom.
- Shared tasks can only be created by approved representatives.
- Shared course tasks require an active class course in the same classroom.
- Shared tasks use `TaskProgress` for each student's completion.
- Shared tasks can be cancelled or archived, but not hard-deleted.
- Shared tasks cannot be globally marked completed.
- Cancelled or archived shared tasks cannot receive progress updates.

Personal task rules:

- Any authenticated user can create a personal task.
- Personal tasks are visible only to their creator.
- Personal tasks may be independent, class-linked, or course-linked.
- Class-linked personal tasks require approved membership in that class.
- Course-linked personal tasks require active registration in that class course.
- Personal tasks use their own `status` and `completed_at`, not `TaskProgress`.
- Personal tasks are not deleted on completion.
- Personal tasks can be reopened.
- Only the owner can delete a personal task.
- Course-linked personal tasks disappear when their class course is dropped/deactivated.

Attachment rules:

- Attachments require task-management permission to upload/delete.
- Downloads require task-view permission.
- Invalid file extensions are rejected.
- Invalid content types are rejected.
- Oversized files are rejected.
- Storage keys cannot escape the attachment storage directory.

## Module 5 - Personal Feed, Filtering, And Search

Implemented backend:

- Global feed endpoint combining personal tasks and accessible shared tasks
- Summary counts
- Filter options
- Authorization-aware repository queries
- Search after authorization filtering
- Timezone-aware due grouping
- Pagination
- Per-item permissions for frontend actions
- Inactive class-course tasks are hidden rather than closed.

Endpoints:

```text
GET /api/v1/feed
GET /api/v1/feed/summary
GET /api/v1/feed/filter-options
```

`GET /api/v1/feed` query parameters:

```text
view=active|completed|archived|all
visibility=all|personal|shared
classroom_id optional
class_course_id optional
task_type optional
priority optional
due=overdue|today|week|later|no_deadline optional
search optional, max 100 chars
timezone optional, default UTC
page default 1
page_size default 20, max 100
```

Feed visibility rules:

- Personal tasks are visible only to their creator.
- Shared class-wide tasks are visible to approved members of the classroom.
- Shared course-specific tasks are visible only to actively registered students for that class course.
- Representatives do not automatically see every course-specific shared task in the feed unless they are registered in the course.
- Course-specific tasks are returned only while the linked class course is active.

Feed response behavior:

- Personal completed tasks derive completion from `Task.status` and `Task.completed_at`.
- Shared completed tasks derive completion from the current user's `TaskProgress`.
- Each item includes context type: `independent`, `class`, or `course`.
- Each item includes classroom/course context when available.
- Each item includes permissions: `can_edit`, `can_delete`, `can_manage`, `can_update_progress`.
- Due groups are computed using the caller's timezone.

Search behavior:

- Search is trimmed.
- Empty search is ignored.
- Terms longer than 100 characters are rejected.
- Search runs against task title, task description, classroom name, course name, and course code.
- Search is applied after authorization constraints in the SQL query.

## Frontend State

Implemented frontend screens include:

```text
/register
/login
/dashboard
/classes
/classes/new
/classes/join
/classes/:classId
/classes/:classId/courses
/classes/:classId/my-courses
/classes/:classId/tasks
/tasks
/tasks/:taskId
/feed
/profile
/courses
```

Frontend API helpers currently cover:

- auth
- classrooms
- memberships
- courses
- tasks
- feed

Frontend should continue to consume backend permission flags instead of duplicating backend authorization logic.

## Testing

Backend tests:

```powershell
.\myvenv\Scripts\python.exe -m pytest
```

Focused task/feed tests:

```powershell
.\myvenv\Scripts\python.exe -m pytest tests\test_tasks_and_attachments.py tests\test_feed.py tests\test_health.py
```

Current backend coverage includes:

- Health endpoints
- Task guardrails
- Personal task visibility and completion retention
- Shared task progress upsert
- Cancelled-task progress rejection
- Attachment validation and permission checks
- Feed item shaping
- Feed search validation
- Feed filter authorization
- Feed summary/filter option mapping
- Due group classification

Frontend checks:

```powershell
cd frontend
npm run build
```

## Current Branch Notes

Recent module branches:

```text
feature/tasks-attachments
feature/personal-feed
frontend-foundation
```

The task/attachment backend has been merged through PR #5. The feed backend lives on `feature/personal-feed` and should be opened against `main` after fetching the latest remote state.

If GitHub does not show the compare banner, open:

```text
https://github.com/Abrehmant7/ClassFlow/compare/main...feature/personal-feed?expand=1
```

## Next Backend Work

Likely next backend modules:

- Announcements
- Resources
- Notifications
- Dashboard aggregation
- RAG ingestion and class-scoped retrieval
- Chatbot endpoints

RAG safety rule:

- Personal tasks must never enter the shared RAG vector store.
- Shared resources/tasks should only be indexed with class/course permission metadata.
