#!/usr/bin/env python3
"""Replace private DITA filenames in committed CSV metadata with corpus labels."""

from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_DOC_RE = re.compile(r"\.dita\b", re.IGNORECASE)


def clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def public_label(source_id: str, fallback: str) -> str:
    source_id = clean(source_id)
    if source_id:
        return source_id.replace("_D2_CORPUS", "_CORPUS").replace("_D2", "_CORPUS")
    return fallback


def sanitize(path: Path) -> bool:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fieldnames = list(reader.fieldnames or [])
        if "source_document" not in fieldnames:
            return False
        rows = list(reader)

    changed = False
    for row in rows:
        supplied = clean(row.get("source_document", ""))
        if PRIVATE_DOC_RE.search(supplied):
            row["source_document"] = public_label(
                row.get("source_id", ""), path.name
            )
            changed = True

    if changed:
        with path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    return changed


def main() -> int:
    changed: list[Path] = []
    for directory in (ROOT / "data", ROOT / "imports"):
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.csv")):
            if path.name == "termbase.csv":
                continue
            if sanitize(path):
                changed.append(path)

    for path in changed:
        print(f"Sanitized {path.relative_to(ROOT)}")
    print(f"Sanitized files: {len(changed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
