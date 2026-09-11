import os
import uuid
import sqlite3
from datetime import datetime, timezone
from functools import wraps

from flask import Flask, request, jsonify, send_from_directory, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# ============================================================
# MSAFIRI GLOBAL MEDIA
# V3 FULL CLEAN
# Flask + PostgreSQL/SQLite + LiveKit
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_FILE = os.path.join(BASE_DIR, "index.html")
MEDIA_DIR = os.path.join(BASE_DIR, "media")

os.makedirs(MEDIA_DIR, exist_ok=True)

app = Flask(__name__, static_folder=None)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "change-this-secret-in-render"
)

app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

LIVEKIT_URL = os.environ.get("LIVEKIT_URL", "").strip()
LIVEKIT_API_KEY = os.environ.get("LIVEKIT_API_KEY", "").strip()
LIVEKIT_API_SECRET = os.environ.get("LIVEKIT_API_SECRET", "").strip()


# ============================================================
# DATABASE
# ============================================================

USE_POSTGRES = bool(DATABASE_URL)

if USE_POSTGRES:
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
    except Exception:
        USE_POSTGRES = False


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def db_connect():
    if USE_POSTGRES:
        conn = psycopg2.connect(
            DATABASE_URL,
            cursor_factory=RealDictCursor
        )
        return conn

    conn = sqlite3.connect(
        os.path.join(BASE_DIR, "msafiri.db"),
        check_same_thread=False
    )
    conn.row_factory = sqlite3.Row
    return conn


def execute(sql, params=(), fetchone=False, fetchall=False, commit=False):
    conn = db_connect()

    try:
        cur = conn.cursor()

        if USE_POSTGRES:
            sql = sql.replace("?", "%s")

        cur.execute(sql, params)

        result = None

        if fetchone:
            result = cur.fetchone()

        elif fetchall:
            result = cur.fetchall()

        if commit:
            conn.commit()

        return result

    finally:
        conn.close()


def init_db():

    conn = db_connect()

    try:
        cur = conn.cursor()

        if USE_POSTGRES:

            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    avatar TEXT DEFAULT '',
                    created_at TEXT NOT NULL
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    caption TEXT DEFAULT '',
                    media_url TEXT DEFAULT '',
                    media_type TEXT DEFAULT '',
                    created_at TEXT NOT NULL
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id SERIAL PRIMARY KEY,
                    sender_id INTEGER NOT NULL,
                    receiver_id INTEGER NOT NULL,
                    text TEXT DEFAULT '',
                    media_url TEXT DEFAULT '',
                    created_at TEXT NOT NULL
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS calls (
                    id SERIAL PRIMARY KEY,
                    caller_id INTEGER NOT NULL,
                    receiver_id INTEGER NOT NULL,
                    room_name TEXT NOT NULL,
                    call_type TEXT DEFAULT 'video',
                    status TEXT DEFAULT 'started',
                    created_at TEXT NOT NULL,
                    ended_at TEXT DEFAULT ''
                )
            """)

        else:

            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    avatar TEXT DEFAULT '',
                    created_at TEXT NOT NULL
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    caption TEXT DEFAULT '',
                    media_url TEXT DEFAULT '',
                    media_type TEXT DEFAULT '',
                    created_at TEXT NOT NULL
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender_id INTEGER NOT NULL,
                    receiver_id INTEGER NOT NULL,
                    text TEXT DEFAULT '',
                    media_url TEXT DEFAULT '',
                    created_at TEXT NOT NULL
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    caller_id INTEGER NOT NULL,
                    receiver_id INTEGER NOT NULL,
                    room_name TEXT NOT NULL,
                    call_type TEXT DEFAULT 'video',
                    status TEXT DEFAULT 'started',
                    created_at TEXT NOT NULL,
                    ended_at TEXT DEFAULT ''
                )
            """)

        conn.commit()

    finally:
        conn.close()


# ============================================================
# HELPERS
# ============================================================

def row_to_dict(row):
    if row is None:
        return None

    if isinstance(row, dict):
        return dict(row)

    return dict(row)


