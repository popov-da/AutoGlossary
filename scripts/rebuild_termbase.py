#!/usr/bin/env python3
"""Build data/termbase.csv from domain and import CSV files.

The master file may contain repository metadata. Consumer exports are generated
separately by scripts/export_consumer.py.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
IMPORT_DIR = ROOT / "imports"
OUTPUT = DATA_DIR / "termbase.csv"
CONFLICTS = ROOT / "reports" / "conflicts.csv"
RESOLUTION_FILES = {"conflict-resolutions.csv", "volga-pilot-approved.csv"}

FIELDS = [
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
    "alternate_targets": ("alternate_targets", "alternate targets"),
}

VALID_STATUSES = {"candidate", "reviewed", "approved", "deprecated", "rejected"}
STATUS_SCORE = {
    "approved": 5,
    "reviewed": 4,
    "candidate": 3,
    "deprecated": 2,
    "rejected": 1,
}
CONFIDENCE_SCORE = {"high": 3, "medium": 2, "low": 1}
PRIVATE_DOC_RE = re.compile(r"\.dita\b", re.IGNORECASE)


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


def public_source_label(path: Path, source_id: str, supplied: str) -> str:
    """Prevent closed DITA filenames from leaking into generated files."""
    supplied = clean(supplied)
    if supplied and not PRIVATE_DOC_RE.search(supplied):
        return supplied
    source_id = clean(source_id)
    if source_id:
        return source_id.replace("_D2_CORPUS", "_CORPUS")
    return path.name


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
                row["source"] = row["source"].rstrip().removesuffix(".")
                status = row["status"].casefold() or "candidate"
                row["status"] = status if status in VALID_STATUSES else "candidate"
                row["confidence"] = row["confidence"].casefold() or "medium"
                row["category"] = row["category"] or "uncategorized"
                row["source_id"] = row["source_id"] or path.stem.upper()
                row["source_document"] = public_source_label(
                    path, row["source_id"], row["source_document"]
                )
                row["term_type"] = row["term_type"] or "term"
                result.append(row)
            return result
    except (UnicodeDecodeError, csv.Error):
        return []


def is_resolution(path: Path) -> bool:
    return path.name in RESOLUTION_FILES


def rank(row: dict[str, str], path: Path) -> tuple[int, int, int, int, str]:
    """Deterministic priority; curated decisions beat imported candidates."""
    return (
        int(is_resolution(path)),
        STATUS_SCORE.get(row["status"], 0),
        CONFIDENCE_SCORE.get(row["confidence"], 0),
        int(row["source_id"].startswith("VOLGA")),
        normalize_key(row["target_preferred"]),
    )


def merge_values(*values: str) -> str:
    parts: list[str] = []
    for value in values:
        parts.extend(clean(item) for item in value.split("|") if clean(item))
    return " | ".join(dict.fromkeys(parts))


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    CONFLICTS.parent.mkdir(exist_ok=True)

    inputs = sorted(path for path in DATA_DIR.glob("*.csv") if path != OUTPUT)
    inputs += sorted(IMPORT_DIR.glob("*.csv")) if IMPORT_DIR.exists() else []

    selected: dict[str, tuple[dict[str, str], Path]] = {}
    conflict_map: dict[tuple[str, str, str], dict[str, str]] = {}

    for path in inputs:
        for row in read_rows(path):
            key = normalize_key(row["source"])
            current_pair = selected.get(key)
            if current_pair is None:
                selected[key] = (row, path)
                continue

            current, current_path = current_pair
            same_target = normalize_key(current["target_preferred"]) == normalize_key(
                row["target_preferred"]
            )
            if same_target:
                current["source_id"] = merge_values(current["source_id"], row["source_id"])
                current["source_document"] = merge_values(
                    current["source_document"], row["source_document"]
                )
                if rank(row, path) > rank(current, current_path):
                    for field in ("status", "confidence", "category", "term_type"):
                        current[field] = row[field]
                    selected[key] = (current, path)
                continue

            if rank(row, path) > rank(current, current_path):
                winner, winner_path, loser = row, path, current
            else:
                winner, winner_path, loser = current, current_path, row

            winner["source_id"] = merge_values(winner["source_id"], loser["source_id"])
            winner["source_document"] = merge_values(
                winner["source_document"], loser["source_document"]
            )
            winner["alternate_targets"] = merge_values(
                winner.get("alternate_targets", ""),
                loser["target_preferred"],
                loser.get("alternate_targets", ""),
            )
            selected[key] = (winner, winner_path)

            # A curated resolution is an explicit editorial decision, not an
            # unresolved conflict. Alternatives remain visible in master metadata.
            if is_resolution(winner_path):
                continue

            conflict_key = (
                key,
                normalize_key(winner["target_preferred"]),
                normalize_key(loser["target_preferred"]),
            )
            conflict_map[conflict_key] = {
                "source": winner["source"],
                "selected_target": winner["target_preferred"],
                "alternate_target": loser["target_preferred"],
                "selected_status": winner["status"],
                "selected_source": winner["source_document"],
                "alternate_source": loser["source_document"],
                "resolution": "manual_review_required",
            }

    rows = [pair[0] for pair in selected.values() if pair[0]["status"] != "rejected"]
    rows.sort(key=lambda row: (row["category"], normalize_key(row["source"])))
    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    conflict_fields = [
        "source",
        "selected_target",
        "alternate_target",
        "selected_status",
        "selected_source",
        "alternate_source",
        "resolution",
    ]
    conflicts = sorted(conflict_map.values(), key=lambda row: normalize_key(row["source"]))
    with CONFLICTS.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=conflict_fields)
        writer.writeheader()
        writer.writerows(conflicts)

    print(f"Built {OUTPUT.relative_to(ROOT)}: {len(rows)} unique terms")
    print(f"Unresolved translation conflicts: {len(conflicts)}")


if __name__ == "__main__":
    main()
