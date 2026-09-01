#!/usr/bin/env python3
"""Import the manual's quantitative ledger into the measurement registry.

The imported record is deliberately a documented specification, not a physical
measurement session. It keeps the source page, raw value text, numeric tokens,
and extraction status while remaining consumable from catalog/measurements/.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ID = "SRC-PORSCHE-WORKSHOP-MANUAL-993"
NUMBER_PATTERN = re.compile(r"[-+]?\d+(?:[\.,]\d+)?")


def numeric_values(value_text: str) -> list[float]:
    values: list[float] = []
    for token in NUMBER_PATTERN.findall(value_text.replace("−", "-")):
        try:
            values.append(float(token.replace(",", ".")))
        except ValueError:
            continue
    return values


def description_for(collection: str, row: dict[str, Any]) -> str:
    if collection == "technical_data":
        return f"{row.get('label', 'Technical data')}: {row.get('value_text', '')}".strip()
    if collection == "torque_specs":
        stage = row.get("stage")
        suffix = f" — {stage}" if stage else ""
        return f"{row.get('label', 'Torque specification')}{suffix}: {row.get('value_text', '')}".strip()
    context = row.get("context") or row.get("kind") or "OCR measurement occurrence"
    return f"{context}: {row.get('value_text', '')}".strip()


def convert(collection: str, prefix: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    converted: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        value_text = str(row.get("value_text", "")).strip()
        if not value_text:
            raise ValueError(f"{collection}[{index}] has no value_text")
        page = row.get("pdf_page")
        if not isinstance(page, int) or page < 1:
            raise ValueError(f"{collection}[{index}] has no valid pdf_page")
        converted.append(
            {
                "value_id": f"MNL-{prefix}-{index:04d}",
                "record_type": row.get("record_type", collection.rstrip("s")),
                "source_collection": collection,
                "description": description_for(collection, row),
                "pdf_page": page,
                "line": row.get("line"),
                "value_text": value_text,
                "unit": str(row.get("unit", "")),
                "numeric_values": numeric_values(value_text),
                "source_id": SOURCE_ID,
                "extraction_status": row.get("extraction_status"),
                "details": row,
            }
        )
    return converted


def build(manual: dict[str, Any], generated_on: str) -> dict[str, Any]:
    values = []
    values.extend(convert("technical_data", "TECH", manual["technical_data"]))
    values.extend(convert("torque_specs", "TORQUE", manual["torque_specs"]))
    values.extend(convert("measurement_occurrences", "OCR", manual["measurement_occurrences"]))
    return {
        "$comment": (
            "Import normalise du registre quantitatif du manuel dans catalog/measurements. "
            "Ces valeurs sont des specifications documentaires Porsche, pas des mesures "
            "physiques prises sur une voiture ou une piece. Regenerable par "
            "scripts/import_manual_measurements.py."
        ),
        "schema_version": "1.0.0",
        "measurement_id": "MEAS-MANUAL-993-ALL",
        "record_kind": "documented_specification",
        "source_id": SOURCE_ID,
        "subject": {
            "part_id": None,
            "part_reference": "Porsche 993 workshop manual",
            "variant": "multiple_993_variants",
            "description": "Toutes les valeurs quantitatives indexees dans le manuel d'atelier 993.",
        },
        "session": {
            "performed_on": generated_on,
            "operator_role": "document indexer",
            "ambient_temperature_c": None,
        },
        "datum": {
            "origin": "Numero de page PDF et ligne OCR du manuel de reference",
            "axes": "Non applicable : aucune piece physique n'a ete mesuree",
            "reference_image": None,
        },
        "instruments": [],
        "readings": [],
        "declared_values": values,
        "evidence": {
            "level": "A",
            "files": [
                "catalog/sources/src-porsche-workshop-manual-993.json",
                "catalog/sources/src-porschefanatics-993-manual-data.json",
                "docs/993_MANUAL_DATA_MAP.md",
            ],
            "contradictions": [],
        },
        "notes": (
            "Le manuel Porsche est la source de reference. Les 111 donnees techniques et "
            "195 couples sont structurees; les 2 190 occurrences proviennent de l'index OCR. "
            "Chaque valeur conserve son texte brut, sa page, son contexte dans details et son "
            "statut d'extraction. Les occurrences ocr_unreviewed doivent etre controlees dans "
            "l'exemplaire autorise avant toute CAO, fabrication ou decision de securite."
        ),
    }


def main(arguments: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=ROOT / "catalog" / "manual" / "993-workshop-manual-measurements.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "catalog" / "measurements" / "MEAS-MANUAL-993-ALL.json",
    )
    parser.add_argument("--generated-on", default="2026-08-30")
    args = parser.parse_args(arguments)

    manual = json.loads(args.input.read_text(encoding="utf-8"))
    payload = build(manual, args.generated_on)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output} ({len(payload['declared_values'])} declared values)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
