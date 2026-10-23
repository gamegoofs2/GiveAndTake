# AGENTS.md

## What this is
FastAPI + SQLite + Jinja2 site for listing items to give away/sell in person. Buyers claim items with an email only; no payments. Admin manages items via HTTP Basic Auth.

## Run
- Local: `pip install -r requirements.txt` then `uvicorn app.main:app --reload` (http://localhost:8000)
- Docker: `docker compose up --build`
- Admin: `/admin`, default creds `admin` / `changeme` (override `ADMIN_USER`/`ADMIN_PASSWORD`)

## Structure
- `app/main.py` — routes (public browse/claim, admin CRUD, orders)
- `app/db.py` — SQLite init + `DB_PATH` (default `data.db`)
- `app/templates/` — Jinja2 templates; `app/static/style.css`
- Uploads served from `UPLOADS_DIR` (default `uploads/`) at `/uploads`

## Conventions / gotchas
- TemplateResponse uses new Starlette signature: `TEMPLATES.TemplateResponse(request, "name.html", {ctx})`. Do not use the old `("name.html", {"request": request})` form — breaks on Starlette 1.6.
- `request` is auto-injected into template context by Starlette.
- DB and uploads paths are env-driven (`DB_PATH`, `UPLOADS_DIR`); in Docker both live under `/data` with a volume.
- Item status flow: `available` -> `claimed` (via buyer email) -> `sold` (admin). Claim is idempotent-guarded: only `available` items can be claimed.
- Admin auth is HTTP Basic Auth; credentials compared with `secrets.compare_digest`.
- Python 3.12 in Docker, but dev machine may run 3.14; keep code compatible (no 3.12-only features needed).
- No tests exist yet; verify manually via browser or a quick smoke script against a running instance.