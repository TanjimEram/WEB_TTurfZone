from config import normalize_database_url


def test_postgres_scheme_becomes_psycopg_driver():
    assert normalize_database_url("postgres://u:p@h/db") == "postgresql+psycopg://u:p@h/db"


def test_postgresql_scheme_becomes_psycopg_driver():
    url = "postgresql://u:p@h/db?sslmode=require"
    assert normalize_database_url(url) == "postgresql+psycopg://u:p@h/db?sslmode=require"


def test_already_normalized_url_is_unchanged():
    url = "postgresql+psycopg://u:p@h/db"
    assert normalize_database_url(url) == url


def test_sqlite_url_is_unchanged():
    assert normalize_database_url("sqlite:///x.sqlite") == "sqlite:///x.sqlite"
