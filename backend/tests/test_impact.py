import subprocess

import pytest

from app.engine.graph import DependencyGraph
from app.engine.impact import compute_impact
from app.engine.resolver import Resolver
from app.parser.scanner import scan_java_files
from app.services.git_diff import export_revision, get_changes

BASE = {
    "app/a/A.java": "package app.a;\nimport app.b.B;\npublic class A {\n  void run() { B.help(); }\n}\n",
    "app/b/B.java": "package app.b;\npublic class B {\n  static void help() {\n  }\n  static void other() {}\n}\n",
    "app/c/C.java": "package app.c;\nimport app.a.A;\npublic class C {\n  void f() { A a = new A(); a.run(); }\n}\n",
    "app/d/D.java": "package app.d;\nclass D {\n  void g() {}\n}\n",
    "app/e/E.java": "package app.e;\nimport app.b.B;\npublic class E {\n  void h() { B.other(); }\n}\n",
    "app/f/F.java": "package app.f;\npublic class F {\n  void z() {}\n}\n",
    "app/g/G.java": "package app.g;\nimport app.f.F;\npublic class G {\n  void y() { F f = new F(); f.z(); }\n}\n",
}


def git(repo, *args):
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false",
         "-C", str(repo), *args],
        check=True, capture_output=True,
    )


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"
    r.mkdir()
    git(r, "init", "-q")
    for rel, src in BASE.items():
        p = r / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(src)
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "base")
    git(r, "tag", "base")

    # B.help gets a new line in its body; A gets a new import; F is deleted; D is renamed.
    (r / "app/b/B.java").write_text(
        "package app.b;\npublic class B {\n  static void help() {\n    int x = 1;\n  }\n  static void other() {}\n}\n")
    (r / "app/a/A.java").write_text(
        "package app.a;\nimport app.b.B;\nimport java.util.List;\npublic class A {\n  void run() { B.help(); }\n}\n")
    (r / "app/f/F.java").unlink()
    (r / "app/d/D.java").rename(r / "app/d/Dd.java")
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "target")
    git(r, "tag", "target")
    return r


def analyze(repo, tmp_path):
    export_revision(repo, "base", tmp_path / "b")
    export_revision(repo, "target", tmp_path / "t")
    bs, ts = scan_java_files(tmp_path / "b"), scan_java_files(tmp_path / "t")
    bg = DependencyGraph.build(bs.files, Resolver(bs.files).resolve())
    tg = DependencyGraph.build(ts.files, Resolver(ts.files).resolve())
    changes = get_changes(repo, "base", "target")
    return changes, compute_impact(changes, ts.files, tg, bs.files, bg)


def test_file_changes(repo, tmp_path):
    changes, _ = analyze(repo, tmp_path)
    types = {c.path: c.change_type for c in changes}
    assert types == {
        "app/a/A.java": "modified",
        "app/b/B.java": "modified",
        "app/f/F.java": "deleted",
        "app/d/Dd.java": "renamed",
    }


def test_changed_symbols(repo, tmp_path):
    _, result = analyze(repo, tmp_path)
    got = {(c.qualified_name, c.change) for c in result.changed}
    assert got == {
        ("app.b.B.help()", "modified"),
        ("app.f.F", "removed"),
        ("app.f.F.z()", "removed"),
    }


def test_affected_symbols_and_paths(repo, tmp_path):
    _, result = analyze(repo, tmp_path)
    by_name = {a.qualified_name: a for a in result.affected}
    assert set(by_name) == {"app.a.A.run()", "app.c.C.f()", "app.g.G.y()"}
    assert by_name["app.a.A.run()"].distance == 1
    assert by_name["app.c.C.f()"].distance == 2
    assert by_name["app.c.C.f()"].via == ("app.c.C.f()", "app.a.A.run()", "app.b.B.help()")
    assert by_name["app.g.G.y()"].root in {"app.f.F", "app.f.F.z()"}  # found via the base graph
    assert all(a.certain for a in result.affected)


def test_unmapped_import_change_is_reported(repo, tmp_path):
    _, result = analyze(repo, tmp_path)
    assert any(u.path == "app/a/A.java" and "outside any class or method" in u.message
               for u in result.uncertainties)
