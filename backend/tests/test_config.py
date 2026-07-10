"""Settings: Railway-style DATABASE_URL normalization + demo/static flags."""
from app.config import Settings


def test_database_url_postgresql_scheme_normalized():
    s = Settings(database_url="postgresql://u:p@host:5432/db")
    assert s.database_url == "postgresql+psycopg://u:p@host:5432/db"


def test_database_url_postgres_scheme_normalized():
    s = Settings(database_url="postgres://u:p@host:5432/db")
    assert s.database_url == "postgresql+psycopg://u:p@host:5432/db"


def test_database_url_with_driver_unchanged():
    s = Settings(database_url="postgresql+psycopg://u:p@host:5432/db")
    assert s.database_url == "postgresql+psycopg://u:p@host:5432/db"


def test_demo_and_static_defaults():
    s = Settings()
    assert s.demo_seed is True
    assert s.static_dir == ""
