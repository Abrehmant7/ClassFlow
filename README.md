# ClassFlow

FastAPI backend for an AI-powered academic coordination platform.

## Local Setup

Use the existing virtual environment:

```powershell
.\myvenv\Scripts\activate
pip install -r requirements.txt
```

Create a local `.env` from `.env.example` when you are ready to use custom settings. App settings use the `CLASSFLOW_` prefix to avoid conflicts with global environment variables.

Run the API:

```powershell
uvicorn app.main:app --reload
```

Health check:

```text
GET /health
GET /api/v1/health
```

## Current Structure

```text
app/
  api/          FastAPI routers grouped by product feature
  core/         configuration, security helpers, exceptions
  database/     SQLAlchemy session/base and future Alembic migrations
  models/       SQLAlchemy ORM models
  schemas/      Pydantic request/response schemas
  repositories/ database access layer
  services/     business rules and orchestration
  ai/           future RAG ingestion, embeddings, retrieval, and chat
tests/          pytest tests
```

PostgreSQL connection details and Alembic migrations are staged but not fully wired into models yet; we can add that together when we design the first tables.
