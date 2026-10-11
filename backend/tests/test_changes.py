import pytest

from app.engine.changes import parse_unified_diff
from app.services.git_diff import GitError, validate_revision

DIFF = """diff --git a/X.java b/X.java
index 111..222 100644
--- a/X.java
+++ b/X.java
@@ -2,2 +2,1 @@
--- removed comment
-int a;
+int b;
diff --git a/New.java b/New.java
new file mode 100644
--- /dev/null
+++ b/New.java
@@ -0,0 +1,3 @@
+a
+b
+c
diff --git a/Old.java b/Old.java
deleted file mode 100644
--- a/Old.java
+++ /dev/null
@@ -1,2 +0,0 @@
-x
-y
diff --git a/R1.java b/R2.java
similarity index 100%
rename from R1.java
rename to R2.java
diff --git a/Y.java b/Y.java
--- a/Y.java
+++ b/Y.java
@@ -5,2 +4,0 @@
-p
-q
"""


def test_parse_diff():
    by_path = {c.path: c for c in parse_unified_diff(DIFF)}
    x = by_path["X.java"]
    assert x.change_type == "modified"
    assert x.new_ranges == [(2, 2)] and x.old_ranges == [(2, 3)]
    n = by_path["New.java"]
    assert n.change_type == "added" and n.new_ranges == [(1, 3)] and n.old_ranges == []
    o = by_path["Old.java"]
    assert o.change_type == "deleted" and o.new_ranges == []
    r = by_path["R2.java"]
    assert r.change_type == "renamed" and r.old_path == "R1.java"
    assert r.new_ranges == [] and r.old_ranges == []
    y = by_path["Y.java"]
    assert y.new_ranges == [(4, 5)] and y.old_ranges == [(5, 6)]


@pytest.mark.parametrize("rev", ["main", "v1.0", "feature/x", "abc123", "HEAD~1", "HEAD^"])
def test_valid_revisions(rev):
    assert validate_revision(rev) == rev


@pytest.mark.parametrize("rev", ["--output=x", "a..b", "", "x y", "a;b", "$(x)"])
def test_invalid_revisions(rev):
    with pytest.raises(GitError):
        validate_revision(rev)
