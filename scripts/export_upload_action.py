"""Assemble the upload action as a stand-alone repository (action.yml at the root).

Usage: python scripts/export_upload_action.py DEST OWNER/REPO

DEST must not exist or must be empty. The Marketplace requires action.yml at the
root of its own public repository (docs/technical-guide.md §11.2); this copies
packages/upload-action into that layout. It does not create or push the repo.
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "packages" / "upload-action"
FILES = ("action.yml", "entrypoint.py", "LICENSE")


def export(dest: Path, repo: str) -> list[Path]:
    if not re.fullmatch(r"[A-Za-z0-9-]+/[A-Za-z0-9._-]+", repo):
        raise ValueError(f"expected OWNER/REPO, got {repo!r}")
    if dest.exists() and any(dest.iterdir()):
        raise ValueError(f"{dest} is not empty")
    dest.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        shutil.copy2(SOURCE / name, dest / name)
    shutil.copytree(
        SOURCE / "standalone",
        dest,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"),
    )
    readme = dest / "README.md"
    readme.write_text(readme.read_text(encoding="utf-8").replace("{{REPO}}", repo), "utf-8")
    return sorted(p.relative_to(dest) for p in dest.rglob("*") if p.is_file())


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        files = export(Path(argv[1]), argv[2])
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    for path in files:
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
