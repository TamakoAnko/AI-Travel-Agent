import os
from pathlib import Path

os.environ["EMBED_PROVIDER"] = "hash"
os.environ["DATABASE_PATH"] = "data/test_app.db"
os.environ["CHECKPOINT_PATH"] = "data/test_checkpoints.db"
os.environ.setdefault("APP_SECRET", "test-secret")

import pytest


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db():
    yield
    for name in ("test_app.db", "test_app.db-wal", "test_app.db-shm",
                 "test_checkpoints.db", "test_checkpoints.db-wal", "test_checkpoints.db-shm"):
        Path("data", name).unlink(missing_ok=True)
