# Give & Take

A quick ecommerce site for giving away or selling items in person. Buyers only enter an email at checkout; all transactions happen in person.

## Run locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://localhost:8000. Admin at http://localhost:8000/admin (default user `admin`, password `changeme` — set `ADMIN_PASSWORD`).

## Run with Docker

```bash
docker compose up --build
```

## Environment variables

- `ADMIN_USER` / `ADMIN_PASSWORD` — admin credentials (HTTP Basic Auth)
- `DB_PATH` — SQLite file path (default `data.db`)
- `UPLOADS_DIR` — uploaded images directory (default `uploads`)