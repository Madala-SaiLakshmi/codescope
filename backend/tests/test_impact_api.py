import subprocess

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app

FILES_1 = {
    "app/a/A.java": "package app.a;\nimport app.b.B;\npublic class A {\n  void run() { B.help(); }\n}\n",
    "app/b/B.java": "package app.b;\npublic class B {\n  static void help() {\n  }\n}\n",
}
B_2 = "package app.b;\npublic class B {\n  static void help() {\n    int x = 1;\n  }\n}\n"


def git(repo, *args):
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false",
         "-C", str(repo), *args],
        check=True, capture_output=True,
    )


def fake_clone(url, dest, branch=None, timeout=0, max_bytes=0, depth=1):
    dest.mkdir(parents=True)
    git(dest, "init", "-q")
    for rel, src in FILES_1.items():
        p = dest / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(src)
    git(dest, "add", "-A")
    git(dest, "commit", "-q", "-m", "one")
    (dest / "app/b/B.java").write_text(B_2)
    git(dest, "add", "-A")
    git(dest, "commit", "-q", "-m", "two")
    return "unused"


@pytest.fixture
def client(db, monkeypatch):
    def override():
        yield db

    app.dependency_overrides[get_db] = override
    monkeypatch.setattr("app.services.impact_service.clone_repository", fake_clone)
    yield TestClient(app)
    app.dependency_overrides.clear()


def register(client) -> int:
    r = client.post("/api/repositories",
                    json={"name": "demo", "source_url": "https://github.com/o/r"})
    return r.json()["id"]


def test_full_report(client):
    repo_id = register(client)
    r = client.post(f"/api/repositories/{repo_id}/impact-reports", json={"base": "HEAD~1"})
    assert r.status_code == 201
    summary = r.json()
    assert summary["status"] == "succeeded"
    assert summary["changed_file_count"] == 1
    assert summary["base_sha"] != summary["target_sha"]

    d = client.get(f"/api/impact-reports/{summary['id']}").json()
    assert [(f["path"], f["change_type"]) for f in d["files"]] == [("app/b/B.java", "modified")]
    assert [(c["qualified_name"], c["change"]) for c in d["changed"]] == [("app.b.B.help()", "modified")]
    assert len(d["affected"]) == 1
    a = d["affected"][0]
    assert a["qualified_name"] == "app.a.A.run()" and a["distance"] == 1 and a["certain"]
    assert a["via"] == ["app.a.A.run()", "app.b.B.help()"]
    assert d["uncertainties"] == []

    listed = client.get(f"/api/repositories/{repo_id}/impact-reports").json()
    assert [x["id"] for x in listed] == [summary["id"]]
    assert len(client.get(f"/api/repositories/{repo_id}/analyses").json()) == 2


@pytest.mark.parametrize("base,message", [
    ("--output=x", "Invalid revision name"),
    ("no-such-rev", "Unknown revision: no-such-rev"),
])
def test_bad_revisions_fail_safely(client, base, message):
    repo_id = register(client)
    r = client.post(f"/api/repositories/{repo_id}/impact-reports", json={"base": base})
    assert r.status_code == 201
    assert r.json()["status"] == "failed" and r.json()["error_summary"] == message


def test_not_found(client):
    assert client.post("/api/repositories/999/impact-reports", json={"base": "HEAD~1"}).status_code == 404
    assert client.get("/api/impact-reports/999").status_code == 404


def test_report_includes_risk_and_tests(client):
    repo_id = register(client)
    r = client.post(f"/api/repositories/{repo_id}/impact-reports", json={"base": "HEAD~1"}).json()
    d = client.get(f"/api/impact-reports/{r['id']}").json()
    assert d["risk_score"] is not None and d["risk_level"] in {"low", "medium", "high", "critical"}
    assert len(d["risk_factors"]) == 6
    assert abs(d["risk_score"] - sum(f["points"] for f in d["risk_factors"])) < 0.2
    assert d["tests"] == []  # the sample repo has no test files
