import pytest
from fastapi.testclient import TestClient

from app import ratelimit
from app.database import get_db
from app.main import app
from tests.auth_helpers import auth_headers


@pytest.fixture(autouse=True)
def fresh_limiters():
    for lim in (ratelimit.login_ip_limiter, ratelimit.login_email_limiter,
                ratelimit.register_limiter, ratelimit.heavy_limiter):
        lim.reset()
    yield


@pytest.fixture
def client(db):
    def override():
        yield db

    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_login_is_rate_limited_per_email(client):
    client.post("/api/auth/register", json={"email": "a@example.com", "password": "correct-horse-1"})
    codes = [client.post("/api/auth/login",
                         json={"email": "a@example.com", "password": "wrong-password"}).status_code
             for _ in range(7)]
    assert codes[:5] == [401] * 5
    assert codes[5] == 429
    r = client.post("/api/auth/login", json={"email": "a@example.com", "password": "wrong-password"})
    assert r.status_code == 429 and int(r.headers["Retry-After"]) >= 1


def test_registration_is_rate_limited(client):
    codes = [client.post("/api/auth/register",
                         json={"email": f"u{i}@example.com", "password": "correct-horse-1"}).status_code
             for i in range(12)]
    assert codes.count(201) == 10 and codes[-1] == 429


def test_oversized_body_is_rejected(client):
    big = {"name": "x" * 100_000, "source_url": "https://github.com/o/r"}
    h = auth_headers(client)
    r = client.post("/api/repositories", json=big, headers=h)
    assert r.status_code == 413
    assert client.get("/api/health").status_code == 200


def test_heavy_endpoint_limited_per_user(client, monkeypatch):
    monkeypatch.setattr("app.services.analysis_service.AnalysisService.run",
                        lambda self, job_id: self.db.get(
                            __import__("app.models.analysis", fromlist=["AnalysisJob"]).AnalysisJob, job_id))
    h = auth_headers(client)
    repo_id = client.post("/api/repositories",
                          json={"name": "d", "source_url": "https://github.com/o/r"}, headers=h).json()["id"]
    codes = [client.post(f"/api/repositories/{repo_id}/analyses", headers=h).status_code
             for _ in range(12)]
    assert codes[:10] == [201] * 10 and codes[10] == 429
