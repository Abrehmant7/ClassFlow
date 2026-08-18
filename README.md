# ClassFlow

ClassFlow is an academic coordination app with a FastAPI/PostgreSQL backend and a React frontend. It supports authentication, classrooms, memberships, course registration, tasks, attachments, and a personal academic feed. Future modules will add announcements, resources, notifications, dashboards, and class-scoped RAG chat.

## Current Capabilities

Backend:

- JWT authentication with refresh-token rotation
- User profile read/update
- Classroom creation, join requests, approvals, and member management
- Global course catalogue
- Class-specific course assignment
- Student course registration, drop, and re-registration
- Shared classroom/course tasks
- Personal academic tasks with optional class/course context
- Per-student task progress for shared tasks
- Task attachments with file validation and permission checks
- Personal feed with summary counts, filtering, pagination, due grouping, and search

Frontend:

- Vite React app
- Authentication screens
- Protected app layout
- Dashboard shell
- Classroom list/create/join/detail screens
- Course catalogue and class course management screens
- Student course registration screens
- Task list/detail screens
- Personal feed screen
- Shared UI components for forms, alerts, loading states, status badges, tabs, modals, and task rows

## Local Setup

Use the existing virtual environment:

```powershell
.\myvenv\Scripts\activate
pip install -r requirements.txt
```

Create a local `.env` from `.env.example` and set your local database URL and secret key. App settings use the `CLASSFLOW_` prefix.

Apply database migrations:

```powershell
.\myvenv\Scripts\python.exe -m alembic upgrade head
```

Run the backend:

```powershell
.\myvenv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Run the frontend:

```powershell
cd frontend
npm install
npm run dev
```

Health checks:

```text
GET /health
GET /api/v1/health
```

## Project Structure

```text
app/
  api/            FastAPI routers and dependencies
  core/           configuration, security helpers, exceptions
  database/       SQLAlchemy session/base and Alembic migrations
  models/         SQLAlchemy ORM models
  schemas/        Pydantic request/response schemas
  repositories/   database access layer
  services/       business rules and orchestration
  ai/             future RAG ingestion, embeddings, retrieval, and chat
frontend/
  src/
    api/          Axios API helpers
    components/   shared UI components
    contexts/     auth/session state
    layouts/      app layout
    pages/        route screens
    styles/       global CSS
tests/            pytest tests
docs/             project knowledge base
```

## Key Backend Endpoints

Authentication and users:

```text
POST  /api/v1/auth/register
POST  /api/v1/auth/login
POST  /api/v1/auth/refresh
POST  /api/v1/auth/logout
GET   /api/v1/users/me
PATCH /api/v1/users/me
```

Classrooms and memberships:

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

Courses:

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

Tasks and attachments:

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
GET    /api/v1/task-attachments/{attachment_id}/download
DELETE /api/v1/task-attachments/{attachment_id}
```

Feed:

```text
GET /api/v1/feed
GET /api/v1/feed/summary
GET /api/v1/feed/filter-options
```

## Database Notes

Database schema is managed through Alembic. Do not use `Base.metadata.create_all(...)` in application startup.

Important migration commands:

```powershell
.\myvenv\Scripts\python.exe -m alembic current
.\myvenv\Scripts\python.exe -m alembic upgrade head
```

Personal tasks require the latest task migration because `tasks.classroom_id` must be nullable for independent personal tasks.

## Testing

Run all backend tests:

```powershell
.\myvenv\Scripts\python.exe -m pytest
```

Focused task/feed tests:

```powershell
.\myvenv\Scripts\python.exe -m pytest tests\test_tasks_and_attachments.py tests\test_feed.py tests\test_health.py
```

Frontend build:

```powershell
cd frontend
npm run build
```
