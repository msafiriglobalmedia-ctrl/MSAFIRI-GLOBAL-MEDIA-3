# ============================================================
# MSAFIRI GLOBAL MEDIA — Database Configuration
# Version: Media V0.0.1
# Purpose: SQLAlchemy setup, DB connection, init_db()
# ============================================================

import os
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import event
from sqlalchemy.engine import Engine
import sqlite3


# ------------------------------------------------------------
# 1. BASE CLASS (SQLAlchemy 2.0 style)
# ------------------------------------------------------------
class Base(DeclarativeBase):
    pass


# ------------------------------------------------------------
# 2. INITIALIZE SQLALCHEMY
# ------------------------------------------------------------
db = SQLAlchemy(model_class=Base)


# ------------------------------------------------------------
# 3. SQLITE FOREIGN KEY SUPPORT
# ------------------------------------------------------------
# SQLite doesn't enforce foreign keys by default.
# This event listener enables it.
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# ------------------------------------------------------------
# 4. DATABASE CONFIGURATION HELPER
# ------------------------------------------------------------
def get_database_url():
    """
    Get database URL from environment variable.
    Falls back to SQLite for development.
    """
    url = os.getenv("DATABASE_URL", "").strip()

    if not url:
        # Default: SQLite file in the project root
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, "msafiri.db")
        url = f"sqlite:///{db_path}"
        print(f"[DATABASE] Using SQLite: {db_path}")

    elif url.startswith("postgres://"):
        # Render/Heroku fix: postgres:// → postgresql://
        url = url.replace("postgres://", "postgresql://", 1)
        print("[DATABASE] Using PostgreSQL")

    else:
        print("[DATABASE] Using custom DATABASE_URL")

    return url


# ------------------------------------------------------------
# 5. INITIALIZE DATABASE (Create Tables)
# ------------------------------------------------------------
def init_db(app=None):
    """
    Initialize database: create all tables if they don't exist.
    Call this inside app context.
    """
    try:
        # Import models here so they register with SQLAlchemy
        from models import (
            User,
            Post,
            Story,
            Status,
            Video,
            Conversation,
            Message,
            Like,
            Comment,
            Follow,
            Notification,
            Product,
            Community,
            CommunityMember
        )

        # Create all tables
        db.create_all()
        print("[DATABASE] ✅ All tables created/verified")

        # Optional: create default admin user if not exists
        _create_default_admin()

    except Exception as e:
        print(f"[DATABASE] ❌ Error initializing database: {e}")
        raise


# ------------------------------------------------------------
# 6. DEFAULT ADMIN USER (Optional)
# ------------------------------------------------------------
def _create_default_admin():
    """
    Create a default admin user if no users exist.
    Useful for first-time setup.
    """
    from models import User
    from werkzeug.security import generate_password_hash

    try:
        user_count = User.query.count()
        if user_count == 0:
            admin = User(
                username="msafiri",
                email="admin@msafiri.com",
                name="MSAFIRI WILLIAM MUNGA",
                password_hash=generate_password_hash("msafiri2025"),
                bio="Founder of MSAFIRI GLOBAL MEDIA",
                location="Tanzania",
                is_verified=True,
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
            print("[DATABASE] ✅ Default admin created:")
            print("           Username: msafiri")
            print("           Password: msafiri2025")
            print("           ⚠️  CHANGE THIS PASSWORD IMMEDIATELY!")
        else:
            print(f"[DATABASE] ℹ️  {user_count} user(s) already exist")
    except Exception as e:
        db.session.rollback()
        print(f"[DATABASE] ⚠️  Could not create default admin: {e}")


# ------------------------------------------------------------
# 7. DATABASE UTILITIES
# ------------------------------------------------------------
def reset_db(app):
    """
    ⚠️ DANGEROUS: Drop all tables and recreate.
    Only use in development!
    """
    with app.app_context():
        db.drop_all()
        db.create_all()
        print("[DATABASE] 🔄 Database reset complete")


def db_stats():
    """
    Get database statistics (row counts).
    """
    from models import User, Post, Story, Message

    stats = {
        "users": User.query.count(),
        "posts": Post.query.count(),
        "stories": Story.query.count(),
        "messages": Message.query.count()
    }
    return stats


# ------------------------------------------------------------
# 8. EXPORTS
# ------------------------------------------------------------
__all__ = [
    "db",
    "Base",
    "init_db",
    "reset_db",
    "db_stats",
    "get_database_url"
]
