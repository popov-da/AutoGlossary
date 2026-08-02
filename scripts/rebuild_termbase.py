#!/usr/bin/env python3
"""Build the single authoritative data/termbase.csv from repository CSV sources."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
IMPORT_DIR = ROOT / "imports"
OUTPUT = DATA_DIR / "termbase.csv"
CONFLICTS = ROOT / "reports" / "conflicts.csv"

FIELDS = [
    "source",
    "target_preferred",
    "status",
    "category",
    "source_id",
    "confidence",
    "source_document",
    "term_type",
]

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
    "category": ("category",),
    "source_id": ("source_id", "source id"),
    "confidence": ("confidence",),
    "source_document": ("source_document", "source document"),
    "term_type": ("term_type", "type", "term type"),
}

STATUS_SCORE = {"approved": 4, "candidate": 3, "deprecated": 2, "rejected": 1}
CONFIDENCE_SCORE = {"high": 3, "medium": 2, "low": 1}


def clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def normalize_key(value: str) -> str:
    return clean(value).casefold()


def pick(raw: dict[str, str], field: str) -> str:
    lowered = {clean(k).casefold(): clean(v) for k, v in raw.items() if k is not None}
    for alias in ALIASES[field]:
        value = lowered.get(alias.casefold(), "")
        if value:
            return value
    return ""


def read_rows(path: Path) -> list[dict[str, str]]:
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if not reader.fieldnames:
                return []
            result: list[dict[str, str]] = []
            for raw in reader:
                row = {field: pick(raw, field) for field in FIELDS}
                if not row["source"] or not row["target_preferred"]:
                    continue
                row["status"] = row["status"] or "candidate"
                row["confidence"] = row["confidence"] or "medium"
                row["category"] = row["category"] or "uncategorized"
                row["source_id"] = row["source_id"] or path.stem.upper()
                row["source_document"] = row["source_document"] or path.name
                row["term_type"] = row["term_type"] or "term"
                result.append(row)
            return result
    except (UnicodeDecodeError, csv.Error):
        return []


def rank(row: dict[str, str]) -> tuple[int, int, int]:
    return (
        STATUS_SCORE.get(row["status"].casefold(), 0),
        CONFIDENCE_SCORE.get(row["confidence"].casefold(), 0),
        len(row["source_document"]),
    )


def merge_values(left: str, right: str) -> str:
    values = [clean(item) for item in f"{left} | {right}".split("|") if clean(item)]
    return " | ".join(dict.fromkeys(values))


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    CONFLICTS.parent.mkdir(exist_ok=True)

    inputs = [OUTPUT]
    inputs += sorted(path for path in DATA_DIR.glob("*.csv") if path != OUTPUT)
    inputs += sorted(IMPORT_DIR.glob("*.csv")) if IMPORT_DIR.exists() else []

    selected: dict[str, dict[str, str]] = {}
    conflicts: list[dict[str, str]] = []

    for path in inputs:
        for row in read_rows(path):
            key = normalize_key(row["source"])
            current = selected.get(key)
            if current is None:
                selected[key] = row
                continue

            if normalize_key(current["target_preferred"]) == normalize_key(row["target_preferred"]):
                current["source_id"] = merge_values(current["source_id"], row["source_id"])
                current["source_document"] = merge_values(
                    current["source_document"], row["source_document"]
                )
                if rank(row) > rank(current):
                    for field in ("status", "confidence", "category", "term_type"):
                        current[field] = row[field]
                continue

            winner, loser = (row, current) if rank(row) > rank(current) else (current, row)
            selected[key] = winner
            conflicts.append(
                {
                    "source": row["source"],
                    "selected_target": winner["target_preferred"],
                    "alternate_target": loser["target_preferred"],
                    "selected_source": winner["source_document"],
                    "alternate_source": loser["source_document"],
                }
            )

    rows = sorted(selected.values(), key=lambda row: (row["category"], normalize_key(row["source"])))
    with OUTPUT.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    conflict_fields = [
        "source",
        "selected_target",
        "alternate_target",
        "selected_source",
        "alternate_source",
    ]
    with CONFLICTS.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=conflict_fields)
        writer.writeheader()
        writer.writerows(conflicts)

    print(f"Built {OUTPUT.relative_to(ROOT)}: {len(rows)} unique terms")
    print(f"Translation conflicts: {len(conflicts)}")


if __name__ == "__main__":
    main()
