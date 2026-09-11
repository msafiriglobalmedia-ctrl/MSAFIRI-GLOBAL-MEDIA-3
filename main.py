import os
import secrets
import sqlite3
from datetime import datetime, timezone

from flask import Flask, jsonify, request, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash

# =========================================================
# OPTIONAL PRODUCTION PACKAGES
# =========================================================

try:
    import psycopg
    from psycopg.rows import dict_row
except Exception:
    psycopg = None
    dict_row = None

try:
    from livekit import api as livekit_api
except Exception:
    livekit_api = None


# =========================================================
# APP CONFIG
# =========================================================

BASE = os.path.dirname(os.path.abspath(__file__))
SQLITE_DB = os.path.join(BASE, "msafiri_local.db")

app = Flask(__name__, static_folder=None)

SECRET_KEY = os.getenv("SECRET_KEY", "").strip()

if not SECRET_KEY:
    # Local development fallback only.
    # On Render, SECRET_KEY MUST be configured.
    SECRET_KEY = secrets.token_hex(32)

app.secret_key = SECRET_KEY

app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# Render normally uses HTTPS.
# Local HTTP development can override with:
# SESSION_COOKIE_SECURE=0
secure_cookie = os.getenv("SESSION_COOKIE_SECURE")

if secure_cookie is None:
    app.config["SESSION_COOKIE_SECURE"] = bool(
        os.getenv("RENDER", "").strip()
    )
else:
    app.config["SESSION_COOKIE_SECURE"] = secure_cookie == "1"


# =========================================================
# DATABASE
# =========================================================

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

# Render/Postgres compatibility
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql://" + DATABASE_URL[len("postgres://"):]

USE_POSTGRES = bool(DATABASE_URL)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def db():
    """
    PostgreSQL on Render.
    SQLite for local Pydroid testing.
    """

    if USE_POSTGRES:

        if psycopg is None:
            raise RuntimeError(
                "psycopg haijawekwa. "
                "Weka psycopg[binary] kwenye requirements.txt."
            )

        return psycopg.connect(
            DATABASE_URL,
            row_factory=dict_row
        )

    connection = sqlite3.connect(SQLITE_DB)
    connection.row_factory = sqlite3.Row

    return connection


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

