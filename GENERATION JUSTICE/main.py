from datetime import datetime
from html import escape
from pathlib import Path
import hashlib
import secrets
import sqlite3

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "generation_justice.db"
SESSION_COOKIE = "gj_session"

app = FastAPI(
    title="Generation Justice",
    description="Membership site with login, join, comments, and broadcasts.",
    version="2.0.0",
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
TEMPLATES_DIR = BASE_DIR / "templates"


class LoginPayload(BaseModel):
    email: str
    password: str


class JoinPayload(BaseModel):
    name: str
    email: str
    password: str
    membership: str


class CommentPayload(BaseModel):
    name: str = ""
    text: str


class BroadcastPayload(BaseModel):
    title: str
    target: str
    message: str


def connect_db() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def now_label() -> str:
    return datetime.now().strftime("%b %d, %Y at %H:%M")


def clean(value: str, limit: int = 500) -> str:
    return value.strip()[:limit]


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def row_to_dict(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row else None


def read_template(name: str) -> str:
    return (TEMPLATES_DIR / name).read_text(encoding="utf-8")


def init_db() -> None:
    connection = connect_db()
    try:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                membership TEXT NOT NULL,
                joined_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT NOT NULL,
                text TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS broadcasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                target TEXT NOT NULL,
                message TEXT NOT NULL,
                created_by TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )

        user_count = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if user_count == 0:
            connection.execute(
                """
                INSERT INTO users (name, email, password_hash, membership, joined_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    "Demo Student",
                    "demo@generationjustice.org",
                    hash_password("demo123"),
                    "Member",
                    now_label(),
                ),
            )

        comment_count = connection.execute("SELECT COUNT(*) FROM comments").fetchone()[0]
        if comment_count == 0:
            connection.executemany(
                """
                INSERT INTO comments (user_name, text, created_at)
                VALUES (?, ?, ?)
                """,
                [
                    (
                        "Alex Rivera",
                        "The leadership workshop helped me feel ready to speak during our school assembly.",
                        "Apr 20, 2026 at 16:10",
                    ),
                    (
                        "Priya Shah",
                        "I want to organize a student panel about safety, belonging, and mental health.",
                        "Apr 21, 2026 at 11:35",
                    ),
                    (
                        "Marcus Lee",
                        "The broadcast center makes it easier for our club to share campaign updates.",
                        "Apr 22, 2026 at 09:20",
                    ),
                ],
            )

        broadcast_count = connection.execute("SELECT COUNT(*) FROM broadcasts").fetchone()[0]
        if broadcast_count == 0:
            connection.execute(
                """
                INSERT INTO broadcasts (title, target, message, created_by, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "Welcome Members",
                    "All pages",
                    "Join this week's student action meeting and bring one idea for a new campaign.",
                    "Demo Student",
                    "running",
                    "Apr 23, 2026 at 13:00",
                ),
            )

        connection.commit()
    finally:
        connection.close()


@app.on_event("startup")
def startup() -> None:
    init_db()


def get_user_by_session(request: Request) -> dict | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None

    connection = connect_db()
    try:
        user = connection.execute(
            """
            SELECT users.id, users.name, users.email, users.membership, users.joined_at
            FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token = ?
            """,
            (token,),
        ).fetchone()
        return row_to_dict(user)
    finally:
        connection.close()


def create_session_response(user: dict, message: str) -> JSONResponse:
    token = secrets.token_urlsafe(32)
    connection = connect_db()
    try:
        connection.execute("DELETE FROM sessions WHERE user_id = ?", (user["id"],))
        connection.execute(
            "INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
            (token, user["id"], now_label()),
        )
        connection.commit()
    finally:
        connection.close()

    response = JSONResponse({"ok": True, "message": message, "user": user})
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
    )
    return response


