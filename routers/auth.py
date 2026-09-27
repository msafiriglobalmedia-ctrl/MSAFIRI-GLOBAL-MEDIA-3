# ============================================================
# MSAFIRI GLOBAL MEDIA — Authentication Router
# Version: Media V0.0.1
# Purpose: Register, Login, Me, Logout, Change Password
# ============================================================

import os
import re
import jwt
from datetime import datetime, timedelta
from functools import wraps

from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash

from database import db
from models import User


# ------------------------------------------------------------
# 1. DEFINE BLUEPRINT
# ------------------------------------------------------------
auth_bp = Blueprint("auth", __name__)


# ------------------------------------------------------------
# 2. CONFIGURATION
# ------------------------------------------------------------
JWT_SECRET = os.getenv("JWT_SECRET", "msafiri-jwt-secret-2025-change-me")
JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", 168))  # 7 days
JWT_ALGORITHM = "HS256"


# ------------------------------------------------------------
# 3. TOKEN HELPERS
# ------------------------------------------------------------
def generate_token(user_id):
    """Generate a JWT token for a user."""
    payload = {
        "user_id": user_id,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token):
    """Decode a JWT token. Returns payload or None."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_token_from_request():
    """Extract Bearer token from Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    return None


# ------------------------------------------------------------
# 4. AUTH DECORATOR (Protect Routes)
# ------------------------------------------------------------
def token_required(f):
    """
    Decorator to protect routes.
    Usage:
        @token_required
        def my_route(current_user):
            ...
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_from_request()
        if not token:
            return jsonify({"error": "Authorization token missing"}), 401

        payload = decode_token(token)
        if not payload:
            return jsonify({"error": "Invalid or expired token"}), 401

        user = User.query.get(payload.get("user_id"))
        if not user or not user.is_active:
            return jsonify({"error": "User not found or inactive"}), 401

        return f(current_user=user, *args, **kwargs)
    return decorated


# ------------------------------------------------------------
# 5. VALIDATION HELPERS
# ------------------------------------------------------------
def validate_email(email):
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


def validate_username(username):
    """Username must be 3-30 chars, letters, numbers, underscore only."""
    pattern = r"^[a-zA-Z0-9_]{3,30}$"
    return re.match(pattern, username) is not None


# ------------------------------------------------------------
# 6. REGISTER ENDPOINT
# ------------------------------------------------------------
@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Register a new user.
    Body: { username, email, password, name? }
    """
    data = request.get_json(silent=True) or {}

    username = (data.get("username") or "").strip().lower()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    name = (data.get("name") or "").strip()

    # Validation
    if not username or not email or not password:
        return jsonify({"error": "Username, email, and password are required"}), 400

    if not validate_username(username):
        return jsonify({
            "error": "Username must be 3-30 characters (letters, numbers, underscore only)"
        }), 400

    if not validate_email(email):
        return jsonify({"error": "Invalid email address"}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    # Check duplicates
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already taken"}), 409

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 409

    # Create user
    user = User(
        username=username,
        email=email,
        name=name or username.title(),
        is_active=True
    )
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    # Generate token
    token = generate_token(user.id)

    return jsonify({
        "message": "Account created successfully",
        "token": token,
        "user": user.to_dict(include_email=True)
    }), 201


# ------------------------------------------------------------
# 7. LOGIN ENDPOINT
# ------------------------------------------------------------
@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Login an existing user.
    Body: { username_or_email, password }
    """
    data = request.get_json(silent=True) or {}

    identifier = (data.get("username") or data.get("email") or data.get("username_or_email") or "").strip().lower()
    password = data.get("password") or ""

    if not identifier or not password:
        return jsonify({"error": "Username/email and password are required"}), 400

    # Find user by username OR email
    user = User.query.filter(
        (User.username == identifier) | (User.email == identifier)
    ).first()

    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid credentials"}), 401

    if not user.is_active:
        return jsonify({"error": "Account is deactivated"}), 403

    # Update last_seen
    user.last_seen = datetime.utcnow()
    db.session.commit()

    token = generate_token(user.id)

    return jsonify({
        "message": "Login successful",
        "token": token,
        "user": user.to_dict(include_email=True)
    }), 200


# ------------------------------------------------------------
# 8. ME ENDPOINT (Get Current User)
# ------------------------------------------------------------
@auth_bp.route("/me", methods=["GET"])
@token_required
def me(current_user):
    """Get the currently authenticated user."""
    return jsonify({
        "user": current_user.to_dict(include_email=True)
    }), 200


# ------------------------------------------------------------
# 9. LOGOUT ENDPOINT
# ------------------------------------------------------------
@auth_bp.route("/logout", methods=["POST"])
@token_required
def logout(current_user):
    """
    Logout endpoint.
    With JWT, logout is handled client-side by deleting the token.
    This endpoint is a placeholder for future token blacklisting.
    """
    return jsonify({"message": "Logged out successfully"}), 200


# ------------------------------------------------------------
# 10. CHANGE PASSWORD
# ------------------------------------------------------------
@auth_bp.route("/change-password", methods=["PUT"])
@token_required
def change_password(current_user):
    """
    Change password for authenticated user.
    Body: { old_password, new_password }
    """
    data = request.get_json(silent=True) or {}
    old_password = data.get("old_password") or ""
    new_password = data.get("new_password") or ""

    if not old_password or not new_password:
        return jsonify({"error": "Old and new passwords are required"}), 400

    if not current_user.check_password(old_password):
        return jsonify({"error": "Old password is incorrect"}), 401

    if len(new_password) < 6:
        return jsonify({"error": "New password must be at least 6 characters"}), 400

    current_user.set_password(new_password)
    db.session.commit()

    return jsonify({"message": "Password changed successfully"}), 200


# ------------------------------------------------------------
# 11. VERIFY TOKEN (Optional)
# ------------------------------------------------------------
@auth_bp.route("/verify", methods=["POST"])
def verify():
    """
    Verify if a token is still valid.
    Body: { token }
    """
    data = request.get_json(silent=True) or {}
    token = data.get("token") or get_token_from_request()

    if not token:
        return jsonify({"valid": False, "error": "No token provided"}), 400

    payload = decode_token(token)
    if not payload:
        return jsonify({"valid": False, "error": "Invalid or expired token"}), 401

    user = User.query.get(payload.get("user_id"))
    if not user:
        return jsonify({"valid": False, "error": "User not found"}), 401

    return jsonify({
        "valid": True,
        "user": user.to_dict()
    }), 200


# ------------------------------------------------------------
# 12. EXPORTS
# ------------------------------------------------------------
__all__ = ["auth_bp", "token_required", "generate_token", "decode_token"]
