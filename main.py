import os, secrets, sqlite3
from datetime import datetime, timezone
from flask import Flask, jsonify, request, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash

# PRODUCTION:
# PostgreSQL: set DATABASE_URL in Render.
# Calls: set LIVEKIT_URL, LIVEKIT_API_KEY and LIVEKIT_API_SECRET in Render.
# Never put real secrets in GitHub or inside this file.

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

BASE = os.path.dirname(os.path.abspath(__file__))
SQLITE_DB = os.path.join(BASE, "msafiri_local.db")

app = Flask(__name__, static_folder=None)
app.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(32))
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.getenv("SESSION_COOKIE_SECURE", "1") == "1"

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
USE_POSTGRES = bool(DATABASE_URL)

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def db():
    if USE_POSTGRES:
        if psycopg is None:
            raise RuntimeError("psycopg is missing.")
        return psycopg.connect(DATABASE_URL, row_factory=dict_row)
    c = sqlite3.connect(SQLITE_DB)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    if USE_POSTGRES:
        with db() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS users(
                    id BIGSERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS posts(
                    id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    caption TEXT NOT NULL DEFAULT '',
                    media_url TEXT NOT NULL DEFAULT '',
                    media_type TEXT NOT NULL DEFAULT '',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS messages(
                    id BIGSERIAL PRIMARY KEY,
                    sender_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    receiver_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    body TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS calls(
                    id BIGSERIAL PRIMARY KEY,
                    caller_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    receiver_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    room_name TEXT NOT NULL,
                    call_type TEXT NOT NULL DEFAULT 'video',
                    status TEXT NOT NULL DEFAULT 'started',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    ended_at TIMESTAMPTZ
                );
                CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_messages_pair ON messages(sender_id, receiver_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_calls_receiver ON calls(receiver_id, created_at DESC);
            """)
    else:
        with db() as c:
            c.executescript("""
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
            """)

def me():
    uid = session.get("uid")
    if not uid:
        return None
    with db() as c:
        if USE_POSTGRES:
            r = c.execute("SELECT id,name,email,created_at FROM users WHERE id=%s", (uid,)).fetchone()
        else:
            r = c.execute("SELECT id,name,email,created_at FROM users WHERE id=?", (uid,)).fetchone()
    return dict(r) if r else None

def need():
    return me() is not None

@app.get("/")
def home():
    return send_from_directory(BASE, "index.html")

@app.get("/api/health")
def health():
    return jsonify(
        ok=True,
        service="MSAFIRI GLOBAL MEDIA V3 PRODUCTION",
        database="postgresql" if USE_POSTGRES else "sqlite-local",
        livekit=bool(os.getenv("LIVEKIT_URL") and os.getenv("LIVEKIT_API_KEY") and os.getenv("LIVEKIT_API_SECRET"))
    )

@app.get("/api/me")
def api_me():
    return jsonify(ok=True, user=me())

@app.post("/api/register")
def register():
    d = request.get_json(silent=True) or {}
    name = str(d.get("name", "")).strip()
    email = str(d.get("email", "")).strip().lower()
    pw = str(d.get("password", ""))
    if len(name) < 2:
        return jsonify(ok=False, error="Weka jina lako."), 400
    if "@" not in email or "." not in email:
        return jsonify(ok=False, error="Email si sahihi."), 400
    if len(pw) < 6:
        return jsonify(ok=False, error="Password iwe angalau herufi 6."), 400
    try:
        with db() as c:
            if USE_POSTGRES:
                r = c.execute(
                    "INSERT INTO users(name,email,password_hash,created_at) VALUES(%s,%s,%s,NOW()) RETURNING id",
                    (name, email, generate_password_hash(pw))
                ).fetchone()
                uid = r["id"]
            else:
                cur = c.execute(
                    "INSERT INTO users(name,email,password_hash,created_at) VALUES(?,?,?,?)",
                    (name, email, generate_password_hash(pw), now_iso())
                )
                uid = cur.lastrowid
        session["uid"] = uid
        return jsonify(ok=True, user=me())
    except Exception as e:
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            return jsonify(ok=False, error="Email hii tayari ina account."), 409
        app.logger.exception("register failed")
        return jsonify(ok=False, error="Account haikuweza kutengenezwa."), 500

@app.post("/api/login")
def login():
    d = request.get_json(silent=True) or {}
    email = str(d.get("email", "")).strip().lower()
    pw = str(d.get("password", ""))
    with db() as c:
        if USE_POSTGRES:
            u = c.execute("SELECT * FROM users WHERE email=%s", (email,)).fetchone()
        else:
            u = c.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    if not u or not check_password_hash(u["password_hash"], pw):
        return jsonify(ok=False, error="Email au password si sahihi."), 401
    session["uid"] = u["id"]
    return jsonify(ok=True, user=me())

@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify(ok=True)

@app.get("/api/posts")
def posts():
    with db() as c:
        if USE_POSTGRES:
            rows = c.execute("""
                SELECT p.*,u.name,u.email FROM posts p
                JOIN users u ON u.id=p.user_id
                ORDER BY p.created_at DESC LIMIT 100
            """).fetchall()
        else:
            rows = c.execute("""
                SELECT p.*,u.name,u.email FROM posts p
                JOIN users u ON u.id=p.user_id
                ORDER BY p.id DESC LIMIT 100
            """).fetchall()
    return jsonify(ok=True, posts=[dict(x) for x in rows])

@app.post("/api/posts")
def add_post():
    u = me()
    if not u:
        return jsonify(ok=False, error="Login required"), 401
    d = request.get_json(silent=True) or {}
    cap = str(d.get("caption", "")).strip()
    url = str(d.get("media_url", "")).strip()
    typ = str(d.get("media_type", "")).strip()
    if not cap and not url:
        return jsonify(ok=False, error="Weka caption au media URL."), 400
    with db() as c:
        if USE_POSTGRES:
            r = c.execute("""
                INSERT INTO posts(user_id,caption,media_url,media_type,created_at)
                VALUES(%s,%s,%s,%s,NOW()) RETURNING id
            """, (u["id"], cap, url, typ)).fetchone()
            pid = r["id"]
        else:
            cur = c.execute("""
                INSERT INTO posts(user_id,caption,media_url,media_type,created_at)
                VALUES(?,?,?,?,?)
            """, (u["id"], cap, url, typ, now_iso()))
            pid = cur.lastrowid
    return jsonify(ok=True, id=pid)

@app.delete("/api/posts/<int:pid>")
def del_post(pid):
    u = me()
    if not u:
        return jsonify(ok=False, error="Login required"), 401
    with db() as c:
        if USE_POSTGRES:
            r = c.execute(
                "DELETE FROM posts WHERE id=%s AND user_id=%s RETURNING id",
                (pid, u["id"])
            ).fetchone()
        else:
            cur = c.execute("DELETE FROM posts WHERE id=? AND user_id=?", (pid, u["id"]))
            r = {"id": pid} if cur.rowcount else None
    return jsonify(ok=bool(r), error=None if r else "Post haipo au si yako.")

@app.get("/api/users")
def users():
    u = me()
    if not u:
        return jsonify(ok=False, error="Login required"), 401
    with db() as c:
        if USE_POSTGRES:
            r = c.execute(
                "SELECT id,name,email FROM users WHERE id<>%s ORDER BY name",
                (u["id"],)
            ).fetchall()
        else:
            r = c.execute(
                "SELECT id,name,email FROM users WHERE id<>? ORDER BY name",
                (u["id"],)
            ).fetchall()
    return jsonify(ok=True, users=[dict(x) for x in r])

@app.post("/api/messages")
def msg():
    u = me()
    if not u:
        return jsonify(ok=False, error="Login required"), 401
    d = request.get_json(silent=True) or {}
    rid = d.get("receiver_id")
    body = str(d.get("body", "")).strip()
    if not rid or not body:
        return jsonify(ok=False, error="Message haijakamilika."), 400
    with db() as c:
        if USE_POSTGRES:
            ok = c.execute("SELECT id FROM users WHERE id=%s", (rid,)).fetchone()
            if not ok:
                return jsonify(ok=False, error="User hayupo."), 404
            c.execute(
                "INSERT INTO messages(sender_id,receiver_id,body,created_at) VALUES(%s,%s,%s,NOW())",
                (u["id"], rid, body)
            )
        else:
            ok = c.execute("SELECT id FROM users WHERE id=?", (rid,)).fetchone()
            if not ok:
                return jsonify(ok=False, error="User hayupo."), 404
            c.execute(
                "INSERT INTO messages(sender_id,receiver_id,body,created_at) VALUES(?,?,?,?)",
                (u["id"], rid, body, now_iso())
            )
    return jsonify(ok=True)

@app.get("/api/messages/<int:uid>")
def messages(uid):
    u = me()
    if not u:
        return jsonify(ok=False, error="Login required"), 401
    with db() as c:
        if USE_POSTGRES:
            r = c.execute("""
                SELECT m.*,u.name AS sender_name
                FROM messages m JOIN users u ON u.id=m.sender_id
                WHERE (m.sender_id=%s AND m.receiver_id=%s)
                   OR (m.sender_id=%s AND m.receiver_id=%s)
                ORDER BY m.created_at
            """, (u["id"], uid, uid, u["id"])).fetchall()
        else:
            r = c.execute("""
                SELECT m.*,u.name sender_name
                FROM messages m JOIN users u ON u.id=m.sender_id
                WHERE (m.sender_id=? AND m.receiver_id=?)
                   OR (m.sender_id=? AND m.receiver_id=?)
                ORDER BY m.id
            """, (u["id"], uid, uid, u["id"])).fetchall()
    return jsonify(ok=True, messages=[dict(x) for x in r])

@app.post("/api/call/token")
def call_token():
    u = me()
    if not u:
        return jsonify(ok=False, error="Login required"), 401
    if livekit_api is None:
        return jsonify(ok=False, error="LiveKit SDK haijawekwa kwenye server."), 503

    livekit_url = os.getenv("LIVEKIT_URL", "").strip()
    api_key = os.getenv("LIVEKIT_API_KEY", "").strip()
    api_secret = os.getenv("LIVEKIT_API_SECRET", "").strip()
    if not livekit_url or not api_key or not api_secret:
        return jsonify(ok=False, error="LiveKit credentials hazijawekwa Render Environment Variables."), 503

    d = request.get_json(silent=True) or {}
    room = str(d.get("room", "")).strip()
    call_type = str(d.get("call_type", "video")).strip().lower()
    receiver_id = d.get("receiver_id")

    if not room or len(room) > 120:
        return jsonify(ok=False, error="Room ya call si sahihi."), 400
    if call_type not in {"audio", "video"}:
        call_type = "video"

    identity = f"user-{u['id']}"
    token = (
        livekit_api.AccessToken(api_key, api_secret)
        .with_identity(identity)
        .with_name(identity)
        .with_grants(livekit_api.VideoGrants(room_join=True, room=room))
        .to_jwt()
    )

    if receiver_id:
        try:
            with db() as c:
                if USE_POSTGRES:
                    c.execute("""
                        INSERT INTO calls(caller_id,receiver_id,room_name,call_type,status,created_at)
                        VALUES(%s,%s,%s,%s,'started',NOW())
                    """, (u["id"], int(receiver_id), room, call_type))
                else:
                    c.execute("""
                        INSERT INTO calls(caller_id,receiver_id,room_name,call_type,status,created_at)
                        VALUES(?,?,?,?,?,?)
                    """, (u["id"], int(receiver_id), room, call_type, "started", now_iso()))
        except Exception:
            app.logger.exception("call log failed")

    return jsonify(ok=True, server_url=livekit_url, token=token, room=room, call_type=call_type)

@app.post("/api/call/end")
def end_call():
    u = me()
    if not u:
        return jsonify(ok=False, error="Login required"), 401
    room = str((request.get_json(silent=True) or {}).get("room", "")).strip()
    if not room:
        return jsonify(ok=False, error="Room haipo."), 400
    with db() as c:
        if USE_POSTGRES:
            c.execute("""
                UPDATE calls SET status='ended', ended_at=NOW()
                WHERE room_name=%s AND (caller_id=%s OR receiver_id=%s) AND ended_at IS NULL
            """, (room, u["id"], u["id"]))
        else:
            c.execute("""
                UPDATE calls SET status='ended', ended_at=?
                WHERE room_name=? AND (caller_id=? OR receiver_id=?) AND ended_at IS NULL
            """, (now_iso(), room, u["id"], u["id"]))
    return jsonify(ok=True)

@app.get("/api/calls")
def calls():
    u = me()
    if not u:
        return jsonify(ok=False, error="Login required"), 401
    with db() as c:
        if USE_POSTGRES:
            rows = c.execute("""
                SELECT c.*,cu.name AS caller_name,ru.name AS receiver_name
                FROM calls c
                JOIN users cu ON cu.id=c.caller_id
                JOIN users ru ON ru.id=c.receiver_id
                WHERE c.caller_id=%s OR c.receiver_id=%s
                ORDER BY c.created_at DESC LIMIT 50
            """, (u["id"], u["id"])).fetchall()
        else:
            rows = c.execute("""
                SELECT c.*,cu.name AS caller_name,ru.name AS receiver_name
                FROM calls c
                JOIN users cu ON cu.id=c.caller_id
                JOIN users ru ON ru.id=c.receiver_id
                WHERE c.caller_id=? OR c.receiver_id=?
                ORDER BY c.id DESC LIMIT 50
            """, (u["id"], u["id"])).fetchall()
    return jsonify(ok=True, calls=[dict(x) for x in rows])

@app.get("/api/market")
def market():
    return jsonify(ok=True, items=[
        {"title":"Smart Phone","category":"Electronics","price":"TZS 450,000","icon":"📱"},
        {"title":"Laptop Pro","category":"Electronics","price":"TZS 1,850,000","icon":"💻"},
        {"title":"Solar Power Kit","category":"Energy","price":"TZS 280,000","icon":"☀️"},
        {"title":"Study Tablet","category":"Education","price":"TZS 520,000","icon":"📚"},
        {"title":"Agro Sensor","category":"Agriculture","price":"TZS 160,000","icon":"🌱"},
        {"title":"Headphones","category":"Tech","price":"TZS 95,000","icon":"🎧"}
    ])

@app.post("/api/ai")
def ai():
    if not need():
        return jsonify(ok=False, error="Login required"), 401
    d = request.get_json(silent=True) or {}
    council = d.get("council", "Education AI")
    q = str(d.get("question", "")).strip()
    if not q:
        return jsonify(ok=False, error="Andika swali kwanza."), 400
    answers = {
        "Education AI":"Nitaeleza dhana kwa hatua, mfano, mazoezi na maswali ya kujipima. Taja nchi, level na topic kwa syllabus maalum.",
        "Health AI":"Nitaeleza taarifa za kielimu kwa usalama; si utambuzi wa daktari. Kwa dalili hatari, mtaalamu wa afya anahitajika.",
        "AgroAI":"Taja zao, eneo, udongo, msimu na tatizo; kisha nitaunda mpango wa kilimo.",
        "Business AI":"Nitaangalia mteja, tatizo, value proposition, gharama, mapato, ushindani na hatua za kuanza.",
        "ResearchAI":"Tutaunda research question, hypothesis, methodology, sources, analysis na conclusion.",
        "Tech AI":"Nitaeleza architecture, teknolojia, security, testing na deployment.",
        "Vision AI":"UI ya Vision AI iko tayari; model ya picha halisi itaunganishwa kupitia vision API."
    }
    return jsonify(ok=True, council=council, answer=answers.get(council, answers["Education AI"]), question=q)

@app.post("/api/reality")
def reality():
    if not need():
        return jsonify(ok=False, error="Login required"), 401
    tool = (request.get_json(silent=True) or {}).get("tool", "Reality Lab")
    return jsonify(ok=True, result=f"{tool}: foundation iko tayari. Vision/AR engine halisi itaunganishwa production.")

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
