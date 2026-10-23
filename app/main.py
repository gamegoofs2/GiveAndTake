import os
import secrets
import shutil
import uuid
from pathlib import Path

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .db import DB_PATH, get_conn, init_db

BASE = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(BASE / "templates"))

UPLOADS_DIR = os.getenv("UPLOADS_DIR", "uploads")
UPLOADS = Path(UPLOADS_DIR)
UPLOADS.mkdir(parents=True, exist_ok=True)

ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme")

security = HTTPBasic()


def require_admin(creds: HTTPBasicCredentials = Depends(security)):
    if not (
        secrets.compare_digest(creds.username, ADMIN_USER)
        and secrets.compare_digest(creds.password, ADMIN_PASSWORD)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )
    return creds.username


app = FastAPI(title="Give & Take")
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")
app.mount("/uploads", StaticFiles(directory=str(UPLOADS.resolve())), name="uploads")


@app.on_event("startup")
def on_startup():
    init_db()


def fetch_items(status_filter=None):
    conn = get_conn()
    if status_filter:
        rows = conn.execute(
            "SELECT * FROM items WHERE status=? ORDER BY created_at DESC", (status_filter,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM items ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def fetch_item(item_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


@app.get("/favicon.ico")
def favicon():
    return RedirectResponse(url="/static/favicon.png", status_code=301)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    items = fetch_items()
    return TEMPLATES.TemplateResponse(
        request, "index.html", {"items": items}
    )


@app.get("/items/{item_id}", response_class=HTMLResponse)
def item_detail(request: Request, item_id: int):
    item = fetch_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return TEMPLATES.TemplateResponse(
        request, "item.html", {"item": item}
    )


@app.post("/items/{item_id}/claim")
def claim_item(
    request: Request,
    item_id: int,
    name: str = Form(""),
    email: str = Form(""),
):
    item = fetch_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if item["status"] != "available":
        return RedirectResponse(url=f"/items/{item_id}?msg=already_claimed", status_code=303)
    name = name.strip()
    email = email.strip()
    if not name:
        return RedirectResponse(url=f"/items/{item_id}?msg=bad_name", status_code=303)
    if not email or "@" not in email:
        return RedirectResponse(url=f"/items/{item_id}?msg=bad_email", status_code=303)
    conn = get_conn()
    conn.execute(
        "INSERT INTO orders (item_id, buyer_name, buyer_email) VALUES (?, ?, ?)",
        (item_id, name, email),
    )
    conn.execute("UPDATE items SET status='claimed' WHERE id=? AND status='available'", (item_id,))
    conn.commit()
    conn.close()
    return RedirectResponse(url=f"/items/{item_id}?msg=claimed", status_code=303)


# ---------- Admin ----------

@app.get("/admin", response_class=HTMLResponse)
def admin(request: Request, user: str = Depends(require_admin)):
    items = fetch_items()
    return TEMPLATES.TemplateResponse(
        request, "admin.html", {"items": items, "user": user}
    )


@app.post("/admin/items")
async def admin_create_item(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    price: float = Form(0.0),
    condition: str = Form(""),
    category: str = Form(""),
    image_url: str = Form(""),
    image: UploadFile = File(None),
    user: str = Depends(require_admin),
):
    image_path = image_url.strip()
    if image is not None and image.filename:
        ext = Path(image.filename).suffix
        fname = f"{uuid.uuid4().hex}{ext}"
        dest = UPLOADS / fname
        with dest.open("wb") as f:
            shutil.copyfileobj(image.file, f)
        image_path = f"/uploads/{fname}"
    conn = get_conn()
    conn.execute(
        """INSERT INTO items (title, description, price, condition, category, image)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (title.strip(), description.strip(), price, condition.strip(), category.strip(), image_path),
    )
    conn.commit()
    conn.close()
    return RedirectResponse(url="/admin", status_code=303)


@app.post("/admin/items/{item_id}/delete")
def admin_delete_item(item_id: int, user: str = Depends(require_admin)):
    conn = get_conn()
    conn.execute("DELETE FROM items WHERE id=?", (item_id,))
    conn.execute("DELETE FROM orders WHERE item_id=?", (item_id,))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/admin", status_code=303)


@app.post("/admin/items/{item_id}/status")
def admin_set_status(item_id: int, status_val: str = Form(...), user: str = Depends(require_admin)):
    if status_val not in ("available", "claimed", "sold"):
        raise HTTPException(status_code=400, detail="bad status")
    conn = get_conn()
    conn.execute("UPDATE items SET status=? WHERE id=?", (status_val, item_id))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/admin", status_code=303)


@app.get("/admin/orders", response_class=HTMLResponse)
def admin_orders(request: Request, user: str = Depends(require_admin)):
    conn = get_conn()
    rows = conn.execute(
        """SELECT o.id, o.buyer_name, o.buyer_email, o.created_at, i.title, i.id AS item_id
           FROM orders o JOIN items i ON i.id=o.item_id
           ORDER BY o.created_at DESC"""
    ).fetchall()
    conn.close()
    orders = [dict(r) for r in rows]
    return TEMPLATES.TemplateResponse(
        request, "orders.html", {"orders": orders, "user": user}
    )
