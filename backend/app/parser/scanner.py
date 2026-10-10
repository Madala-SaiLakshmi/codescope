import os
from pathlib import Path

from app.parser.java_parser import JavaParser
from app.parser.models import ScanResult

SKIP_DIRS = {".git", "node_modules", "target", "build", "out", ".gradle", ".idea"}


def scan_java_files(
    root: Path, max_files: int = 5000, max_file_bytes: int = 1_000_000
) -> ScanResult:
    root = root.resolve()
    parser = JavaParser()
    result = ScanResult()

    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for filename in sorted(filenames):
            if not filename.endswith(".java"):
                continue
            file_path = Path(dirpath) / filename
            rel = file_path.relative_to(root).as_posix()

            if file_path.is_symlink():
                result.skipped.append((rel, "symlink"))
                continue
            if not file_path.resolve().is_relative_to(root):
                result.skipped.append((rel, "outside repository root"))
                continue
            if file_path.stat().st_size > max_file_bytes:
                result.skipped.append((rel, "file too large"))
                continue
            if len(result.files) >= max_files:
                raise ValueError(f"Repository has more than {max_files} Java files")

            result.files.append(parser.parse_source(file_path.read_bytes(), rel))

    return result