Amazi — AI-native Scheduling (Early Prototype)
==============================================

This repo contains a FastAPI backend and a React (Vite) frontend to upload past timesheets and preview extracted employees and shifts. Extraction is deterministic-first; LLMs are not required.

Quickstart
----------

1. Copy environment files

```bash
cp .env.example .env
cp frontend/.env.example frontend/.env
```

2. Start Postgres

```bash
docker compose up -d db
```

3. Backend

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --app-dir backend
```

4. Frontend

```bash
cd frontend
npm install
npm run dev
```

Visit http://localhost:5173 and upload a sample CSV/XLSX/PDF (≤ 5 MB).

Notes
-----
- Images currently return a review request; OCR will be added later.
- The API returns evidence and confidence for each field and never fabricates data; missing values are surfaced in the UI for manual confirmation.

