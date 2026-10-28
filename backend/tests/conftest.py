import os
import tempfile

os.environ["SESSION_SECRET"] = "test-secret-with-at-least-thirty-two-characters"
os.environ["DATABASE_URL"] = "sqlite:///" + tempfile.mktemp(suffix=".db")
os.environ["ALLOW_DEMO_LOGIN"] = "true"
os.environ["ANALYSIS_MODE"] = "demo"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def database():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def client():
    with TestClient(app, headers={"Origin": "http://localhost:3000"}) as c:
        yield c


@pytest.fixture
def logged_in(client):
    assert client.post("/auth/demo").status_code == 200
    return client
