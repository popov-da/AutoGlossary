#!/usr/bin/env python3
"""Convert a COVESA VSS JSON export into AutoGlossary candidate rows.

Expected input is produced by the official vss-tools JSON exporter. The script
walks arbitrary nested dictionaries, recognizes VSS nodes by their metadata and
writes only English source records. Russian translations are deliberately left
empty for later editorial approval.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

FIELDS = [
    "source_key",
    "term_en",
    "abbreviation",
    "term_ru_candidate",
    "category",
    "term_type",
    "source_id",
    "translation_status",
    "definition_en",
    "usage_note_ru",
    "product_scope",
    "confidence",
    "source_url",
]

SOURCE_ID = "COVESA_VSS"
SOURCE_URL = "https://github.com/COVESA/vehicle_signal_specification"


def humanize(name: str) -> str:
    """Convert a VSS path segment to a readable fallback label."""
    result: list[str] = []
    token = ""
    for char in name.replace("_", " "):
        if token and char.isupper() and token[-1].islower():
            result.append(token)
            token = char
        else:
            token += char
    if token:
        result.append(token)
    return " ".join(result).strip()


def walk(
    value: Any,
    path: tuple[str, ...] = (),
) -> Iterator[tuple[tuple[str, ...], dict[str, Any]]]:
    if not isinstance(value, dict):
        return

    node_type = value.get("type")
    if isinstance(node_type, str):
        yield path, value

    ignored_keys = {"allowed", "default", "instances", "metadata"}
    for key, child in value.items():
        if isinstance(child, dict) and key not in ignored_keys:
            yield from walk(child, (*path, key))


def convert(document: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[str] = set()

    for path, node in walk(document):
        source_key = ".".join(path)
        if not source_key or source_key in seen:
            continue
        seen.add(source_key)

        description = str(node.get("description") or "").strip()
        leaf = path[-1] if path else source_key
        term = humanize(leaf)
        node_type = str(node.get("type") or "unknown").strip().lower()

        rows.append(
            {
                "source_key": source_key,
                "term_en": term,
                "abbreviation": "",
                "term_ru_candidate": "",
                "category": "vehicle_data",
                "term_type": node_type,
                "source_id": SOURCE_ID,
                "translation_status": "candidate",
                "definition_en": description,
                "usage_note_ru": "Требуется перевод и проверка по контексту проекта.",
                "product_scope": "",
                "confidence": "high" if description else "medium",
                "source_url": SOURCE_URL,
            }
        )

    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="VSS JSON export")
    parser.add_argument("output", type=Path, help="Output CSV")
    args = parser.parse_args()

    with args.input.open(encoding="utf-8") as source:
        document = json.load(source)
    if not isinstance(document, dict):
        raise TypeError("The VSS JSON root must be an object")

    rows = convert(document)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Written {len(rows)} COVESA candidate rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
