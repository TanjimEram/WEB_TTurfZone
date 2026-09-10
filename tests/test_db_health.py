from services.db_health import check_database


def test_check_database_reports_connected_sqlite(app):
    result = check_database()
    assert result["connected"] is True
    assert result["dialect"] == "sqlite"
    assert result["missing_tables"] == []
    assert result["ok"] is True


def test_check_database_reports_missing_tables(app):
    from extensions import db
    db.drop_all()
    result = check_database()
    assert result["connected"] is True
    assert "bookings" in result["missing_tables"]
    assert result["ok"] is False
