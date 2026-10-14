import os
import tempfile

# Set before importing any application module; tests never touch deployment data.
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="tg-dashboard-tests-")
os.environ["ADMIN_PASSWORD"] = "test-password-long-enough"

import pytest
from fastapi.testclient import TestClient

from backend.app.db import Account, Run, Session, Task
from backend.app.main import app
from backend.app.security import attempts


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def admin(client):
    attempts.clear()
    response = client.post("/api/panel/login", json={"password": "test-password-long-enough"})
    assert response.status_code == 200
    yield client


@pytest.fixture
def account():
    from backend.app.security import encrypt

    with Session() as db:
        a = Account(
            name="test account",
            phone="+8613800000000",
            username="test",
            user_id="987654321",
            session=encrypt("test-session"),
            api_id=1234,
            api_hash=encrypt("a" * 32),
        )
        db.add(a)
        db.commit()
        account_id = a.id
    yield account_id
    with Session() as db:
        db.query(Run).delete()
        db.query(Task).delete()
        db.query(Account).delete()
        db.commit()
