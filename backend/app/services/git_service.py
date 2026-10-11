import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse


class GitError(Exception):
    """Raised with a message that is safe to show to users."""


_BRANCH_RE = re.compile(r"^[A-Za-z0-9._/-]{1,100}$")


def validate_clone_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise GitError("Only https:// repository URLs are allowed")
    if parsed.username or parsed.password:
        raise GitError("URLs with embedded credentials are not allowed")
    return url


def validate_branch(branch: str) -> str:
    if not _BRANCH_RE.fullmatch(branch) or branch.startswith("-") or ".." in branch:
        raise GitError("Invalid branch name")
    return branch


def directory_size(path: Path) -> int:
    total = 0
    for dirpath, _dirs, files in os.walk(path, followlinks=False):
        for name in files:
            p = Path(dirpath) / name
            if not p.is_symlink():
                total += p.stat().st_size
    return total


def new_workspace(base: Path) -> Path:
    """A fresh private directory for one analysis."""
    base.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="job-", dir=base))


def remove_workspace(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)


def clone_repository(
    url: str,
    dest: Path,
    branch: str | None = None,
    timeout: int = 120,
    max_bytes: int = 200 * 1024 * 1024,
    depth: int = 1,
) -> str:
    """Clone into dest (must not exist) and return the HEAD commit sha.

    Nothing from the repository is executed: hooks are disabled, only https is
    allowed, symlinks are written as plain files, submodules are not fetched.
    """
    validate_clone_url(url)
    cmd = [
        "git",
        "-c", "core.hooksPath=/dev/null",
        "-c", "protocol.allow=never",
        "-c", "protocol.https.allow=always",
        "-c", "core.symlinks=false",
        "clone", "--depth", str(depth), "--single-branch", "--no-tags",
    ]
    if branch:
        cmd += ["--branch", validate_branch(branch)]
    cmd += ["--", url, str(dest)]
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}

    try:
        subprocess.run(cmd, env=env, capture_output=True, text=True,
                       timeout=timeout, check=True)
    except subprocess.TimeoutExpired:
        shutil.rmtree(dest, ignore_errors=True)
        raise GitError("Clone timed out")
    except subprocess.CalledProcessError:
        shutil.rmtree(dest, ignore_errors=True)
        raise GitError("Could not clone the repository (check the URL and branch)")

    if directory_size(dest) > max_bytes:
        shutil.rmtree(dest, ignore_errors=True)
        raise GitError("Repository is too large")

    head = subprocess.run(
        ["git", "-C", str(dest), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    )
    return head.stdout.strip()
