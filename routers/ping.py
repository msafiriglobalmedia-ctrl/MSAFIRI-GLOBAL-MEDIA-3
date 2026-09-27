# ============================================================
# MSAFIRI GLOBAL MEDIA — Ping Router
# Version: Media V0.0.1
# Purpose: Health check endpoint
# ============================================================

from datetime import datetime
from flask import Blueprint, jsonify, request


# ------------------------------------------------------------
# 1. DEFINE BLUEPRINT
# ------------------------------------------------------------
ping_bp = Blueprint("ping", __name__)


# ------------------------------------------------------------
# 2. PING ENDPOINT
# ------------------------------------------------------------
@ping_bp.route("/ping", methods=["GET"])
def ping():
    """
    Basic health check endpoint.
    Returns server status, timestamp, and version.
    """
    return jsonify({
        "status": "ok",
        "message": "MSAFIRI GLOBAL MEDIA is alive",
        "app": "MSAFIRI GLOBAL MEDIA",
        "version": "Media V0.0.1",
        "timestamp": datetime.utcnow().isoformat(),
        "server_time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    }), 200


# ------------------------------------------------------------
# 3. PING WITH ECHO (Optional)
# ------------------------------------------------------------
@ping_bp.route("/ping/echo", methods=["GET", "POST"])
def ping_echo():
    """
    Echo endpoint — returns whatever you send.
    Useful for testing API connectivity.
    """
    data = {
        "status": "ok",
        "method": request.method,
        "args": dict(request.args),
        "json": request.get_json(silent=True),
        "timestamp": datetime.utcnow().isoformat()
    }
    return jsonify(data), 200


# ------------------------------------------------------------
# 4. PING WITH DB CHECK (Optional)
# ------------------------------------------------------------
@ping_bp.route("/ping/db", methods=["GET"])
def ping_db():
    """
    Health check that also verifies database connection.
    """
    from database import db
    from sqlalchemy import text

    try:
        # Try to execute a simple query
        db.session.execute(text("SELECT 1"))
        db_status = "ok"
        db_message = "Database connected"
    except Exception as e:
        db_status = "error"
        db_message = str(e)

    return jsonify({
        "status": "ok" if db_status == "ok" else "degraded",
        "api": "ok",
        "database": {
            "status": db_status,
            "message": db_message
        },
        "timestamp": datetime.utcnow().isoformat()
    }), 200 if db_status == "ok" else 503


# ------------------------------------------------------------
# 5. EXPORTS
# ------------------------------------------------------------
__all__ = ["ping_bp"]