def get_comments() -> list[dict]:
    connection = connect_db()
    try:
        rows = connection.execute(
            "SELECT id, user_name, text, created_at FROM comments ORDER BY id DESC LIMIT 30"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def get_recent_broadcasts() -> list[dict]:
    connection = connect_db()
    try:
        rows = connection.execute(
            """
            SELECT id, title, target, message, created_by, status, created_at
            FROM broadcasts
            ORDER BY id DESC
            LIMIT 8
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def get_latest_broadcast() -> dict | None:
    connection = connect_db()
    try:
        row = connection.execute(
            """
            SELECT id, title, target, message, created_by, status, created_at
            FROM broadcasts
            WHERE status = 'running'
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
        return row_to_dict(row)
    finally:
        connection.close()


def active_class(current: str, expected: str) -> str:
    return "active" if current == expected else ""


def render_latest_broadcast(broadcast: dict | None) -> str:
    if not broadcast:
        return ""
    return f"""
        <section class="broadcast-strip" id="liveBroadcastBanner">
            <strong>{escape(broadcast["title"])}</strong>
            <span>{escape(broadcast["message"])}</span>
            <small>{escape(broadcast["target"])} - by {escape(broadcast["created_by"])}</small>
        </section>
    """


def render_comments(comments: list[dict]) -> str:
    return "\n".join(
        f"""
        <article class="comment">
            <strong>{escape(comment["user_name"])}</strong>
            <small>{escape(comment["created_at"])}</small>
            <p>{escape(comment["text"])}</p>
        </article>
        """
        for comment in comments
    )


def render_broadcasts(broadcasts: list[dict]) -> str:
    return "\n".join(
        f"""
        <article class="broadcast-item">
            <strong>{escape(broadcast["title"])}</strong>
            <span>{escape(broadcast["message"])}</span>
            <small>{escape(broadcast["target"])} - {escape(broadcast["status"])} - {escape(broadcast["created_at"])} - by {escape(broadcast["created_by"])}</small>
        </article>
        """
        for broadcast in broadcasts
    )


def render_page(request: Request, template_name: str, active_page: str, title: str, **context):
    user = get_user_by_session(request)
    content = read_template(template_name)

    replacements = {
        "__COMMENT_NAME__": escape(user["name"]) if user else "",
        "__COMMENTS__": render_comments(context.get("comments", [])),
        "__BROADCASTS__": render_broadcasts(context.get("broadcasts", [])),
    }
    for placeholder, value in replacements.items():
        content = content.replace(placeholder, value)

    base = read_template("base.html")
    chip_text = f"{escape(user['membership'])} Member" if user else ""
    chip_class = "member-chip show" if user else "member-chip"
    login_hidden = "hidden" if user else ""
    logout_hidden = "" if user else "hidden"
    base_replacements = {
        "__TITLE__": escape(title),
        "__ACTIVE_HOME__": active_class(active_page, "home"),
        "__ACTIVE_ABOUT__": active_class(active_page, "about"),
        "__ACTIVE_WORK__": active_class(active_page, "work"),
        "__ACTIVE_MEMBERSHIP__": active_class(active_page, "membership"),
        "__ACTIVE_COMMENTS__": active_class(active_page, "comments"),
        "__ACTIVE_BROADCAST__": active_class(active_page, "broadcast"),
        "__LOGIN_HIDDEN__": login_hidden,
        "__LOGOUT_HIDDEN__": logout_hidden,
        "__MEMBER_CHIP_CLASS__": chip_class,
        "__MEMBER_CHIP_TEXT__": chip_text,
        "__BROADCAST_BANNER__": render_latest_broadcast(get_latest_broadcast()),
        "__CONTENT__": content,
    }
    for placeholder, value in base_replacements.items():
        base = base.replace(placeholder, value)

    return HTMLResponse(base)


@app.get("/")
def home(request: Request):
    return render_page(request, "index.html", "home", "Generation Justice | Home")


@app.get("/about")
def about(request: Request):
    return render_page(request, "about.html", "about", "Generation Justice | Who We Are")


@app.get("/what-we-do")
def what_we_do(request: Request):
    return render_page(request, "what_we_do.html", "work", "Generation Justice | What We Do")


@app.get("/membership")
def membership(request: Request):
    return render_page(request, "membership.html", "membership", "Generation Justice | Membership")


@app.get("/comments")
def comments(request: Request):
    return render_page(
        request,
        "comments.html",
        "comments",
        "Generation Justice | Comments",
        comments=get_comments(),
    )


@app.get("/broadcast")
def broadcast(request: Request):
    return render_page(
        request,
        "broadcast.html",
        "broadcast",
        "Generation Justice | Broadcast",
        broadcasts=get_recent_broadcasts(),
    )


@app.get("/api/me")
def current_user(request: Request):
    return {"user": get_user_by_session(request)}


@app.post("/api/login")
def login(payload: LoginPayload):
    email = clean(payload.email.lower(), 160)
    password = payload.password
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required.")

    connection = connect_db()
    try:
        user_row = connection.execute(
            """
            SELECT id, name, email, membership, joined_at, password_hash
            FROM users
            WHERE email = ?
            """,
            (email,),
        ).fetchone()
        if not user_row or user_row["password_hash"] != hash_password(password):
            raise HTTPException(status_code=401, detail="Incorrect email or password.")

        user = dict(user_row)
        user.pop("password_hash")
    finally:
        connection.close()

    return create_session_response(user, "You are logged in.")


@app.post("/api/join")
def join(payload: JoinPayload):
    allowed_memberships = {"Starter", "Member", "Organizer"}
    name = clean(payload.name, 120)
    email = clean(payload.email.lower(), 160)
    password = payload.password.strip()
    membership = payload.membership if payload.membership in allowed_memberships else "Member"

    if not name or not email or len(password) < 4:
        raise HTTPException(
            status_code=400,
            detail="Name, email, and a password with at least 4 characters are required.",
        )

    connection = connect_db()
    try:
        existing = connection.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,),
        ).fetchone()
        if existing:
            user_id = existing["id"]
            connection.execute(
                """
                UPDATE users
                SET name = ?, password_hash = ?, membership = ?
                WHERE id = ?
                """,
                (name, hash_password(password), membership, user_id),
            )
        else:
            cursor = connection.execute(
                """
                INSERT INTO users (name, email, password_hash, membership, joined_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (name, email, hash_password(password), membership, now_label()),
            )
            user_id = cursor.lastrowid

        connection.commit()
        user = connection.execute(
            "SELECT id, name, email, membership, joined_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    finally:
        connection.close()

    return create_session_response(dict(user), f"Your {membership} membership is active.")


@app.post("/api/logout")
def logout(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        connection = connect_db()
        try:
            connection.execute("DELETE FROM sessions WHERE token = ?", (token,))
            connection.commit()
        finally:
            connection.close()

    response = JSONResponse({"ok": True, "message": "You are logged out."})
    response.delete_cookie(SESSION_COOKIE)
    return response


@app.post("/api/comments")
def create_comment(payload: CommentPayload, request: Request):
    user = get_user_by_session(request)
    name = clean(user["name"] if user else payload.name, 120)
    text = clean(payload.text, 900)
    if not name or not text:
        raise HTTPException(status_code=400, detail="Name and comment text are required.")

    connection = connect_db()
    try:
        cursor = connection.execute(
            "INSERT INTO comments (user_name, text, created_at) VALUES (?, ?, ?)",
            (name, text, now_label()),
        )
        connection.commit()
        comment = connection.execute(
            "SELECT id, user_name, text, created_at FROM comments WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        return {"ok": True, "comment": dict(comment)}
    finally:
        connection.close()


@app.post("/api/broadcasts")
def create_broadcast(payload: BroadcastPayload, request: Request):
    user = get_user_by_session(request)
    if not user:
        raise HTTPException(status_code=401, detail="Log in or join before running a broadcast.")

    allowed_targets = {
        "Home page",
        "Who We Are page",
        "What We Do page",
        "Membership page",
        "Comments page",
        "All pages",
    }
    title = clean(payload.title, 140)
    target = payload.target if payload.target in allowed_targets else "All pages"
    message = clean(payload.message, 900)
    if not title or not message:
        raise HTTPException(status_code=400, detail="Broadcast title and message are required.")

    connection = connect_db()
    try:
        cursor = connection.execute(
            """
            INSERT INTO broadcasts (title, target, message, created_by, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (title, target, message, user["name"], "running", now_label()),
        )
        connection.commit()
        broadcast = connection.execute(
            """
            SELECT id, title, target, message, created_by, status, created_at
            FROM broadcasts
            WHERE id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()
        return {"ok": True, "broadcast": dict(broadcast)}
    finally:
        connection.close()


@app.get("/api/broadcasts")
def broadcasts():
    return {"broadcasts": get_recent_broadcasts()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
