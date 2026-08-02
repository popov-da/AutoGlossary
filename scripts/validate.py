#!/usr/bin/env python3
"""Validate domain CSVs, master termbase, and consumer exports."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MASTER_FIELDS = [
    "source",
    "target_preferred",
    "status",
    "category",
    "source_id",
    "confidence",
    "source_document",
    "term_type",
    "alternate_targets",
]
CONSUMER_FIELDS = ["source", "target_preferred", "status"]

ALIASES = {
    "source": ("source", "term_en", "english term", "term"),
    "target_preferred": (
        "target_preferred",
        "term_ru_candidate",
        "russian candidate",
        "target",
        "translation",
    ),
    "status": ("status", "translation_status"),
    "confidence": ("confidence",),
}

MASTER_STATUSES = {"candidate", "reviewed", "approved", "deprecated"}
DOMAIN_STATUSES = MASTER_STATUSES | {"rejected"}
CONFIDENCE = {"high", "medium", "low"}


def clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def normalized_headers(fieldnames: list[str] | None) -> dict[str, str]:
    return {clean(name).casefold(): name for name in fieldnames or [] if name is not None}


def resolve_column(fieldnames: list[str] | None, canonical: str) -> str | None:
    headers = normalized_headers(fieldnames)
    for alias in ALIASES[canonical]:
        actual = headers.get(alias.casefold())
        if actual is not None:
            return actual
    return None


def validate_csv(path: Path, kind: str) -> list[str]:
    errors: list[str] = []
    seen: dict[str, int] = {}

    try:
        stream = path.open(encoding="utf-8-sig", newline="")
    except UnicodeDecodeError as exc:
        return [f"invalid UTF-8: {exc}"]

    with stream:
        reader = csv.DictReader(stream)
        fields = list(reader.fieldnames or [])

        if kind == "consumer":
            if fields != CONSUMER_FIELDS:
                return [f"expected exactly {CONSUMER_FIELDS}, got {fields}"]
            source_col = "source"
            target_col = "target_preferred"
            status_col = "status"
            confidence_col = None
            allowed_statuses = MASTER_STATUSES
        elif kind == "master":
            missing = [field for field in MASTER_FIELDS if field not in fields]
            if missing:
                return [f"missing master columns: {', '.join(missing)}"]
            source_col = "source"
            target_col = "target_preferred"
            status_col = "status"
            confidence_col = "confidence"
            allowed_statuses = MASTER_STATUSES
        else:
            source_col = resolve_column(fields, "source")
            target_col = resolve_column(fields, "target_preferred")
            status_col = resolve_column(fields, "status")
            missing = [
                name
                for name, column in (
                    ("source/term_en", source_col),
                    ("target_preferred/term_ru_candidate", target_col),
                    ("status/translation_status", status_col),
                )
                if column is None
            ]
            if missing:
                return [f"missing domain columns (including aliases): {', '.join(missing)}"]
            confidence_col = resolve_column(fields, "confidence")
            allowed_statuses = DOMAIN_STATUSES

        for line, row in enumerate(reader, start=2):
            source = clean(row.get(source_col or "", ""))
            target = clean(row.get(target_col or "", ""))
            status = clean(row.get(status_col or "", "")).casefold()

            if not source:
                errors.append(f"line {line}: empty source")
                continue
            if kind in {"master", "consumer"} and source.endswith("."):
                errors.append(f"line {line}: source ends with a period")
            if not target:
                errors.append(f"line {line}: empty target_preferred")
            if status not in allowed_statuses:
                errors.append(f"line {line}: invalid status {status!r}")

            # Domain files may intentionally contain homonyms or contextual variants.
            # Uniqueness by casefold is required only in the generated master and
            # consumer exports.
            if kind in {"master", "consumer"}:
                normalized = source.casefold()
                if normalized in seen:
                    errors.append(
                        f"line {line}: duplicate source (casefold), first on line {seen[normalized]}"
                    )
                else:
                    seen[normalized] = line

            if confidence_col:
                confidence = clean(row.get(confidence_col, "")).casefold()
                if confidence and confidence not in CONFIDENCE:
                    errors.append(f"line {line}: invalid confidence {confidence!r}")
                if kind == "master" and not confidence:
                    errors.append(f"line {line}: empty confidence")

            if kind == "master" and ".dita" in clean(
                row.get("source_document", "")
            ).casefold():
                errors.append(
                    f"line {line}: private DITA filename leaked into source_document"
                )

    return errors


def discover() -> list[tuple[Path, str]]:
    files: list[tuple[Path, str]] = []
    for directory in (ROOT / "data", ROOT / "imports"):
        if directory.exists():
            for path in sorted(directory.glob("*.csv")):
                kind = "master" if path.name == "termbase.csv" else "domain"
                files.append((path, kind))

    export_dir = ROOT / "exports"
    if export_dir.exists():
        files.extend(
            (path, "consumer")
            for path in sorted(export_dir.glob("consumer-*.csv"))
        )
    return files


def classify(path: Path) -> str:
    if path.parent.name == "exports":
        return "consumer"
    if path.name == "termbase.csv":
        return "master"
    return "domain"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", type=Path)
    args = parser.parse_args()
    targets = [(path, classify(path)) for path in args.paths] or discover()

    failed = False
    for path, kind in targets:
        errors = validate_csv(path, kind)
        display = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
        if errors:
            failed = True
            print(f"Validation failed: {display}")
            for error in errors:
                print(f"- {error}")
        else:
            print(f"Validation passed: {display}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
