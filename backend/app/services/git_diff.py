import io
import os
import re
import subprocess
import tarfile
from pathlib import Path

from app.engine.changes import FileChange, parse_unified_diff
from app.services.git_service import GitError

_REV_RE = re.compile(r"^[A-Za-z0-9._/~^-]{1,100}$")


def validate_revision(rev: str) -> str:
    if not _REV_RE.fullmatch(rev) or rev.startswith("-") or ".." in rev:
        raise GitError("Invalid revision name")
    return rev


def _git(repo: Path, *args: str, timeout: int = 60) -> bytes:
    cmd = [
        "git", "-c", "core.hooksPath=/dev/null", "-c", "core.quotePath=false",
        "-C", str(repo), *args,
    ]
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    try:
        return subprocess.run(cmd, capture_output=True, timeout=timeout,
                              env=env, check=True).stdout
    except subprocess.TimeoutExpired:
        raise GitError("Git operation timed out")
    except subprocess.CalledProcessError:
        raise GitError("Git operation failed")


def resolve_revision(repo: Path, rev: str) -> str:
    validate_revision(rev)
    try:
        out = _git(repo, "rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}")
    except GitError:
        raise GitError(f"Unknown revision: {rev}")
    return out.decode().strip()


def get_changes(repo: Path, base: str, target: str, max_files: int = 2000) -> list[FileChange]:
    base_sha = resolve_revision(repo, base)
    target_sha = resolve_revision(repo, target)
    out = _git(
        repo, "diff", "--no-color", "--no-ext-diff", "--no-textconv", "-M", "--unified=0",
        "--src-prefix=a/", "--dst-prefix=b/", base_sha, target_sha, "--",
        timeout=120,
    )
    changes = parse_unified_diff(out.decode("utf-8", errors="replace"))
    if len(changes) > max_files:
        raise GitError("Too many changed files")
    return changes


def export_revision(repo: Path, rev: str, dest: Path, max_bytes: int = 200 * 1024 * 1024) -> str:
    """Write the files of a revision into dest. Nothing is executed; symlinks are skipped."""
    sha = resolve_revision(repo, rev)
    data = _git(repo, "archive", "--format=tar", sha, timeout=120)
    if len(data) > max_bytes:
        raise GitError("Repository is too large")
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(data)) as tf:
        members = [m for m in tf.getmembers() if m.isfile() or m.isdir()]
        tf.extractall(dest, members=members, filter="data")
    return sha
