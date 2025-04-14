import os
import sqlite3
from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.status import HTTP_303_SEE_OTHER
from ai_companion.settings import settings

# For long-term memory vector store
from ai_companion.modules.memory.long_term.vector_store import get_vector_store

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
SHORT_TERM_DB = settings.SHORT_TERM_MEMORY_DB_PATH
BLOCKLIST_DB = "admin_blocklist.db"

admin_router = APIRouter()

def check_auth(request: Request):
    password = request.cookies.get("admin_password")
    if password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Unauthorized")

def init_blocklist_db():
    conn = sqlite3.connect(BLOCKLIST_DB)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS blocked_users (
            telegram_id TEXT PRIMARY KEY,
            blocked_at TEXT
        )
        """
    )
    conn.commit()
    conn.close()

init_blocklist_db()

@admin_router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    # Auth check
    password = request.cookies.get("admin_password")
    if password != ADMIN_PASSWORD:
        return HTMLResponse(
            """
            <h2>Admin Login</h2>
            <form method="post" action="/admin/login">
                <input type="password" name="password" placeholder="Password"/>
                <button type="submit">Login</button>
            </form>
            """, status_code=200
        )
    # Get blocked users
    conn = sqlite3.connect(BLOCKLIST_DB)
    c = conn.cursor()
    c.execute("SELECT telegram_id, blocked_at FROM blocked_users")
    blocked = c.fetchall()
    conn.close()
    # Render dashboard
    html = """
    <h2>Admin Dashboard</h2>
    <form method="post" action="/admin/block_user">
        <input type="text" name="telegram_id" placeholder="Telegram ID to block" required/>
        <button type="submit">Block User</button>
    </form>
    <form method="post" action="/admin/unblock_user">
        <input type="text" name="telegram_id" placeholder="Telegram ID to unblock" required/>
        <button type="submit">Unblock User</button>
    </form>
    <h3>Blocked Users</h3>
    <table border="1">
        <tr><th>Telegram ID</th><th>Blocked At</th></tr>
    """
    for tid, blocked_at in blocked:
        html += f"<tr><td>{tid}</td><td>{blocked_at}</td></tr>"
    html += "</table><br>"
    html += """
    <form method="post" action="/admin/clear_short_term_memory" onsubmit="return confirm('Clear short-term memory?');">
        <button type="submit">Clear Short-Term Memory</button>
    </form>
    <form method="post" action="/admin/clear_long_term_memory" onsubmit="return confirm('Clear long-term memory?');">
        <button type="submit">Clear Long-Term Memory</button>
    </form>
    <form method="post" action="/admin/clear_reminders" onsubmit="return confirm('Clear ALL reminders?');">
        <button type="submit">Clear All Reminders</button>
    </form>
    """
    return HTMLResponse(html)

@admin_router.post("/admin/login")
async def admin_login(request: Request, password: str = Form(...)):
    if password == ADMIN_PASSWORD:
        response = RedirectResponse(url="/admin", status_code=HTTP_303_SEE_OTHER)
        response.set_cookie("admin_password", password, httponly=True)
        return response
    return HTMLResponse("<h2>Invalid password</h2><a href='/admin'>Try again</a>", status_code=401)

@admin_router.post("/admin/block_user")
async def block_user(request: Request, telegram_id: str = Form(...)):
    check_auth(request)
    from datetime import datetime
    conn = sqlite3.connect(BLOCKLIST_DB)
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO blocked_users (telegram_id, blocked_at) VALUES (?, ?)",
        (telegram_id, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    return RedirectResponse(url="/admin", status_code=HTTP_303_SEE_OTHER)

@admin_router.post("/admin/unblock_user")
async def unblock_user(request: Request, telegram_id: str = Form(...)):
    check_auth(request)
    conn = sqlite3.connect(BLOCKLIST_DB)
    c = conn.cursor()
    c.execute("DELETE FROM blocked_users WHERE telegram_id = ?", (telegram_id,))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/admin", status_code=HTTP_303_SEE_OTHER)

@admin_router.post("/admin/clear_short_term_memory")
async def clear_short_term_memory(request: Request):
    check_auth(request)
    conn = sqlite3.connect(SHORT_TERM_DB)
    c = conn.cursor()
    # List all tables and delete from each
    c.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in c.fetchall()]
    for table in tables:
        c.execute(f"DELETE FROM {table}")
    conn.commit()
    conn.close()
    return RedirectResponse(url="/admin", status_code=HTTP_303_SEE_OTHER)

@admin_router.post("/admin/clear_long_term_memory")
async def clear_long_term_memory(request: Request):
    check_auth(request)
    vector_store = get_vector_store()
    # Assuming the vector store has a method to delete all from the collection
    try:
        vector_store.delete_collection("long_term_memory")
    except Exception:
        pass
    return RedirectResponse(url="/admin", status_code=HTTP_303_SEE_OTHER)

@admin_router.post("/admin/clear_reminders")
async def clear_reminders(request: Request):
    check_auth(request)
    REMINDERS_DB = "reminders.db"
    conn = sqlite3.connect(REMINDERS_DB)
    c = conn.cursor()
    c.execute("DELETE FROM reminders")
    conn.commit()
    conn.close()
    return RedirectResponse(url="/admin", status_code=HTTP_303_SEE_OTHER)
