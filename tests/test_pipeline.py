from __future__ import annotations

import csv
from pathlib import Path

from scripts.rebuild_termbase import public_source_label
from scripts.validate import validate_csv


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_public_source_label_anonymizes_dita_name(tmp_path: Path) -> None:
    path = tmp_path / "source.csv"
    assert (
        public_source_label(path, "N155_D2_CORPUS", "11.1 private-name.dita")
        == "N155_CORPUS"
    )


def test_consumer_rejects_casefold_duplicates(tmp_path: Path) -> None:
    path = tmp_path / "consumer-glossary.csv"
    write_csv(
        path,
        ["source", "target_preferred", "status"],
        [
            {"source": "ABS", "target_preferred": "ABS", "status": "approved"},
            {"source": "abs", "target_preferred": "АБС", "status": "candidate"},
        ],
    )
    errors = validate_csv(path, "consumer")
    assert any("duplicate source" in error for error in errors)


def test_domain_rejects_private_dita_filename(tmp_path: Path) -> None:
    path = tmp_path / "domain.csv"
    write_csv(
        path,
        [
            "source",
            "target_preferred",
            "status",
            "source_document",
        ],
        [
            {
                "source": "horn relay",
                "target_preferred": "реле звукового сигнала",
                "status": "candidate",
                "source_document": "11.12 private-title.dita",
            }
        ],
    )
    errors = validate_csv(path, "domain")
    assert any("private DITA filename" in error for error in errors)
