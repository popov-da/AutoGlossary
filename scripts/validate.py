#!/usr/bin/env python3
"""Validate AutoGlossary CSV files."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

REQUIRED = {
    "id",
    "term_en",
    "term_ru_candidate",
    "category",
    "term_type",
    "source_id",
    "translation_status",
    "confidence",
    "source_url",
}
STATUSES = {"candidate", "approved", "rejected", "deprecated"}
CONFIDENCE = {"high", "medium", "low"}


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    ids: set[str] = set()
    meanings: dict[tuple[str, str, str], list[int]] = defaultdict(list)

    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        missing = REQUIRED - set(reader.fieldnames or [])
        if missing:
            return [f"Missing columns: {', '.join(sorted(missing))}"]

        for line, row in enumerate(reader, start=2):
            entry_id = row["id"].strip()
            if not entry_id:
                errors.append(f"line {line}: empty id")
            elif entry_id in ids:
                errors.append(f"line {line}: duplicate id {entry_id}")
            ids.add(entry_id)

            if not row["term_en"].strip():
                errors.append(f"line {line}: empty term_en")
            if row["translation_status"] not in STATUSES:
                errors.append(f"line {line}: invalid status {row['translation_status']!r}")
            if row["confidence"] not in CONFIDENCE:
                errors.append(f"line {line}: invalid confidence {row['confidence']!r}")
            if row["translation_status"] == "approved" and not row["term_ru_candidate"].strip():
                errors.append(f"line {line}: approved entry has no Russian term")

            key = (
                row["term_en"].strip().casefold(),
                row.get("category", "").strip().casefold(),
                row.get("term_type", "").strip().casefold(),
            )
            meanings[key].append(line)

    for key, lines in meanings.items():
        if len(lines) > 1:
            errors.append(f"duplicate meaning {key!r} on lines {lines}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file", type=Path)
    args = parser.parse_args()

    errors = validate(args.csv_file)
    if errors:
        print("Validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Validation passed: {args.csv_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