def init_postgres():

    statements = [

        """
        CREATE TABLE IF NOT EXISTS users(
            id BIGSERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,

        """
        CREATE TABLE IF NOT EXISTS posts(
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL
                REFERENCES users(id)
                ON DELETE CASCADE,
            caption TEXT NOT NULL DEFAULT '',
            media_url TEXT NOT NULL DEFAULT '',
            media_type TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,

        """
        CREATE TABLE IF NOT EXISTS messages(
            id BIGSERIAL PRIMARY KEY,
            sender_id BIGINT NOT NULL
                REFERENCES users(id)
                ON DELETE CASCADE,
            receiver_id BIGINT NOT NULL
                REFERENCES users(id)
                ON DELETE CASCADE,
            body TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,

        """
        CREATE TABLE IF NOT EXISTS calls(
            id BIGSERIAL PRIMARY KEY,
            caller_id BIGINT NOT NULL
                REFERENCES users(id)
                ON DELETE CASCADE,
            receiver_id BIGINT NOT NULL
                REFERENCES users(id)
                ON DELETE CASCADE,
            room_name TEXT NOT NULL,
            call_type TEXT NOT NULL DEFAULT 'video',
            status TEXT NOT NULL DEFAULT 'started',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            ended_at TIMESTAMPTZ
        )
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_posts_created
        ON posts(created_at DESC)
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_messages_pair
        ON messages(sender_id, receiver_id, created_at)
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_calls_receiver
        ON calls(receiver_id, created_at DESC)
        """
    ]

    with db() as conn:

        for sql in statements:
            conn.execute(sql)


def init_sqlite():

    with db() as conn:

        conn.executescript("""

        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS posts(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            caption TEXT NOT NULL DEFAULT '',
            media_url TEXT NOT NULL DEFAULT '',
            media_type TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS messages(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS calls(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            caller_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            room_name TEXT NOT NULL,
            call_type TEXT NOT NULL DEFAULT 'video',
            status TEXT NOT NULL DEFAULT 'started',
            created_at TEXT NOT NULL,
            ended_at TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_posts_created
        ON posts(created_at);

        CREATE INDEX IF NOT EXISTS idx_messages_pair
        ON messages(sender_id, receiver_id, created_at);

        """)


def init_db():

    try:

        if USE_POSTGRES:
            init_postgres()
        else:
            init_sqlite()

        app.logger.info(
            "Database initialized: %s",
            "PostgreSQL" if USE_POSTGRES else "SQLite"
        )

    except Exception:

        app.logger.exception(
            "Database initialization failed"
        )

        raise


# =========================================================
# AUTH HELPERS
# =========================================================

def me():

    uid = session.get("uid")

    if not uid:
        return None

    try:

        with db() as conn:

            if USE_POSTGRES:

                row = conn.execute(
                    """
                    SELECT id, name, email, created_at
                    FROM users
                    WHERE id=%s
                    """,
                    (uid,)
                ).fetchone()

            else:

                row = conn.execute(
                    """
                    SELECT id, name, email, created_at
                    FROM users
                    WHERE id=?
                    """,
                    (uid,)
                ).fetchone()

        return dict(row) if row else None

    except Exception:

        app.logger.exception("me() failed")
        return None


def require_login():

    user = me()

    if not user:
        return None

    return user


# =========================================================
# HOME
# =========================================================

@app.get("/")
def home():

    return send_from_directory(
        BASE,
        "index.html"
    )


# =========================================================
# HEALTH
# =========================================================

@app.get("/api/health")
def health():

    postgres_ok = False

    if USE_POSTGRES:

        try:

            with db() as conn:
                conn.execute("SELECT 1")

            postgres_ok = True

        except Exception:

            postgres_ok = False

    else:

        postgres_ok = True

    livekit_ok = bool(
        os.getenv("LIVEKIT_URL", "").strip()
        and
        os.getenv("LIVEKIT_API_KEY", "").strip()
        and
        os.getenv("LIVEKIT_API_SECRET", "").strip()
    )

    return jsonify(
        ok=True,
        service="MSAFIRI GLOBAL MEDIA V3",
        database="postgresql" if USE_POSTGRES else "sqlite-local",
        database_connected=postgres_ok,
        livekit=livekit_ok
    )


# =========================================================
# CURRENT USER
# =========================================================

@app.get("/api/me")
def api_me():

    return jsonify(
        ok=True,
        user=me()
    )


# =========================================================
# REGISTER
# =========================================================

@app.post("/api/register")
def register():

    data = request.get_json(silent=True) or {}

    name = str(
        data.get("name", "")
    ).strip()

    email = str(
        data.get("email", "")
    ).strip().lower()

    password = str(
        data.get("password", "")
    )

    if len(name) < 2:

        return jsonify(
            ok=False,
            error="Weka jina lako."
        ), 400

    if len(name) > 80:

        return jsonify(
            ok=False,
            error="Jina ni refu sana."
        ), 400

    if "@" not in email or "." not in email:

        return jsonify(
            ok=False,
            error="Email si sahihi."
        ), 400

    if len(email) > 180:

        return jsonify(
            ok=False,
            error="Email ni ndefu sana."
        ), 400

    if len(password) < 6:

        return jsonify(
            ok=False,
            error="Password iwe angalau herufi 6."
        ), 400

    password_hash = generate_password_hash(
        password
    )

    try:

        with db() as conn:

            if USE_POSTGRES:

                row = conn.execute(
                    """
                    INSERT INTO users
                    (name, email, password_hash, created_at)
                    VALUES
                    (%s, %s, %s, NOW())
                    RETURNING id
                    """,
                    (
                        name,
                        email,
                        password_hash
                    )
                ).fetchone()

                uid = row["id"]

            else:

                cur = conn.execute(
                    """
                    INSERT INTO users
                    (name, email, password_hash, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        name,
                        email,
                        password_hash,
                        now_iso()
                    )
                )

                uid = cur.lastrowid

        session.clear()
        session["uid"] = uid
        session.permanent = True

        return jsonify(
            ok=True,
            user=me()
        )

    except Exception as e:

        message = str(e).lower()

        if (
            "unique" in message
            or
            "duplicate" in message
        ):

            return jsonify(
                ok=False,
                error="Email hii tayari ina account."
            ), 409

        app.logger.exception(
            "Registration failed"
        )

        return jsonify(
            ok=False,
            error="Account haikuweza kutengenezwa."
        ), 500


# =========================================================
# LOGIN
# =========================================================

@app.post("/api/login")
def login():

    data = request.get_json(silent=True) or {}

    email = str(
        data.get("email", "")
    ).strip().lower()

    password = str(
        data.get("password", "")
    )

    if not email or not password:

        return jsonify(
            ok=False,
            error="Weka email na password."
        ), 400

    try:

        with db() as conn:

            if USE_POSTGRES:

                user = conn.execute(
                    """
                    SELECT *
                    FROM users
                    WHERE email=%s
                    """,
                    (email,)
                ).fetchone()

            else:

                user = conn.execute(
                    """
                    SELECT *
                    FROM users
                    WHERE email=?
                    """,
                    (email,)
                ).fetchone()

        if not user:

            return jsonify(
                ok=False,
                error="Email au password si sahihi."
            ), 401

        if not check_password_hash(
            user["password_hash"],
            password
        ):

            return jsonify(
                ok=False,
                error="Email au password si sahihi."
            ), 401

        session.clear()
        session["uid"] = user["id"]
        session.permanent = True

        return jsonify(
            ok=True,
            user=me()
        )

    except Exception:

        app.logger.exception(
            "Login failed"
        )

        return jsonify(
            ok=False,
            error="Tatizo la server wakati wa login."
        ), 500


# =========================================================
# LOGOUT
# =========================================================

@app.post("/api/logout")
def logout():

    session.clear()

    return jsonify(
        ok=True
    )


# =========================================================
# POSTS
# =========================================================

@app.get("/api/posts")
def get_posts():

    try:

        with db() as conn:

            if USE_POSTGRES:

                rows = conn.execute(
                    """
                    SELECT
                        p.id,
                        p.user_id,
                        p.caption,
                        p.media_url,
                        p.media_type,
                        p.created_at,
                        u.name,
                        u.email
                    FROM posts p
                    JOIN users u
                    ON u.id = p.user_id
                    ORDER BY p.created_at DESC
                    LIMIT 100
                    """
                ).fetchall()

            else:

                rows = conn.execute(
                    """
                    SELECT
                        p.id,
                        p.user_id,
                        p.caption,
                        p.media_url,
                        p.media_type,
                        p.created_at,
                        u.name,
                        u.email
                    FROM posts p
                    JOIN users u
                    ON u.id = p.user_id
                    ORDER BY p.id DESC
                    LIMIT 100
                    """
                ).fetchall()

        return jsonify(
            ok=True,
            posts=[dict(row) for row in rows]
        )

    except Exception:

        app.logger.exception(
            "Loading posts failed"
        )

        return jsonify(
            ok=False,
            error="Posts hazikuweza kupakiwa.",
            posts=[]
        ), 500


@app.post("/api/posts")
def add_post():

    user = require_login()

    if not user:

        return jsonify(
            ok=False,
            error="Login required"
        ), 401

    data = request.get_json(silent=True) or {}

    caption = str(
        data.get("caption", "")
    ).strip()

    media_url = str(
        data.get("media_url", "")
    ).strip()

    media_type = str(
        data.get("media_type", "")
    ).strip().lower()

    if len(caption) > 5000:

        return jsonify(
            ok=False,
            error="Caption ni ndefu sana."
        ), 400

    if len(media_url) > 2000:

        return jsonify(
            ok=False,
            error="Media URL ni ndefu sana."
        ), 400

    if media_type not in {
        "",
        "image",
        "video"
    }:

        media_type = ""

    if not caption and not media_url:

        return jsonify(
            ok=False,
            error="Weka caption au media URL."
        ), 400

    try:

        with db() as conn:

            if USE_POSTGRES:

                row = conn.execute(
                    """
                    INSERT INTO posts
                    (
                        user_id,
                        caption,
                        media_url,
                        media_type,
                        created_at
                    )
                    VALUES
                    (%s, %s, %s, %s, NOW())
                    RETURNING id
                    """,
                    (
                        user["id"],
                        caption,
                        media_url,
                        media_type
                    )
                ).fetchone()

                post_id = row["id"]

            else:

                cur = conn.execute(
                    """
                    INSERT INTO posts
                    (
                        user_id,
                        caption,
                        media_url,
                        media_type,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        user["id"],
                        caption,
                        media_url,
                        media_type,
                        now_iso()
                    )
                )

                post_id = cur.lastrowid

        return jsonify(
            ok=True,
            id=post_id
        )

    except Exception:

        app.logger.exception(
            "Creating post failed"
        )

        return jsonify(
            ok=False,
            error="Post haikuweza kuwekwa."
        ), 500


# =========================================================
# DELETE POST
# =========================================================

@app.delete("/api/posts/<int:post_id>")
def delete_post(post_id):

    user = require_login()

    if not user:

        return jsonify(
            ok=False,
            error="Login required"
        ), 401

    try:

        with db() as conn:

            if USE_POSTGRES:

                row = conn.execute(
                    """
                    DELETE FROM posts
                    WHERE id=%s
                    AND user_id=%s
                    RETURNING id
                    """,
                    (
                        post_id,
                        user["id"]
                    )
                ).fetchone()

            else:

                cur = conn.execute(
                    """
                    DELETE FROM posts
                    WHERE id=?
                    AND user_id=?
                    """,
                    (
                        post_id,
                        user["id"]
                    )
                )

                row = (
                    {"id": post_id}
                    if cur.rowcount
                    else None
                )

        if not row:

            return jsonify(
                ok=False,
                error="Post haipo au si yako."
            ), 404

        return jsonify(
            ok=True
        )

    except Exception:

        app.logger.exception(
            "Delete post failed"
        )

        return jsonify(
            ok=False,
            error="Post haikuweza kufutwa."
        ), 500


# =========================================================
# USERS
# =========================================================

@app.get("/api/users")
def get_users():

    user = require_login()

    if not user:

        return jsonify(
            ok=False,
            error="Login required"
        ), 401

    try:

        with db() as conn:

            if USE_POSTGRES:

                rows = conn.execute(
                    """
                    SELECT id, name, email
                    FROM users
                    WHERE id<>%s
                    ORDER BY name
                    """,
                    (user["id"],)
                ).fetchall()

            else:

                rows = conn.execute(
                    """
                    SELECT id, name, email
                    FROM users
                    WHERE id<>?
                    ORDER BY name
                    """,
                    (user["id"],)
                ).fetchall()

        return jsonify(
            ok=True,
            users=[dict(row) for row in rows]
        )

    except Exception:

        app.logger.exception(
            "Loading users failed"
        )

        return jsonify(
            ok=False,
            error="Users hawakuweza kupakiwa."
        ), 500


# =========================================================
# MESSAGES
# =========================================================

@app.post("/api/messages")
def send_message():

    user = require_login()

    if not user:

        return jsonify(
            ok=False,
            error="Login required"
        ), 401

    data = request.get_json(silent=True) or {}

    receiver_id = data.get(
        "receiver_id"
    )

    body = str(
        data.get("body", "")
    ).strip()

    if not receiver_id or not body:

        return jsonify(
            ok=False,
            error="Message haijakamilika."
        ), 400

    if len(body) > 5000:

        return jsonify(
            ok=False,
            error="Message ni ndefu sana."
        ), 400

    try:

        receiver_id = int(
            receiver_id
        )

    except Exception:

        return jsonify(
            ok=False,
            error="Receiver si sahihi."
        ), 400

    if receiver_id == user["id"]:

        return jsonify(
            ok=False,
            error="Huwezi kutuma message kwako mwenyewe."
        ), 400

    try:

        with db() as conn:

            if USE_POSTGRES:

                exists = conn.execute(
                    """
                    SELECT id
                    FROM users
                    WHERE id=%s
                    """,
                    (receiver_id,)
                ).fetchone()

            else:

                exists = conn.execute(
                    """
                    SELECT id
                    FROM users
                    WHERE id=?
                    """,
                    (receiver_id,)
                ).fetchone()

            if not exists:

                return jsonify(
                    ok=False,
                    error="User hayupo."
                ), 404

            if USE_POSTGRES:

                row = conn.execute(
                    """
                    INSERT INTO messages
                    (
                        sender_id,
                        receiver_id,
                        body,
                        created_at
                    )
                    VALUES
                    (%s, %s, %s, NOW())
                    RETURNING id
                    """,
                    (
                        user["id"],
                        receiver_id,
                        body
                    )
                ).fetchone()

                message_id = row["id"]

            else:

                cur = conn.execute(
                    """
                    INSERT INTO messages
                    (
                        sender_id,
                        receiver_id,
                        body,
                        created_at
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        user["id"],
                        receiver_id,
                        body,
                        now_iso()
                    )
                )

                message_id = cur.lastrowid

        return jsonify(
            ok=True,
            id=message_id
        )

    except Exception:

        app.logger.exception(
            "Sending message failed"
        )

        return jsonify(
            ok=False,
            error="Message haikutumwa."
        ), 500


@app.get("/api/messages/<int:user_id>")
def get_messages(user_id):

    user = require_login()

    if not user:

        return jsonify(
            ok=False,
            error="Login required"
        ), 401

    if user_id == user["id"]:

        return jsonify(
            ok=True,
            messages=[]
        )

    try:

        with db() as conn:

            if USE_POSTGRES:

                rows = conn.execute(
                    """
                    SELECT
                        m.id,
                        m.sender_id,
                        m.receiver_id,
                        m.body,
                        m.created_at,
                        u.name AS sender_name
                    FROM messages m
                    JOIN users u
                    ON u.id=m.sender_id
                    WHERE
                    (
                        m.sender_id=%s
                        AND
                        m.receiver_id=%s
                    )
                    OR
                    (
                        m.sender_id=%s
                        AND
                        m.receiver_id=%s
                    )
                    ORDER BY m.created_at ASC
                    LIMIT 500
                    """,
                    (
                        user["id"],
                        user_id,
                        user_id,
                        user["id"]
                    )
                ).fetchall()

            else:

                rows = conn.execute(
                    """
                    SELECT
                        m.id,
                        m.sender_id,
                        m.receiver_id,
                        m.body,
                        m.created_at,
                        u.name AS sender_name
                    FROM messages m
                    JOIN users u
                    ON u.id=m.sender_id
                    WHERE
                    (
                        m.sender_id=?
                        AND
                        m.receiver_id=?
                    )
                    OR
                    (
                        m.sender_id=?
                        AND
                        m.receiver_id=?
                    )
                    ORDER BY m.id ASC
                    LIMIT 500
                    """,
                    (
                        user["id"],
                        user_id,
                        user_id,
                        user["id"]
                    )
                ).fetchall()

        return jsonify(
            ok=True,
            messages=[dict(row) for row in rows]
        )

    except Exception:

        app.logger.exception(
            "Loading messages failed"
        )

        return jsonify(
            ok=False,
            error="Messages hazikuweza kupakiwa.",
            messages=[]
        ), 500


# =========================================================
# LIVEKIT
# =========================================================

def livekit_credentials():

    url = os.getenv(
        "LIVEKIT_URL",
        ""
    ).strip()

    key = os.getenv(
        "LIVEKIT_API_KEY",
        ""
    ).strip()

    secret = os.getenv(
        "LIVEKIT_API_SECRET",
        ""
    ).strip()

    return url, key, secret


def valid_room(room):

    if not room:
        return False

    if len(room) > 120:
        return False

    allowed = (
        "abcdefghijklmnopqrstuvwxyz"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789-_"
    )

    return all(
        char in allowed
        for char in room
    )


@app.post("/api/call/token")
def call_token():

    user = require_login()

    if not user:

        return jsonify(
            ok=False,
            error="Login required"
        ), 401

    if livekit_api is None:

        return jsonify(
            ok=False,
            error="LiveKit SDK haijawekwa kwenye server."
        ), 503

    livekit_url, api_key, api_secret = (
        livekit_credentials()
    )

    if not livekit_url or not api_key or not api_secret:

        return jsonify(
            ok=False,
            error=(
                "LiveKit credentials hazijawekwa "
                "Render Environment Variables."
            )
        ), 503

    data = request.get_json(
        silent=True
    ) or {}

    room = str(
        data.get("room", "")
    ).strip()

    call_type = str(
        data.get("call_type", "video")
    ).strip().lower()

    receiver_id = data.get(
        "receiver_id"
    )

    if not valid_room(room):

        return jsonify(
            ok=False,
            error="Room ya call si sahihi."
        ), 400

    if call_type not in {
        "audio",
        "video"
    }:

        call_type = "video"

    identity = f"user-{user['id']}"

    try:

        token = (
            livekit_api.AccessToken(
                api_key,
                api_secret
            )
            .with_identity(identity)
            .with_name(user["name"])
            .with_grants(
                livekit_api.VideoGrants(
                    room_join=True,
                    room=room,
                    can_publish=True,
                    can_subscribe=True,
                    can_publish_data=True
                )
            )
            .to_jwt()
        )

    except Exception:

        app.logger.exception(
            "LiveKit token generation failed"
        )

        return jsonify(
            ok=False,
            error="LiveKit token haikuweza kutengenezwa."
        ), 500

    # -----------------------------------------------------
    # SAVE CALL RECORD
    # -----------------------------------------------------

    if receiver_id:

        try:

            receiver_id = int(
                receiver_id
            )

            if receiver_id != user["id"]:

                with db() as conn:

                    if USE_POSTGRES:

                        exists = conn.execute(
                            """
                            SELECT id
                            FROM users
                            WHERE id=%s
                            """,
                            (receiver_id,)
                        ).fetchone()

                        if exists:

                            conn.execute(
                                """
                                INSERT INTO calls
                                (
                                    caller_id,
                                    receiver_id,
                                    room_name,
                                    call_type,
                                    status,
                                    created_at
                                )
                                VALUES
                                (
                                    %s,
                                    %s,
                                    %s,
                                    %s,
                                    'started',
                                    NOW()
                                )
                                """,
                                (
                                    user["id"],
                                    receiver_id,
                                    room,
                                    call_type
                                )
                            )

                    else:

                        exists = conn.execute(
                            """
                            SELECT id
                            FROM users
                            WHERE id=?
                            """,
                            (receiver_id,)
                        ).fetchone()

                        if exists:

                            conn.execute(
                                """
                                INSERT INTO calls
                                (
                                    caller_id,
                                    receiver_id,
                                    room_name,
                                    call_type,
                                    status,
                                    created_at
                                )
                                VALUES (?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    user["id"],
                                    receiver_id,
                                    room,
                                    call_type,
                                    "started",
                                    now_iso()
                                )
                            )

        except Exception:

            # Call should still work even if logging fails.
            app.logger.exception(
                "Call logging failed"
            )

    return jsonify(
        ok=True,
        server_url=livekit_url,
        token=token,
        room=room,
        call_type=call_type
    )


# =========================================================
# INCOMING / ACTIVE CALLS
# =========================================================

@app.get("/api/calls/incoming")
def incoming_calls():

    user = require_login()

    if not user:

        return jsonify(
            ok=False,
            error="Login required"
        ), 401

    try:

        with db() as conn:

            if USE_POSTGRES:

                rows = conn.execute(
                    """
                    SELECT
                        c.id,
                        c.caller_id,
                        c.receiver_id,
                        c.room_name,
                        c.call_type,
                        c.status,
                        c.created_at,
                        u.name AS caller_name
                    FROM calls c
                    JOIN users u
                    ON u.id=c.caller_id
                    WHERE
                        c.receiver_id=%s
                        AND
                        c.status='started'
                        AND
                        c.ended_at IS NULL
                    ORDER BY c.created_at DESC
                    LIMIT 20
                    """,
                    (user["id"],)
                ).fetchall()

            else:

                rows = conn.execute(
                    """
                    SELECT
                        c.id,
                        c.caller_id,
                        c.receiver_id,
                        c.room_name,
                        c.call_type,
                        c.status,
                        c.created_at,
                        u.name AS caller_name
                    FROM calls c
                    JOIN users u
                    ON u.id=c.caller_id
                    WHERE
                        c.receiver_id=?
                        AND
                        c.status='started'
                        AND
                        c.ended_at IS NULL
                    ORDER BY c.id DESC
                    LIMIT 20
                    """,
                    (user["id"],)
                ).fetchall()

        return jsonify(
            ok=True,
            calls=[dict(row) for row in rows]
        )

    except Exception:

        app.logger.exception(
            "Incoming calls failed"
        )

        return jsonify(
            ok=False,
            calls=[]
        ), 500


# =========================================================
# END CALL
# =========================================================

@app.post("/api/call/end")
def end_call():

    user = require_login()

    if not user:

        return jsonify(
            ok=False,
            error="Login required"
        ), 401

    data = request.get_json(
        silent=True
    ) or {}

    room = str(
        data.get("room", "")
    ).strip()

    if not room:

        return jsonify(
            ok=False,
            error="Room haipo."
        ), 400

    try:

        with db() as conn:

            if USE_POSTGRES:

                conn.execute(
                    """
                    UPDATE calls
                    SET
                        status='ended',
                        ended_at=NOW()
                    WHERE
                        room_name=%s
                        AND
                        (
                            caller_id=%s
                            OR
                            receiver_id=%s
                        )
                        AND
                        ended_at IS NULL
                    """,
                    (
                        room,
                        user["id"],
                        user["id"]
                    )
                )

            else:

                conn.execute(
                    """
                    UPDATE calls
                    SET
                        status='ended',
                        ended_at=?
                    WHERE
                        room_name=?
                        AND
                        (
                            caller_id=?
                            OR
                            receiver_id=?
                        )
                        AND
                        ended_at IS NULL
                    """,
                    (
                        now_iso(),
                        room,
                        user["id"],
                        user["id"]
                    )
                )

        return jsonify(
            ok=True
        )

    except Exception:

        app.logger.exception(
            "Ending call failed"
        )

        return jsonify(
            ok=False,
            error="Call haikuweza kufungwa."
        ), 500


# =========================================================
# CALL HISTORY
# =========================================================

@app.get("/api/calls")
def call_history():

    user = require_login()

    if not user:

        return jsonify(
            ok=False,
            error="Login required"
        ), 401

    try:

        with db() as conn:

            if USE_POSTGRES:

                rows = conn.execute(
                    """
                    SELECT
                        c.*,
                        cu.name AS caller_name,
                        ru.name AS receiver_name
                    FROM calls c
                    JOIN users cu
                    ON cu.id=c.caller_id
                    JOIN users ru
                    ON ru.id=c.receiver_id
                    WHERE
                        c.caller_id=%s
                        OR
                        c.receiver_id=%s
                    ORDER BY c.created_at DESC
                    LIMIT 50
                    """,
                    (
                        user["id"],
                        user["id"]
                    )
                ).fetchall()

            else:

                rows = conn.execute(
                    """
                    SELECT
                        c.*,
                        cu.name AS caller_name,
                        ru.name AS receiver_name
                    FROM calls c
                    JOIN users cu
                    ON cu.id=c.caller_id
                    JOIN users ru
                    ON ru.id=c.receiver_id
                    WHERE
                        c.caller_id=?
                        OR
                        c.receiver_id=?
                    ORDER BY c.id DESC
                    LIMIT 50
                    """,
                    (
                        user["id"],
                        user["id"]
                    )
                ).fetchall()

        return jsonify(
            ok=True,
            calls=[dict(row) for row in rows]
        )

    except Exception:

        app.logger.exception(
            "Call history failed"
        )

        return jsonify(
            ok=False,
            calls=[]
        ), 500


# =========================================================
# MARKET
# =========================================================

@app.get("/api/market")
def market():

    return jsonify(
        ok=True,
        items=[
            {
                "title": "Smart Phone",
                "category": "Electronics",
                "price": "TZS 450,000",
                "icon": "📱"
            },
            {
                "title": "Laptop Pro",
                "category": "Electronics",
                "price": "TZS 1,850,000",
                "icon": "💻"
            },
            {
                "title": "Solar Power Kit",
                "category": "Energy",
                "price": "TZS 280,000",
                "icon": "☀️"
            },
            {
                "title": "Study Tablet",
                "category": "Education",
                "price": "TZS 520,000",
                "icon": "📚"
            },
            {
                "title": "Agro Sensor",
                "category": "Agriculture",
                "price": "TZS 160,000",
                "icon": "🌱"
            },
            {
                "title": "Headphones",
                "category": "Tech",
                "price": "TZS 95,000",
                "icon": "🎧"
            }
        ]
    )


# =========================================================
# AI COUNCIL FOUNDATION
# =========================================================

@app.post("/api/ai")
def ai_council():

    user = require_login()

    if not user:

        return jsonify(
            ok=False,
            error="Login required"
        ), 401

    data = request.get_json(
        silent=True
    ) or {}

    council = str(
        data.get(
            "council",
            "Education AI"
        )
    ).strip()

    question = str(
        data.get(
            "question",
            ""
        )
    ).strip()

    if not question:

        return jsonify(
            ok=False,
            error="Andika swali kwanza."
        ), 400

    if len(question) > 5000:

        return jsonify(
            ok=False,
            error="Swali ni refu sana."
        ), 400

    answers = {

        "Education AI":
            "Education AI foundation iko tayari. "
            "Kwa jibu la kina, taja nchi, level ya elimu, "
            "subject na topic.",

        "Health AI":
            "Health AI inatoa taarifa za kielimu tu. "
            "Haiwezi kuchukua nafasi ya mtaalamu wa afya. "
            "Kwa hali ya dharura, tafuta msaada wa kitaalamu.",

        "AgroAI":
            "AgroAI foundation iko tayari. "
            "Taja zao, eneo, msimu, udongo na tatizo "
            "ili kuandaa uchambuzi wa kilimo.",

        "Business AI":
            "Business AI inaweza kuchambua customer, "
            "tatizo, value proposition, gharama, mapato, "
            "ushindani na business model.",

        "ResearchAI":
            "ResearchAI foundation iko tayari. "
            "Tunaweza kupanga research question, "
            "hypothesis, methodology, analysis na conclusion.",

        "Tech AI":
            "Tech AI foundation iko tayari. "
            "Inaweza kusaidia architecture, coding, "
            "security, testing na deployment.",

        "Vision AI":
            "Vision AI UI iko tayari. "
            "Vision model halisi itaunganishwa kupitia "
            "vision API."
    }

    answer = answers.get(
        council,
        answers["Education AI"]
    )

    return jsonify(
        ok=True,
        council=council,
        answer=answer,
        question=question
    )


# =========================================================
# REALITY LAB FOUNDATION
# =========================================================

@app.post("/api/reality")
def reality():

    user = require_login()

    if not user:

        return jsonify(
            ok=False,
            error="Login required"
        ), 401

    data = request.get_json(
        silent=True
    ) or {}

    tool = str(
        data.get(
            "tool",
            "Reality Lab"
        )
    ).strip()

    return jsonify(
        ok=True,
        result=(
            f"{tool}: foundation iko tayari. "
            "Vision/AR engine halisi itaunganishwa "
            "katika production."
        )
    )


# =========================================================
# ERROR HANDLERS
# =========================================================

@app.errorhandler(413)
def too_large(_):

    return jsonify(
        ok=False,
        error="File/request ni kubwa sana."
    ), 413


@app.errorhandler(404)
def not_found(_):

    if request.path.startswith("/api/"):

        return jsonify(
            ok=False,
            error="API endpoint haipo."
        ), 404

    return send_from_directory(
        BASE,
        "index.html"
    )


@app.errorhandler(500)
def server_error(_):

    app.logger.exception(
        "Internal server error"
    )

    return jsonify(
        ok=False,
        error="Internal server error."
    ), 500


# =========================================================
# STARTUP
# =========================================================

init_db()


if __name__ == "__main__":

    port = int(
        os.getenv(
            "PORT",
            "5000"
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
