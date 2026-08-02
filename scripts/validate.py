#!/usr/bin/env python3
"""Validate domain CSVs, master termbase, reports, and consumer exports."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER_REQUIRED = {
    "source", "target_preferred", "status", "category", "source_id",
    "confidence", "source_document", "term_type", "alternate_targets",
}
DOMAIN_MINIMUM = {"source", "target_preferred", "status"}
CONSUMER_FIELDS = ["source", "target_preferred", "status"]
MASTER_STATUSES = {"candidate", "reviewed", "approved", "deprecated"}
DOMAIN_STATUSES = MASTER_STATUSES | {"rejected"}
CONFIDENCE = {"high", "medium", "low"}


def clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def validate_csv(path: Path, kind: str) -> list[str]:
    errors: list[str] = []
    seen: dict[str, int] = {}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = list(reader.fieldnames or [])
        field_set = set(fields)
        if kind == "consumer":
            if fields != CONSUMER_FIELDS:
                return [f"expected exactly {CONSUMER_FIELDS}, got {fields}"]
            allowed_statuses = MASTER_STATUSES
        elif kind == "master":
            missing = MASTER_REQUIRED - field_set
            if missing:
                return [f"missing master columns: {', '.join(sorted(missing))}"]
            allowed_statuses = MASTER_STATUSES
        else:
            missing = DOMAIN_MINIMUM - field_set
            if missing:
                return [f"missing domain columns: {', '.join(sorted(missing))}"]
            allowed_statuses = DOMAIN_STATUSES

        for line, row in enumerate(reader, start=2):
            source = clean(row.get("source", ""))
            target = clean(row.get("target_preferred", ""))
            status = clean(row.get("status", "")).casefold()
            if not source:
                errors.append(f"line {line}: empty source")
                continue
            if source.endswith("."):
                errors.append(f"line {line}: source ends with a period")
            if not target:
                errors.append(f"line {line}: empty target_preferred")
            if status not in allowed_statuses:
                errors.append(f"line {line}: invalid status {status!r}")
            normalized = source.casefold()
            if normalized in seen:
                errors.append(f"line {line}: duplicate source (casefold), first on line {seen[normalized]}")
            else:
                seen[normalized] = line
            if kind == "master":
                confidence = clean(row.get("confidence", "")).casefold()
                if confidence not in CONFIDENCE:
                    errors.append(f"line {line}: invalid confidence {confidence!r}")
                if ".dita" in clean(row.get("source_document", "")).casefold():
                    errors.append(f"line {line}: private DITA filename leaked into source_document")
            if kind == "consumer" and status == "rejected":
                errors.append(f"line {line}: rejected is forbidden in consumer export")
    return errors


def discover() -> list[tuple[Path, str]]:
    files: list[tuple[Path, str]] = []
    for directory in (ROOT / "data", ROOT / "imports"):
        if directory.exists():
            for path in sorted(directory.glob("*.csv")):
                files.append((path, "master" if path.name == "termbase.csv" else "domain"))
    export_dir = ROOT / "exports"
    if export_dir.exists():
        files.extend((path, "consumer") for path in sorted(export_dir.glob("consumer-*.csv")))
    return files


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", type=Path)
    args = parser.parse_args()
    targets = [(path, "consumer" if path.parent.name == "exports" else "master" if path.name == "termbase.csv" else "domain") for path in args.paths] or discover()

    failed = False
    for path, kind in targets:
        errors = validate_csv(path, kind)
        if errors:
            failed = True
            print(f"Validation failed: {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}")
            for error in errors:
                print(f"- {error}")
        else:
            print(f"Validation passed: {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
