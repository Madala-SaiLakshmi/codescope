import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import get_db
from app.main import app
from app.models.user import User
from app.security import create_token
from app.services.analysis_service import AnalysisService
from tests.auth_helpers import auth_headers

REPO = {"name": "demo", "source_url": "https://github.com/o/r"}


@pytest.fixture
def client(db):
    def override():
        yield db

    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_register_login_me_and_password_is_hashed(client, db):
    h = auth_headers(client)
    me = client.get("/api/auth/me", headers=h)
    assert me.status_code == 200 and me.json()["email"] == "user@example.com"
    stored = db.scalar(select(User)).password_hash
    assert stored.startswith("$argon2") and "correct-horse-1" not in stored


def test_duplicate_and_invalid_registration(client):
    body = {"email": "a@example.com", "password": "correct-horse-1"}
    assert client.post("/api/auth/register", json=body).status_code == 201
    assert client.post("/api/auth/register", json=body).status_code == 409
    assert client.post("/api/auth/register", json={"email": "b@example.com", "password": "short"}).status_code == 422
    assert client.post("/api/auth/register", json={"email": "not-an-email", "password": "correct-horse-1"}).status_code == 422


def test_bad_logins_look_identical(client):
    client.post("/api/auth/register", json={"email": "a@example.com", "password": "correct-horse-1"})
    wrong = client.post("/api/auth/login", json={"email": "a@example.com", "password": "wrong-password"})
    unknown = client.post("/api/auth/login", json={"email": "who@example.com", "password": "wrong-password"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


@pytest.mark.parametrize("path", [
    "/api/repositories", "/api/auth/me", "/api/analyses/1", "/api/impact-reports/1",
    "/api/repositories/1/analyses", "/api/repositories/1/impact-reports",
])
def test_endpoints_require_authentication(client, path):
    assert client.get(path).status_code == 401


def test_invalid_and_expired_tokens_rejected(client):
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401
    h = auth_headers(client)
    uid = client.get("/api/auth/me", headers=h).json()["id"]
    expired = {"Authorization": f"Bearer {create_token(uid, minutes=-1)}"}
    assert client.get("/api/auth/me", headers=expired).status_code == 401


def test_users_cannot_access_each_others_data(client, db):
    a = auth_headers(client, "a@example.com")
    b = auth_headers(client, "b@example.com")
    repo_id = client.post("/api/repositories", json=REPO, headers=a).json()["id"]
    job = AnalysisService(db).create_job(repo_id)

    assert [r["id"] for r in client.get("/api/repositories", headers=a).json()] == [repo_id]
    assert client.get("/api/repositories", headers=b).json() == []

    assert client.get(f"/api/analyses/{job.id}", headers=a).status_code == 200
    for method, path in [
        ("get", f"/api/analyses/{job.id}"),
        ("get", f"/api/analyses/{job.id}/graph"),
        ("get", f"/api/repositories/{repo_id}/analyses"),
        ("post", f"/api/repositories/{repo_id}/analyses"),
        ("get", f"/api/repositories/{repo_id}/impact-reports"),
    ]:
        assert getattr(client, method)(path, headers=b).status_code == 404, path
    r = client.post(f"/api/repositories/{repo_id}/impact-reports", json={"base": "HEAD~1"}, headers=b)
    assert r.status_code == 404
