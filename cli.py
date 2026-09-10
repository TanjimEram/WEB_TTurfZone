"""Command-line tools:  flask --app app <command>"""
import secrets

import click
from flask import Flask
from flask.cli import with_appcontext

from database.seed_data import DEFAULT_SETTINGS
from extensions import db
from models import Admin, TurfSettings
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
    for command in (db_check, seed_settings, create_admin, fake_bookings, fake_conflict_test, fake_clear):
        app.cli.add_command(command)
