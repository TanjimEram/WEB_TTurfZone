"""Application factory: start here to see how TTURFZONE is wired together.

Run locally:  flask --app app run --debug
"""
import os

from flask import Flask

from config import BASE_DIR, CONFIGS, normalize_database_url
from extensions import csrf, db, migrate


def create_app(env_name: str | None = None, overrides: dict | None = None) -> Flask:
    """Build the Flask app.

    env_name:  "development", "testing" or "production". Defaults to APP_ENV, then "development".
    overrides: config values applied last (used by tests).
    """
    env_name = env_name or os.environ.get("APP_ENV", "development")
    if env_name not in CONFIGS:
        raise RuntimeError(f"Unknown APP_ENV '{env_name}'. Use one of: {', '.join(CONFIGS)}")

    app = Flask(__name__)
    app.config.from_object(CONFIGS[env_name])
    _apply_environment(app, env_name)
    app.config.update(overrides or {})

    db.init_app(app)
    migrate.init_app(app, db, directory=str(BASE_DIR / "database" / "migrations"), render_as_batch=True)
    csrf.init_app(app)

    import models  # noqa: F401  (registers tables with SQLAlchemy)

    _register_blueprints(app)
    _register_security_headers(app)
    _register_error_pages(app)

    from cli import register_cli
    register_cli(app)

    return app


def _apply_environment(app: Flask, env_name: str) -> None:
    """Read SECRET_KEY and DATABASE_URL from the environment."""
    if env_name == "testing":
        return

    secret_key = os.environ.get("SECRET_KEY", "").strip()
    database_url = os.environ.get("DATABASE_URL", "").strip()

    if env_name == "production":
        missing = [name for name, value in (("SECRET_KEY", secret_key), ("DATABASE_URL", database_url)) if not value]
        if missing:
            raise RuntimeError("Production needs these environment variables: " + ", ".join(missing))

    if secret_key:
        app.config["SECRET_KEY"] = secret_key

    if database_url:
        app.config["SQLALCHEMY_DATABASE_URI"] = normalize_database_url(database_url)
    else:
        instance_dir = BASE_DIR / "instance"
        instance_dir.mkdir(exist_ok=True)
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{instance_dir / 'dev.sqlite'}"

    if database_url.startswith("sqlite"):
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {}


def _register_blueprints(app: Flask) -> None:
    from routes.admin import bp as admin_bp
    from routes.api import bp as api_bp
    from routes.public import bp as public_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(admin_bp)

    if app.config["ENABLE_DEV_TOOLS"]:
        from routes.dev import bp as dev_bp
        app.register_blueprint(dev_bp)


def _register_security_headers(app: Flask) -> None:
    @app.after_request
    def add_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return response


def _register_error_pages(app: Flask) -> None:
    """Friendly 404 / 500 pages. The 500 template touches no database."""
    from flask import render_template

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(_error):
        return render_template("errors/500.html"), 500
