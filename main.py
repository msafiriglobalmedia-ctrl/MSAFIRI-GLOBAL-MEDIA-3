# ============================================================
# MSAFIRI GLOBAL MEDIA — Main Flask Application
# Version: Media V0.0.1
# Purpose: Entry point, CORS, static serving, router registration
# ============================================================

import os
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import database
from database import db, init_db

# Import routers
from routers import (
    auth_bp,
    feed_bp,
    posts_bp,
    stories_bp,
    profile_bp,
    messages_bp,
    statuses_bp,
    videos_bp,
    ping_bp
)

# ------------------------------------------------------------
# 1. APP INITIALIZATION
# ------------------------------------------------------------
def create_app():
    app = Flask(
        __name__,
        static_folder="static",
        static_url_path="/static"
    )

    # ------------------------------------------------------------
    # 2. CONFIGURATION
    # ------------------------------------------------------------
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "msafiri-secret-key-change-me")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL",
        "sqlite:///msafiri.db"  # Default: SQLite for development
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100 MB max upload
    app.config["UPLOAD_FOLDER"] = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "static", "uploads"
    )

    # Create upload folder if it doesn't exist
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(os.path.join(app.config["UPLOAD_FOLDER"], "profiles"), exist_ok=True)
    os.makedirs(os.path.join(app.config["UPLOAD_FOLDER"], "posts"), exist_ok=True)
    os.makedirs(os.path.join(app.config["UPLOAD_FOLDER"], "stories"), exist_ok=True)
    os.makedirs(os.path.join(app.config["UPLOAD_FOLDER"], "messages"), exist_ok=True)

    # ------------------------------------------------------------
    # 3. CORS (Allow Frontend to talk to Backend)
    # ------------------------------------------------------------
    CORS(
        app,
        resources={r"/api/*": {"origins": "*"}},
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    )

    # ------------------------------------------------------------
    # 4. INITIALIZE DATABASE
    # ------------------------------------------------------------
    db.init_app(app)
    with app.app_context():
        init_db()

    # ------------------------------------------------------------
    # 5. REGISTER ROUTERS (All API Blueprints)
    # ------------------------------------------------------------
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(feed_bp, url_prefix="/api/feed")
    app.register_blueprint(posts_bp, url_prefix="/api/posts")
    app.register_blueprint(stories_bp, url_prefix="/api/stories")
    app.register_blueprint(profile_bp, url_prefix="/api/profile")
    app.register_blueprint(messages_bp, url_prefix="/api/messages")
    app.register_blueprint(statuses_bp, url_prefix="/api/statuses")
    app.register_blueprint(videos_bp, url_prefix="/api/videos")
    app.register_blueprint(ping_bp, url_prefix="/api")

    # ------------------------------------------------------------
    # 6. SERVE FRONTEND (index.html + static files)
    # ------------------------------------------------------------
    @app.route("/")
    def serve_index():
        """Serve the main index.html"""
        return send_from_directory(app.static_folder, "index.html")

    @app.route("/<path:path>")
    def serve_static(path):
        """Serve static files (JS, CSS, images)"""
        # If file exists in static folder, serve it
        file_path = os.path.join(app.static_folder, path)
        if os.path.isfile(file_path):
            return send_from_directory(app.static_folder, path)
        # Otherwise serve index.html (SPA fallback)
        return send_from_directory(app.static_folder, "index.html")

    @app.route("/login")
    def serve_login():
        """Serve login page"""
        return send_from_directory(app.static_folder, "login.html")

    @app.route("/register")
    def serve_register():
        """Serve register page"""
        return send_from_directory(app.static_folder, "register.html")

    # ------------------------------------------------------------
    # 7. GLOBAL ERROR HANDLERS
    # ------------------------------------------------------------
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not found", "status": 404}), 404

    @app.errorhandler(500)
    def server_error(error):
        return jsonify({"error": "Internal server error", "status": 500}), 500

    @app.errorhandler(413)
    def file_too_large(error):
        return jsonify({"error": "File too large. Max 100 MB", "status": 413}), 413

    # ------------------------------------------------------------
    # 8. HEALTH CHECK (Basic)
    # ------------------------------------------------------------
    @app.route("/health")
    def health():
        return jsonify({
            "status": "ok",
            "app": "MSAFIRI GLOBAL MEDIA",
            "version": "Media V0.0.1"
        }), 200

    return app


# ------------------------------------------------------------
# 9. RUN APP
# ------------------------------------------------------------
if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_ENV", "development") == "development"

    print("=" * 60)
    print("  MSAFIRI GLOBAL MEDIA — Media V0.0.1")
    print(f"  Server running on: http://0.0.0.0:{port}")
    print(f"  Debug mode: {debug}")
    print("=" * 60)

    app.run(
        host="0.0.0.0",
        port=port,
        debug=debug,
        threaded=True
    )
