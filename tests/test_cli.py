from models import Admin, Booking, TurfSettings


def test_db_check_reports_ok(app):
    result = app.test_cli_runner().invoke(args=["db-check"])
    assert result.exit_code == 0
    assert "Database OK" in result.output


def test_seed_settings_creates_single_row(app):
    runner = app.test_cli_runner()
    runner.invoke(args=["seed-settings"])
    runner.invoke(args=["seed-settings"])
    assert TurfSettings.query.count() == 1
    assert "TODO(owner)" in TurfSettings.current().address


def test_create_admin_stores_hashed_password(app):
    result = app.test_cli_runner().invoke(args=["create-admin", "--username", "owner"])
    assert result.exit_code == 0
    admin = Admin.query.filter_by(username="owner").one()
    printed = result.output.split("Password: ")[1].split()[0]
    assert len(printed) >= 20
    assert admin.password_hash != printed
    assert admin.check_password(printed)


def test_create_admin_refuses_duplicate_username(app):
    runner = app.test_cli_runner()
    runner.invoke(args=["create-admin", "--username", "owner"])
    result = runner.invoke(args=["create-admin", "--username", "owner"])
    assert result.exit_code != 0


def test_fake_commands_absent_without_dev_tools(app):
    """Production and testing have ENABLE_DEV_TOOLS off: fake-* must not exist."""
    for name in ("fake-bookings", "fake-conflict-test", "fake-clear"):
        assert name not in app.cli.commands


def test_fake_bookings_and_clear_commands(app):
    from cli import fake_bookings, fake_clear
    app.cli.add_command(fake_bookings)
    app.cli.add_command(fake_clear)
    runner = app.test_cli_runner()
    runner.invoke(args=["fake-bookings", "--count", "6"])
    assert Booking.query.count() == 6
    runner.invoke(args=["fake-clear"])
    assert Booking.query.count() == 0


def test_reset_admin_password_prints_a_new_one_and_signs_everyone_out(app):
    from services.auth import verify_admin
    runner = app.test_cli_runner()
    runner.invoke(args=["create-admin", "--username", "owner"])
    old_hash = Admin.query.filter_by(username="owner").one().password_hash
    result = runner.invoke(args=["reset-admin-password", "--username", "owner"])
    assert result.exit_code == 0
    new_password = result.output.split("New password for 'owner': ")[1].split()[0]
    assert len(new_password) == 20
    admin = Admin.query.filter_by(username="owner").one()
    assert admin.password_hash != old_hash  # different hash = every session's stamp is stale
    assert verify_admin("owner", new_password) is not None


def test_reset_admin_password_unknown_user(app):
    result = app.test_cli_runner().invoke(args=["reset-admin-password", "--username", "nobody"])
    assert result.exit_code != 0 and "No admin called 'nobody'" in result.output
