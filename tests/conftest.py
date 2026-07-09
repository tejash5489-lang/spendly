import importlib
import sys

import pytest


@pytest.fixture
def app_module(monkeypatch, tmp_path):
    """Import (or reload) app.py against an isolated, temporary SQLite file.

    Patches database.db.DB_PATH *before* app is (re)imported so the
    module-level init_db()/seed_db() calls in app.py run against the temp
    file instead of the real dev database (expense-tracker/spendly.db).
    """
    db_path = tmp_path / "test_spendly.db"
    monkeypatch.setattr("database.db.DB_PATH", str(db_path))

    if "app" in sys.modules:
        module = importlib.reload(sys.modules["app"])
    else:
        import app as module  # noqa: F401

    module.app.config["TESTING"] = True
    yield module


@pytest.fixture
def client(app_module):
    """A Flask test client backed by a fresh, seeded temp database.

    app.py's module-level seed_db() call has already run by the time this
    fixture yields, so the demo user ("Demo User" / demo@spendly.com, id=1)
    and its sample expenses exist unless a test clears them.
    """
    with app_module.app.test_client() as test_client:
        yield test_client


@pytest.fixture
def logged_in_client(client):
    """Test client with session["user_id"] set to the seeded demo user (id=1)."""
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["user_name"] = "Demo User"
    return client
