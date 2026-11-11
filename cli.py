"""Command-line tools:  flask --app app <command>"""
import secrets
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import click
from flask import Flask
from flask.cli import with_appcontext

from database.seed_data import DEFAULT_SETTINGS
from extensions import db
from models import Admin, TurfSettings
from services import google
from services.db_health import check_database
from services.fake_data import clear_fake_data, make_fake_bookings, try_double_booking


@click.command("db-check")
@with_appcontext
def db_check():
    """Connect to DATABASE_URL and report tables, migration and latency."""
    r = check_database()
    click.echo(f"Driver: {r['dialect']}  Host: {r['host']}  Database: {r['database']}")
    if not r["connected"]:
        raise click.ClickException(f"Could not connect: {r['error']}")
    click.echo(f"Round trip: {r['latency_ms']} ms   Migration: {r['migration_revision'] or 'none'}")
    if r["missing_tables"]:
        raise click.ClickException("Connected, but tables are missing: " + ", ".join(r["missing_tables"])
                                   + ". Run: flask --app app db upgrade")
    click.echo("Database OK")


@click.command("seed-settings")
@click.option("--force", is_flag=True, help="Overwrite the existing settings row with seed values.")
@with_appcontext
def seed_settings(force):
    """Create the single turf_settings row from database/seed_data.py."""
    settings = TurfSettings.current()
    if settings and not force:
        click.echo("Settings row already exists. Use --force to overwrite.")
        return
    if not settings:
        settings = TurfSettings(id=1)
        db.session.add(settings)
    for key, value in DEFAULT_SETTINGS.items():
        setattr(settings, key, value)
    db.session.commit()
    click.echo("Settings saved.")


@click.command("create-admin")
@click.option("--username", prompt=True)
@with_appcontext
def create_admin(username):
    """Create the owner login with a generated password (shown once)."""
    username = username.strip()
    if Admin.query.filter_by(username=username).first():
        raise click.ClickException(f"Admin '{username}' already exists.")
    password = secrets.token_urlsafe(15)  # 20 characters
    admin = Admin(username=username)
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    click.echo(f"Created admin '{username}'.")
    click.echo(f"Password: {password}")
    click.echo("Save it now in a password manager. It will not be shown again.")


@click.command("reset-admin-password")
@click.option("--username", prompt=True)
@with_appcontext
def reset_admin_password(username):
    """Recovery: give an admin a new generated password (shown once). Signs out every session."""
    admin = Admin.query.filter_by(username=username.strip()).first()
    if admin is None:
        raise click.ClickException(f"No admin called '{username.strip()}'.")
    password = secrets.token_urlsafe(15)  # 20 characters
    admin.set_password(password)  # new hash -> every existing session is logged out (D-49)
    db.session.commit()
    click.echo(f"New password for '{admin.username}': {password}")
    click.echo("Save it now in a password manager. It will not be shown again. All sessions are signed out.")


def _open_browser(url: str) -> None:
    webbrowser.open(url)


def _wait_for_gmail_code(state: str, port: int = 8765, timeout: int = 300) -> dict:
    """Serve one request on localhost:8765 (Google's redirect after consent) and return its
    query: {"code", "state"} or {"error"}. Stdlib http.server, nothing kept on disk."""
    result: dict = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 (http.server's name)
            query = parse_qs(urlparse(self.path).query)
            result.update({key: values[0] for key, values in query.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Done. You can close this tab and go back to the terminal.")

        def log_message(self, *args):  # keep the code out of the terminal log
            pass

    server = HTTPServer(("localhost", port), Handler)
    server.timeout = timeout
    server.handle_request()
    server.server_close()
    return result


@click.command("gmail-authorize")
@with_appcontext
def gmail_authorize():
    """One time, on your PC: let the site send email as the Gmail account (CR-9).

    Opens Google's consent page; sign in as tturfzone@gmail.com and allow "send email".
    Prints a refresh token once, for GMAIL_REFRESH_TOKEN in the cPanel environment.
    Needs GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env.
    """
    state = secrets.token_urlsafe(24)
    url = google.gmail_consent_url(state)
    click.echo("Opening Google's consent page. If it doesn't open, paste this into your browser:")
    click.echo(url)
    _open_browser(url)
    answer = _wait_for_gmail_code(state)
    if answer.get("error"):
        raise click.ClickException(f"Google said: {answer['error']}. Nothing was saved.")
    if not answer.get("code") or not secrets.compare_digest(answer.get("state", ""), state):
        raise click.ClickException("That reply didn't come from this request. Run the command again.")
    try:
        token = google.refresh_token_from_code(answer["code"])
    except google.GoogleError as exc:
        raise click.ClickException(f"Couldn't get the token: {exc}") from None
    click.echo("")
    click.echo("Put this in cPanel -> Setup Python App -> Environment variables as GMAIL_REFRESH_TOKEN:")
    click.echo(token)
    click.echo("")
    click.echo("It is not saved anywhere. Keep it secret like a password; then restart the app.")


@click.command("fake-bookings")
@click.option("--count", default=10, show_default=True)
@with_appcontext
def fake_bookings(count):
    """Create fake bookings (codes start with FK-)."""
    click.echo(f"Created {len(make_fake_bookings(count=count))} fake bookings.")


@click.command("fake-conflict-test")
@with_appcontext
def fake_conflict_test():
    """Try to book the same slot twice and show whether the database stopped it."""
    result = try_double_booking()
    click.echo(result["message"])
    if not result["conflict_caught"]:
        raise click.ClickException("Double-booking protection is NOT working.")


@click.command("fake-clear")
@with_appcontext
def fake_clear():
    """Delete all fake (FK-) bookings. Real bookings are untouched."""
    click.echo(f"Deleted {clear_fake_data()} fake bookings.")


def register_cli(app: Flask) -> None:
    """Fake-data commands exist only with ENABLE_DEV_TOOLS (D-18), never in production."""
    commands = [db_check, seed_settings, create_admin, reset_admin_password, gmail_authorize]
    if app.config["ENABLE_DEV_TOOLS"]:
        commands += [fake_bookings, fake_conflict_test, fake_clear]
    for command in commands:
        app.cli.add_command(command)
