# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**EZZAOUIA/MARETAP Platform** — an on-premise Django enterprise application for oil production data management, analytics, and AI-powered document Q&A. Deployed on Windows servers with Microsoft SQL Server, no containerization.

## Development Commands

### Environment Setup

```bash
# Create and activate virtual environment (Windows)
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements/base.txt      # production
pip install -r requirements/dev.txt       # development tools

# Configure environment
cp .env.example .env  # then edit with actual values
```

### Running the Application

```bash
# Django dev server
python manage.py runserver

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic
```

### Celery (Async Tasks)

```bash
# Windows requires --pool=solo
celery -A config worker --loglevel=info --pool=solo

# Check task results
python manage.py shell -c "from django_celery_results.models import TaskResult; print(TaskResult.objects.all())"
```

### Code Quality

```bash
black .                        # format code
flake8 .                       # lint
```

### Testing

```bash
pytest                         # run all tests
pytest apps/chatbot/           # run tests for a specific app
pytest -k "test_name"          # run a single test by name
pytest --cov=apps --cov-report=term-missing  # with coverage
```

Note: Pytest infrastructure is installed but no tests exist yet. `pytest-django` is configured; a `conftest.py` with `DJANGO_SETTINGS_MODULE=config.settings` will be needed when writing tests.

## Architecture

### Key Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 4.2 |
| Database | MS SQL Server via `mssql-django` + `pyodbc` (ODBC Driver 17) |
| Async | Celery 5.4 + Redis (Memurai on Windows) |
| REST API | Django REST Framework — consumed by Power BI DirectQuery |
| AI/LLM | Ollama (local, `llama3` model) via LangChain |
| Embeddings | SentenceTransformer `all-MiniLM-L6-v2` (CPU, no GPU needed) |
| Vector DB | ChromaDB (local persistence at `./chroma_db/`) |
| Auth/RBAC | Django auth + `django-guardian` (object-level permissions) |

### Application Structure (`apps/`)

- **`accounts/`** — Custom `User` model (extends `AbstractUser`) with three roles: `ADMIN`, `INGENIEUR`, `DIRECTION`. Includes role-based decorators used across views.
- **`core/`** — `BaseModel` abstract model providing `created_at`/`updated_at` to all domain models.
- **`warehouse/`** — Read-only Django models (`managed=False`) mapped to existing SQL Server DWH tables: dimension tables (`DimDate`, `DimWell`, `DimPowerType`, etc.) and fact tables (`FactDailyProduction`, `FactWellTest`, `FactTankLevel`). Never run migrations against these.
- **`kpis/`** — DRF REST API aggregating over warehouse fact tables for Power BI. Calculators in `calculators.py`; 6 endpoints under `/api/kpis/`.
- **`ingestion/`** — File upload pipeline: `UploadedFile` model tracks status (`pending → processing → success/error`). Celery task `process_uploaded_file()` parses PDF/DOCX/XLSX, then indexes content into ChromaDB for RAG.
- **`chatbot/`** — RAG chatbot. `ChatSession`/`ChatMessage` models. `rag_pipeline.py` orchestrates Ollama LLM + ChromaDB retrieval. Collections are isolated per document (`doc_id`).
- **`dashboard/`** — Entry point after login; shows recent uploads.

### Data Flow

```
File Upload → ingestion app → Celery task → parse (PDF/DOCX/XLSX)
    → embed (SentenceTransformer) → store in ChromaDB (per doc_id)
    → chatbot RAG query → Ollama llama3 → response
```

### URL Structure

```
/admin/              Django admin (warehouse models are read-only)
/accounts/           Login / logout / profile
/dashboard/          Main dashboard
/ingestion/          File upload & processing status
/chatbot/            RAG chat interface
/api/kpis/           REST API for Power BI
/api/warehouse/      Warehouse data APIs
```

### Environment Variables (`.env`)

Critical variables to configure:
- `DB_SERVER`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_TRUSTED_CONNECTION` — SQL Server connection
- `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` — Redis (default: `redis://127.0.0.1:6379/0`)
- `OLLAMA_BASE_URL`, `OLLAMA_MODEL` — Local LLM (default: `http://127.0.0.1:11434`, `llama3`)
- `CHROMA_PERSIST_DIR` — Vector store path (default: `./chroma_db`)

### Important Constraints

- **`warehouse/` models use `managed=False`** — they map to pre-existing DWH tables. Never create/run migrations for these models.
- **Celery on Windows must use `--pool=solo`** — thread-based pools are unsupported.
- **ChromaDB collections are per-document** — keyed by `doc_id`; deleting a file should also delete its ChromaDB collection.
- **Language/locale:** Django is configured for French (`LANGUAGE_CODE = 'fr-fr'`, `TIME_ZONE = 'Africa/Tunis'`).
- **Max file upload size:** 50MB; accepted formats: PDF, DOCX, XLSX.
