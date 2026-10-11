import re
from dataclasses import dataclass, field

_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


@dataclass
class FileChange:
    path: str                      # new path (old path for deleted files)
    change_type: str               # added | modified | renamed | deleted
    old_path: str | None = None
    new_ranges: list[tuple[int, int]] = field(default_factory=list)  # changed lines, new file
    old_ranges: list[tuple[int, int]] = field(default_factory=list)  # changed lines, old file


def _strip(p: str) -> str | None:
    p = p.split("\t")[0]
    if p == "/dev/null":
        return None
    return p[2:] if p[:2] in ("a/", "b/") else p


def parse_unified_diff(text: str) -> list[FileChange]:
    """Parse `git diff --unified=0 -M` output."""
    lines = text.splitlines()
    blocks: list[dict] = []
    cur: dict | None = None
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        if line.startswith("diff --git "):
            cur = {"old": None, "new": None, "type": "modified", "new_ranges": [], "old_ranges": []}
            blocks.append(cur)
            continue
        if cur is None:
            continue
        m = _HUNK.match(line)
        if m:
            a = int(m.group(1))
            b = int(m.group(2)) if m.group(2) is not None else 1
            c = int(m.group(3))
            d = int(m.group(4)) if m.group(4) is not None else 1
            if b > 0:
                cur["old_ranges"].append((a, a + b - 1))
            if d > 0:
                cur["new_ranges"].append((c, c + d - 1))
            else:  # pure deletion: the point where lines were removed
                s = max(c, 1)
                cur["new_ranges"].append((s, s + 1))
            # Consume hunk body so content lines like "--- x" are not read as headers.
            remaining = b + d
            while remaining > 0 and i < len(lines):
                content = lines[i]
                i += 1
                if content.startswith("\\"):
                    continue
                remaining -= 1
            continue
        if line.startswith("new file mode"):
            cur["type"] = "added"
        elif line.startswith("deleted file mode"):
            cur["type"] = "deleted"
        elif line.startswith("rename from "):
            cur["old"] = line[len("rename from "):]
            cur["type"] = "renamed"
        elif line.startswith("rename to "):
            cur["new"] = line[len("rename to "):]
        elif line.startswith("--- "):
            p = _strip(line[4:])
            if p is not None:
                cur["old"] = p
        elif line.startswith("+++ "):
            p = _strip(line[4:])
            if p is not None:
                cur["new"] = p

    changes: list[FileChange] = []
    for b in blocks:
        t, old, new = b["type"], b["old"], b["new"]
        path = old if t == "deleted" else (new or old)
        if not path:
            continue
        changes.append(FileChange(
            path=path,
            change_type=t,
            old_path=old if t in ("renamed", "modified", "deleted") else None,
            new_ranges=[] if t == "deleted" else b["new_ranges"],
            old_ranges=[] if t == "added" else b["old_ranges"],
        ))
    return changes
