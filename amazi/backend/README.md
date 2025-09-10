Amazi Backend (FastAPI)
=======================

Quickstart
----------

1. Copy .env.example to .env and adjust if needed.
2. Start Postgres:

```bash
docker compose up -d db
```

3. Create a virtualenv and install dependencies:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
```

4. Run the API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Migrations
----------

Generate (if models change):

```bash
alembic -c alembic.ini revision --autogenerate -m "change"
```

Apply:

```bash
alembic -c alembic.ini upgrade head
```

Endpoints
---------

- GET `/api/health`
- POST `/api/uploads/timesheet` (multipart `file`) — 5MB limit; returns extraction preview
- POST `/api/uploads/{id}/confirm` — placeholder for now

Extraction
----------
The pipeline prefers deterministic parsing for CSV/XLSX, light PDF parsing, and returns a preview with evidence/needs_review fields. Images return a needs_review item until OCR is added.

