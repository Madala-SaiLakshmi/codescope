import pytest

from app.services.git_service import (
    GitError,
    directory_size,
    new_workspace,
    remove_workspace,
    validate_branch,
    validate_clone_url,
)


@pytest.mark.parametrize("url", [
    "https://github.com/google/guava",
    "https://gitlab.com/owner/project.git",
])
def test_valid_urls(url):
    assert validate_clone_url(url) == url


@pytest.mark.parametrize("url", [
    "/etc/passwd",
    "file:///tmp/x",
    "http://github.com/o/r",
    "git@github.com:o/r.git",
    "ssh://git@github.com/o/r",
    "https://user:secret@github.com/o/r",
    "https://",
    "--upload-pack=evil",
    "ext::sh -c evil",
])
def test_invalid_urls(url):
    with pytest.raises(GitError):
        validate_clone_url(url)


@pytest.mark.parametrize("branch", ["main", "release/1.2", "feature_x-1"])
def test_valid_branches(branch):
    assert validate_branch(branch) == branch


@pytest.mark.parametrize("branch", ["--upload-pack=x", "a..b", "x y", "", "a;b"])
def test_invalid_branches(branch):
    with pytest.raises(GitError):
        validate_branch(branch)


def test_directory_size_ignores_symlinks(tmp_path):
    (tmp_path / "a.txt").write_text("12345")
    (tmp_path / "link").symlink_to(tmp_path / "a.txt")
    assert directory_size(tmp_path) == 5


def test_workspace_lifecycle(tmp_path):
    ws = new_workspace(tmp_path / "base")
    assert ws.is_dir() and ws.parent == tmp_path / "base"
    remove_workspace(ws)
    assert not ws.exists()
