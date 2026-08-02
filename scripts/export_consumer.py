#!/usr/bin/env python3
"""Export strict three-column glossaries for the machine-translation consumer."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data" / "termbase.csv"
EXPORT_DIR = ROOT / "exports"
FIELDS = ["source", "target_preferred", "status"]
VALID_EXPORT_STATUSES = {"candidate", "reviewed", "approved", "deprecated"}

SLICES = {
    "body-repair": {
        "categories": ("body.", "welding", "service."),
        "sources": ("N155", "N165", "EDITORIAL_CORE"),
    },
    "n155-n165": {
        "categories": (),
        "sources": ("N155", "N165"),
    },
    "mechanical": {
        "categories": (
            "engine", "fuel", "cooling", "lubrication", "transmission",
            "automatic_transmission", "driveline", "brakes", "suspension",
            "steering", "bearings", "assembly", "fasteners", "tools",
            "materials", "service.", "maintenance.", "hydraulics", "pneumatics",
            "wheels", "tires",
        ),
        "sources": (),
        "exclude_categories": ("adas", "automated_driving", "ev", "charging", "autosar"),
    },
}


def clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def key(value: str) -> str:
    return clean(value).casefold()


def read_master(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"source", "target_preferred", "status", "category", "source_id", "source_document"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Master file missing columns: {', '.join(sorted(missing))}")
        return [dict(row) for row in reader]


def export_rows(rows: list[dict[str, str]], output: Path) -> int:
    unique: dict[str, dict[str, str]] = {}
    for row in rows:
        source = clean(row.get("source", "")).removesuffix(".")
        target = clean(row.get("target_preferred", ""))
        status = clean(row.get("status", "")).casefold()
        if not source or not target or status == "rejected":
            continue
        if status not in VALID_EXPORT_STATUSES:
            status = "deprecated" if status == "rejected" else "candidate"
        normalized = key(source)
        if normalized in unique:
            raise ValueError(f"Duplicate source in export input: {source!r}")
        unique[normalized] = {
            "source": source,
            "target_preferred": target,
            "status": status,
        }

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(sorted(unique.values(), key=lambda row: key(row["source"])))
    return len(unique)


def matches_slice(row: dict[str, str], config: dict[str, tuple[str, ...]]) -> bool:
    category = key(row.get("category", ""))
    provenance = key(f"{row.get('source_id', '')} | {row.get('source_document', '')}")
    excluded = tuple(item.casefold() for item in config.get("exclude_categories", ()))
    if excluded and any(category.startswith(item) for item in excluded):
        return False
    categories = tuple(item.casefold() for item in config.get("categories", ()))
    sources = tuple(item.casefold() for item in config.get("sources", ()))
    category_match = bool(categories and any(category.startswith(item) for item in categories))
    source_match = bool(sources and any(item in provenance for item in sources))
    return category_match or source_match


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--master", type=Path, default=MASTER)
    parser.add_argument("--output-dir", type=Path, default=EXPORT_DIR)
    args = parser.parse_args()

    rows = read_master(args.master)
    count = export_rows(rows, args.output_dir / "consumer-glossary.csv")
    print(f"Exported consumer-glossary.csv: {count} rows")

    for name, config in SLICES.items():
        selected = [row for row in rows if matches_slice(row, config)]
        slice_count = export_rows(selected, args.output_dir / f"consumer-{name}.csv")
        print(f"Exported consumer-{name}.csv: {slice_count} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
