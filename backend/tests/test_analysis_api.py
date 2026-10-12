import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from tests.auth_helpers import login
from app.services.git_service import GitError
from tests.sample_repo import write_sample

HELP = "app.b.B.help()"


@pytest.fixture
def client(db, monkeypatch):
    def override():
        yield db

    def fake_clone(url, dest, branch=None, timeout=0, max_bytes=0, depth=1):
        write_sample(dest)
        return "abc123"

    app.dependency_overrides[get_db] = override
    monkeypatch.setattr("app.services.analysis_service.clone_repository", fake_clone)
    c = TestClient(app)
    login(c)
    yield c
    app.dependency_overrides.clear()


def register(client) -> int:
    r = client.post("/api/repositories",
                    json={"name": "demo", "source_url": "https://github.com/o/r"})
    assert r.status_code == 201
    return r.json()["id"]


def test_full_flow(client):
    repo_id = register(client)
    r = client.post(f"/api/repositories/{repo_id}/analyses")
    assert r.status_code == 201
    job = r.json()
    assert job["status"] == "succeeded" and job["revision"] == "abc123"

    assert client.get(f"/api/analyses/{job['id']}").json()["file_count"] == 3
    assert [j["id"] for j in client.get(f"/api/repositories/{repo_id}/analyses").json()] == [job["id"]]

    graph = client.get(f"/api/analyses/{job['id']}/graph").json()
    assert "app.a.A" in {n["id"] for n in graph["nodes"]}
    assert any(e["source"] == "app.a.A.run()" and e["target"] == HELP for e in graph["edges"])

    types = client.get(f"/api/analyses/{job['id']}/graph", params={"level": "type"}).json()
    assert all(n["kind"] in ("class", "interface", "enum", "record") for n in types["nodes"])

    dep = client.get(f"/api/analyses/{job['id']}/dependents",
                     params={"symbol": HELP, "transitive": True}).json()
    assert dep["items"] == ["app.a.A.run()", "app.c.C.f()"]

    down = client.get(f"/api/analyses/{job['id']}/dependencies", params={"symbol": "app.c.C.f()"}).json()
    assert down["items"] == [HELP]


def test_unknown_ids_and_symbols(client):
    assert client.get("/api/analyses/999").status_code == 404
    assert client.post("/api/repositories/999/analyses").status_code == 404
    repo_id = register(client)
    job = client.post(f"/api/repositories/{repo_id}/analyses").json()
    r = client.get(f"/api/analyses/{job['id']}/dependents", params={"symbol": "no.Such"})
    assert r.status_code == 404


def test_failed_clone_marks_job_failed_and_blocks_graph(client, monkeypatch):
    def boom(*args, **kwargs):
        raise GitError("Could not clone the repository (check the URL and branch)")

    monkeypatch.setattr("app.services.analysis_service.clone_repository", boom)
    repo_id = register(client)
    job = client.post(f"/api/repositories/{repo_id}/analyses").json()
    assert job["status"] == "failed"
    assert "Could not clone" in job["error_summary"]
    assert client.get(f"/api/analyses/{job['id']}/graph").status_code == 409
