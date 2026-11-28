from pathlib import Path

from dotenv import load_dotenv

test_env_file = Path(__file__).resolve().parents[1] / ".env.test"
if test_env_file.is_file():
    load_dotenv(test_env_file, override=False)

from epic23_test_support import (
    epic23_app,
    fake_redis,
    postgres_sessions,
    real_redis,
    sqlite_sessions,
    test_postgres_engine,
)


__all__ = [
    "epic23_app",
    "fake_redis",
    "postgres_sessions",
    "real_redis",
    "sqlite_sessions",
    "test_postgres_engine",
]
