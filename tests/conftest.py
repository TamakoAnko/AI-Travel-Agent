import os
from pathlib import Path

os.environ["EMBED_PROVIDER"] = "hash"
os.environ["DATABASE_PATH"] = "data/test_app.db"
os.environ["CHECKPOINT_PATH"] = "data/test_checkpoints.db"
os.environ["REDIS_FAKE"] = "1"

import pytest

DB_FILES = (
    "test_app.db", "test_app.db-wal", "test_app.db-shm",
    "test_checkpoints.db", "test_checkpoints.db-wal", "test_checkpoints.db-shm",
)


def _remove_db_files() -> None:
    for name in DB_FILES:
        Path("data", name).unlink(missing_ok=True)


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db():
    _remove_db_files()
    yield
    _remove_db_files()


@pytest.fixture(autouse=True)
def clean_redis():
    from ai_travel_agent.memory import get_redis

    get_redis().flushall()
    yield