def current_user():
    uid = session.get("user_id")

    if not uid:
        return None

    row = execute(
        """
        SELECT id, name, email, avatar, created_at
        FROM users
        WHERE id = ?
        """,
        (uid,),
        fetchone=True
    )

    return row_to_dict(row)


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            return jsonify({
                "ok": False,
                "error": "Ingia kwanza."
            }), 401

        return fn(*args, **kwargs)

    return wrapper


def clean_text(value, max_length=5000):
    if value is None:
        return ""

    return str(value).strip()[:max_length]


# ============================================================
# FRONTEND
# ============================================================

@app.route("/", methods=["GET"])
def home():
    """
    IMPORTANT:
    Serve index.html directly from the same directory as main.py.
    This fixes the Render 200 0 problem caused by an empty response.
    """

    if not os.path.isfile(INDEX_FILE):
        return """
        <h1>MSAFIRI GLOBAL MEDIA</h1>
        <p>index.html haipo kwenye root ya project.</p>
        """, 500

    return send_from_directory(BASE_DIR, "index.html")


@app.route("/index.html", methods=["GET"])
def index_html():
    return home()


@app.route("/media/<path:filename>")
def media_file(filename):
    return send_from_directory(MEDIA_DIR, filename)


@app.route("/favicon.ico")
def favicon():
    return ("", 204)


# ============================================================
# HEALTH
# ============================================================

@app.route("/api/health", methods=["GET"])
def health():
    database = "postgresql" if USE_POSTGRES else "sqlite"

    return jsonify({
        "ok": True,
        "app": "MSAFIRI GLOBAL MEDIA",
        "version": "V3 FULL CLEAN",
        "database": database,
        "livekit": bool(
            LIVEKIT_URL and
            LIVEKIT_API_KEY and
            LIVEKIT_API_SECRET
        ),
        "time": now_iso()
    })


# ============================================================
# AUTH
# ============================================================

@app.route("/api/me", methods=["GET"])
def me():
    user = current_user()

    return jsonify({
        "ok": True,
        "user": user
    })


@app.route("/api/register", methods=["POST"])
def register():

    data = request.get_json(silent=True) or {}

    name = clean_text(data.get("name"), 100)
    email = clean_text(data.get("email"), 200).lower()
    password = str(data.get("password") or "")

    if not name:
        return jsonify({
            "ok": False,
            "error": "Weka jina."
        }), 400

    if not email or "@" not in email:
        return jsonify({
            "ok": False,
            "error": "Weka email sahihi."
        }), 400

    if len(password) < 6:
        return jsonify({
            "ok": False,
            "error": "Password iwe na angalau characters 6."
        }), 400

    existing = execute(
        "SELECT id FROM users WHERE email = ?",
        (email,),
        fetchone=True
    )

    if existing:
        return jsonify({
            "ok": False,
            "error": "Email tayari imesajiliwa."
        }), 409

    password_hash = generate_password_hash(password)
    created = now_iso()

    conn = db_connect()

    try:
        cur = conn.cursor()

        if USE_POSTGRES:

            cur.execute(
                """
                INSERT INTO users
                (name, email, password_hash, created_at)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (name, email, password_hash, created)
            )

            uid = cur.fetchone()["id"]

        else:

            cur.execute(
                """
                INSERT INTO users
                (name, email, password_hash, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (name, email, password_hash, created)
            )

            uid = cur.lastrowid

        conn.commit()

    finally:
        conn.close()

    session["user_id"] = uid

    return jsonify({
        "ok": True,
        "user": current_user()
    })


@app.route("/api/login", methods=["POST"])
def login():

    data = request.get_json(silent=True) or {}

    email = clean_text(data.get("email"), 200).lower()
    password = str(data.get("password") or "")

    user = execute(
        """
        SELECT *
        FROM users
        WHERE email = ?
        """,
        (email,),
        fetchone=True
    )

    if not user:
        return jsonify({
            "ok": False,
            "error": "Email au password si sahihi."
        }), 401

    user = row_to_dict(user)

    if not check_password_hash(
        user["password_hash"],
        password
    ):
        return jsonify({
            "ok": False,
            "error": "Email au password si sahihi."
        }), 401

    session["user_id"] = user["id"]

    user.pop("password_hash", None)

    return jsonify({
        "ok": True,
        "user": user
    })


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()

    return jsonify({
        "ok": True
    })


# ============================================================
# USERS
# ============================================================

@app.route("/api/users", methods=["GET"])
@login_required
def users():

    rows = execute(
        """
        SELECT id, name, email, avatar, created_at
        FROM users
        ORDER BY id DESC
        LIMIT 100
        """,
        fetchall=True
    )

    return jsonify({
        "ok": True,
        "users": [
            row_to_dict(x)
            for x in rows
        ]
    })


# ============================================================
# POSTS
# ============================================================

@app.route("/api/posts", methods=["GET"])
def get_posts():

    rows = execute(
        """
        SELECT
            p.id,
            p.user_id,
            p.caption,
            p.media_url,
            p.media_type,
            p.created_at,
            u.name AS user_name,
            u.avatar AS user_avatar
        FROM posts p
        JOIN users u ON u.id = p.user_id
        ORDER BY p.id DESC
        LIMIT 100
        """,
        fetchall=True
    )

    return jsonify({
        "ok": True,
        "posts": [
            row_to_dict(x)
            for x in rows
        ]
    })


@app.route("/api/posts", methods=["POST"])
@login_required
def create_post():

    user = current_user()
    data = request.get_json(silent=True) or {}

    caption = clean_text(data.get("caption"), 5000)
    media_url = clean_text(data.get("media_url"), 1000)
    media_type = clean_text(data.get("media_type"), 50)

    if not caption and not media_url:
        return jsonify({
            "ok": False,
            "error": "Weka caption au media."
        }), 400

    created = now_iso()

    conn = db_connect()

    try:
        cur = conn.cursor()

        if USE_POSTGRES:

            cur.execute(
                """
                INSERT INTO posts
                (user_id, caption, media_url, media_type, created_at)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    user["id"],
                    caption,
                    media_url,
                    media_type,
                    created
                )
            )

            pid = cur.fetchone()["id"]

        else:

            cur.execute(
                """
                INSERT INTO posts
                (user_id, caption, media_url, media_type, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user["id"],
                    caption,
                    media_url,
                    media_type,
                    created
                )
            )

            pid = cur.lastrowid

        conn.commit()

    finally:
        conn.close()

    return jsonify({
        "ok": True,
        "post_id": pid
    })


@app.route("/api/posts/<int:post_id>", methods=["DELETE"])
@login_required
def delete_post(post_id):

    user = current_user()

    post = execute(
        """
        SELECT id, user_id
        FROM posts
        WHERE id = ?
        """,
        (post_id,),
        fetchone=True
    )

    if not post:
        return jsonify({
            "ok": False,
            "error": "Post haipo."
        }), 404

    post = row_to_dict(post)

    if int(post["user_id"]) != int(user["id"]):
        return jsonify({
            "ok": False,
            "error": "Huna ruhusa kufuta post hii."
        }), 403

    execute(
        "DELETE FROM posts WHERE id = ?",
        (post_id,),
        commit=True
    )

    return jsonify({
        "ok": True
    })


# ============================================================
# MESSAGES / CHAT
# ============================================================

@app.route("/api/messages", methods=["GET"])
@login_required
def get_messages():

    user = current_user()

    try:
        other_id = int(request.args.get("user_id", "0"))
    except ValueError:
        other_id = 0

    if other_id <= 0:
        return jsonify({
            "ok": False,
            "error": "user_id haipo."
        }), 400

    rows = execute(
        """
        SELECT
            m.id,
            m.sender_id,
            m.receiver_id,
            m.text,
            m.media_url,
            m.created_at,
            u.name AS sender_name
        FROM messages m
        JOIN users u ON u.id = m.sender_id
        WHERE
            (m.sender_id = ? AND m.receiver_id = ?)
            OR
            (m.sender_id = ? AND m.receiver_id = ?)
        ORDER BY m.id ASC
        LIMIT 500
        """,
        (
            user["id"],
            other_id,
            other_id,
            user["id"]
        ),
        fetchall=True
    )

    return jsonify({
        "ok": True,
        "messages": [
            row_to_dict(x)
            for x in rows
        ]
    })


@app.route("/api/messages", methods=["POST"])
@login_required
def send_message():

    user = current_user()
    data = request.get_json(silent=True) or {}

    try:
        receiver_id = int(data.get("receiver_id"))
    except (TypeError, ValueError):
        return jsonify({
            "ok": False,
            "error": "receiver_id si sahihi."
        }), 400

    text = clean_text(data.get("text"), 5000)
    media_url = clean_text(data.get("media_url"), 1000)

    if receiver_id == user["id"]:
        return jsonify({
            "ok": False,
            "error": "Huwezi kujitumia message."
        }), 400

    if not text and not media_url:
        return jsonify({
            "ok": False,
            "error": "Message iko tupu."
        }), 400

    receiver = execute(
        "SELECT id FROM users WHERE id = ?",
        (receiver_id,),
        fetchone=True
    )

    if not receiver:
        return jsonify({
            "ok": False,
            "error": "Mtumiaji huyo hayupo."
        }), 404

    execute(
        """
        INSERT INTO messages
        (sender_id, receiver_id, text, media_url, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            user["id"],
            receiver_id,
            text,
            media_url,
            now_iso()
        ),
        commit=True
    )

    return jsonify({
        "ok": True
    })


# ============================================================
# LIVEKIT
# ============================================================

def livekit_available():
    return bool(
        LIVEKIT_URL and
        LIVEKIT_API_KEY and
        LIVEKIT_API_SECRET
    )


@app.route("/api/call/token", methods=["POST"])
@login_required
def call_token():

    if not livekit_available():
        return jsonify({
            "ok": False,
            "error": "LiveKit environment variables hazijawekwa vizuri kwenye Render."
        }), 500

    try:
        from livekit import api
    except Exception:
        return jsonify({
            "ok": False,
            "error": "livekit package haipo kwenye requirements.txt."
        }), 500

    user = current_user()
    data = request.get_json(silent=True) or {}

    room = clean_text(data.get("room"), 200)
    call_type = clean_text(
        data.get("call_type", "video"),
        20
    )

    try:
        receiver_id = int(data.get("receiver_id", 0))
    except (TypeError, ValueError):
        receiver_id = 0

    if not room:
        return jsonify({
            "ok": False,
            "error": "Room name haipo."
        }), 400

    if call_type not in ("video", "voice"):
        call_type = "video"

    # --------------------------------------------------------
    # START CALL
    # receiver_id ikiwa imeletwa = caller anaanzisha call
    # --------------------------------------------------------

    if receiver_id:

        if receiver_id == user["id"]:
            return jsonify({
                "ok": False,
                "error": "Huwezi kumpigia simu mwenyewe."
            }), 400

        receiver = execute(
            "SELECT id FROM users WHERE id = ?",
            (receiver_id,),
            fetchone=True
        )

        if not receiver:
            return jsonify({
                "ok": False,
                "error": "Mpokeaji wa call hayupo."
            }), 404

        # Prevent duplicate active call for same room
        active = execute(
            """
            SELECT id
            FROM calls
            WHERE room_name = ?
            AND status = 'started'
            """,
            (room,),
            fetchone=True
        )

        if not active:

            execute(
                """
                INSERT INTO calls
                (caller_id, receiver_id, room_name, call_type, status, created_at)
                VALUES (?, ?, ?, ?, 'started', ?)
                """,
                (
                    user["id"],
                    receiver_id,
                    room,
                    call_type,
                    now_iso()
                ),
                commit=True
            )

    # --------------------------------------------------------
    # LIVEKIT ACCESS TOKEN
    # --------------------------------------------------------

    try:

        token = (
            api.AccessToken(
                LIVEKIT_API_KEY,
                LIVEKIT_API_SECRET
            )
            .with_identity(
                str(user["id"])
            )
            .with_name(
                user["name"]
            )
            .with_grants(
                api.VideoGrants(
                    room_join=True,
                    room=room,
                    can_publish=True,
                    can_subscribe=True
                )
            )
        )

        jwt_token = token.to_jwt()

    except Exception as e:

        return jsonify({
            "ok": False,
            "error": f"LiveKit token error: {str(e)}"
        }), 500

    return jsonify({
        "ok": True,
        "token": jwt_token,
        "server_url": LIVEKIT_URL,
        "room": room,
        "call_type": call_type
    })


# ============================================================
# CALLS
# ============================================================

@app.route("/api/calls", methods=["GET"])
@login_required
def calls():

    user = current_user()

    rows = execute(
        """
        SELECT
            c.id,
            c.caller_id,
            c.receiver_id,
            c.room_name,
            c.call_type,
            c.status,
            c.created_at,
            c.ended_at,
            caller.name AS caller_name,
            receiver.name AS receiver_name
        FROM calls c
        JOIN users caller
            ON caller.id = c.caller_id
        JOIN users receiver
            ON receiver.id = c.receiver_id
        WHERE
            c.caller_id = ?
            OR c.receiver_id = ?
        ORDER BY c.id DESC
        LIMIT 100
        """,
        (
            user["id"],
            user["id"]
        ),
        fetchall=True
    )

    return jsonify({
        "ok": True,
        "calls": [
            row_to_dict(x)
            for x in rows
        ]
    })


@app.route("/api/calls/incoming", methods=["GET"])
@login_required
def incoming_calls():

    user = current_user()

    rows = execute(
        """
        SELECT
            c.id,
            c.caller_id,
            c.receiver_id,
            c.room_name,
            c.call_type,
            c.status,
            c.created_at,
            caller.name AS caller_name
        FROM calls c
        JOIN users caller
            ON caller.id = c.caller_id
        WHERE
            c.receiver_id = ?
            AND c.status = 'started'
        ORDER BY c.id DESC
        LIMIT 20
        """,
        (user["id"],),
        fetchall=True
    )

    return jsonify({
        "ok": True,
        "calls": [
            row_to_dict(x)
            for x in rows
        ]
    })


@app.route("/api/calls/<int:call_id>/accept", methods=["POST"])
@login_required
def accept_call(call_id):

    user = current_user()

    call = execute(
        """
        SELECT *
        FROM calls
        WHERE id = ?
        """,
        (call_id,),
        fetchone=True
    )

    if not call:
        return jsonify({
            "ok": False,
            "error": "Call haipo."
        }), 404

    call = row_to_dict(call)

    if int(call["receiver_id"]) != int(user["id"]):
        return jsonify({
            "ok": False,
            "error": "Huna ruhusa."
        }), 403

    if call["status"] != "started":
        return jsonify({
            "ok": False,
            "error": "Call hii haipo active."
        }), 400

    execute(
        """
        UPDATE calls
        SET status = 'accepted'
        WHERE id = ?
        """,
        (call_id,),
        commit=True
    )

    return jsonify({
        "ok": True,
        "call": call
    })


@app.route("/api/calls/<int:call_id>/reject", methods=["POST"])
@login_required
def reject_call(call_id):

    user = current_user()

    call = execute(
        """
        SELECT *
        FROM calls
        WHERE id = ?
        """,
        (call_id,),
        fetchone=True
    )

    if not call:
        return jsonify({
            "ok": False,
            "error": "Call haipo."
        }), 404

    call = row_to_dict(call)

    if int(call["receiver_id"]) != int(user["id"]):
        return jsonify({
            "ok": False,
            "error": "Huna ruhusa."
        }), 403

    execute(
        """
        UPDATE calls
        SET status = 'rejected',
            ended_at = ?
        WHERE id = ?
        """,
        (
            now_iso(),
            call_id
        ),
        commit=True
    )

    return jsonify({
        "ok": True
    })


@app.route("/api/call/end", methods=["POST"])
@login_required
def end_call():

    user = current_user()
    data = request.get_json(silent=True) or {}

    room = clean_text(data.get("room"), 200)

    if not room:
        return jsonify({
            "ok": False,
            "error": "Room haipo."
        }), 400

    execute(
        """
        UPDATE calls
        SET status = 'ended',
            ended_at = ?
        WHERE
            room_name = ?
            AND
            (caller_id = ? OR receiver_id = ?)
            AND
            status IN ('started', 'accepted')
        """,
        (
            now_iso(),
            room,
            user["id"],
            user["id"]
        ),
        commit=True
    )

    return jsonify({
        "ok": True
    })


# ============================================================
# FILE UPLOAD
# ============================================================

ALLOWED_EXTENSIONS = {
    "jpg", "jpeg", "png", "gif",
    "webp", "mp4", "webm",
    "mp3", "wav", "m4a",
    "pdf", "doc", "docx"
}


def allowed_file(filename):

    if "." not in filename:
        return False

    ext = filename.rsplit(".", 1)[1].lower()

    return ext in ALLOWED_EXTENSIONS


@app.route("/api/upload", methods=["POST"])
@login_required
def upload_file():

    if "file" not in request.files:
        return jsonify({
            "ok": False,
            "error": "File haijatumwa."
        }), 400

    file = request.files["file"]

    if not file.filename:
        return jsonify({
            "ok": False,
            "error": "Chagua file."
        }), 400

    if not allowed_file(file.filename):
        return jsonify({
            "ok": False,
            "error": "Aina ya file hairuhusiwi."
        }), 400

    original = secure_filename(file.filename)

    ext = ""

    if "." in original:
        ext = "." + original.rsplit(".", 1)[1].lower()

    filename = (
        uuid.uuid4().hex +
        ext
    )

    path = os.path.join(
        MEDIA_DIR,
        filename
    )

    file.save(path)

    return jsonify({
        "ok": True,
        "url": "/media/" + filename,
        "filename": filename
    })


# ============================================================
# MARKET
# ============================================================

@app.route("/api/market", methods=["GET"])
def market():

    return jsonify({
        "ok": True,
        "items": [
            {
                "id": 1,
                "name": "Digital Services",
                "category": "Services",
                "price": "TZS 10,000"
            },
            {
                "id": 2,
                "name": "Creative Studio",
                "category": "Digital",
                "price": "TZS 15,000"
            },
            {
                "id": 3,
                "name": "Education Materials",
                "category": "Education",
                "price": "TZS 5,000"
            }
        ]
    })


# ============================================================
# AI COUNCIL
# ============================================================

@app.route("/api/ai", methods=["POST"])
@login_required
def ai():

    data = request.get_json(silent=True) or {}

    council = clean_text(
        data.get("council", "Education AI"),
        100
    )

    prompt = clean_text(
        data.get("prompt") or data.get("message"),
        5000
    )

    if not prompt:
        return jsonify({
            "ok": False,
            "error": "Andika swali kwanza."
        }), 400

    # --------------------------------------------------------
    # V3 foundation.
    # Hapa tunaweza kuunganisha AI provider baadaye.
    # --------------------------------------------------------

    return jsonify({
        "ok": True,
        "council": council,
        "answer": (
            f"{council} imepokea swali lako. "
            "AI engine inaweza kuunganishwa hapa "
            "na provider wako wa AI."
        )
    })


# ============================================================
# REALITY LAB
# ============================================================

@app.route("/api/reality", methods=["POST"])
@login_required
def reality():

    data = request.get_json(silent=True) or {}

    mode = clean_text(
        data.get("mode", "object_counter"),
        100
    )

    return jsonify({
        "ok": True,
        "mode": mode,
        "result": {
            "message": "Reality Lab engine iko tayari kupokea image/camera input."
        }
    })


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(404)
def not_found(error):

    if request.path.startswith("/api/"):
        return jsonify({
            "ok": False,
            "error": "API endpoint haipo.",
            "path": request.path
        }), 404

    return home()


@app.errorhandler(413)
def too_large(error):

    return jsonify({
        "ok": False,
        "error": "File ni kubwa sana. Maximum ni 100MB."
    }), 413


@app.errorhandler(500)
def internal_error(error):

    return jsonify({
        "ok": False,
        "error": "Server error."
    }), 500


# ============================================================
# INITIALIZE DATABASE
# ============================================================

try:
    init_db()
    print("==========================================")
    print("MSAFIRI GLOBAL MEDIA V3")
    print("Database initialized")
    print("Database:", "PostgreSQL" if USE_POSTGRES else "SQLite")
    print("LiveKit:", "READY" if livekit_available() else "NOT CONFIGURED")
    print("Index:", INDEX_FILE)
    print("Index exists:", os.path.isfile(INDEX_FILE))
    print("==========================================")

except Exception as e:
    print("DATABASE INITIALIZATION ERROR:", repr(e))


# ============================================================
# LOCAL RUN
# Render uses: gunicorn main:app
# ============================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            "5000"
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
