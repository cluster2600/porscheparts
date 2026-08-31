#!/usr/bin/env python3
"""Import PorscheFanatics 993 documentary specifications without upgrading evidence.

The upstream files are OCR-derived facts. This importer preserves every field,
adds stable identifiers and provenance, and deliberately does not write to the
instrumented measurement registry.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "catalog" / "specifications"

TECHNICAL_KEYS = {"label", "value", "values", "variants", "page", "unit", "subject"}
TORQUE_KEYS = {
    "location",
    "page",
    "group",
    "thread",
    "stage",
    "section",
    "torqueNm",
    "torqueFtLb",
    "angleDegrees",
    "note",
    "toleranceNm",
    "torqueNmMax",
    "model",
}


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("entries"), list):
        raise ValueError(f"{path}: expected an object containing an entries array")
    if not isinstance(value.get("reviewedOn"), str):
        raise ValueError(f"{path}: missing reviewedOn")
    return value


def _identifier(prefix: str, entry: dict[str, Any]) -> str:
    canonical = json.dumps(entry, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12].upper()
    return f"{prefix}-{digest}"


def _check_keys(entry: Any, allowed: set[str], label: str) -> dict[str, Any]:
    if not isinstance(entry, dict):
        raise ValueError(f"{label}: expected an object")
    unknown = set(entry) - allowed
    if unknown:
        raise ValueError(f"{label}: unsupported upstream fields: {', '.join(sorted(unknown))}")
    return entry


def _source(source_id: str, url: str, upstream: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "url": url,
        "publisher": "PorscheFanatics",
        "retrieved_on": date.today().isoformat(),
        "upstream_reviewed_on": upstream["reviewedOn"],
        "method": "derived_facts_from_ocr_transcription",
    }


def import_technical(upstream: dict[str, Any]) -> dict[str, Any]:
    records = []
    for index, raw in enumerate(upstream["entries"]):
        entry = _check_keys(raw, TECHNICAL_KEYS, f"technical entries[{index}]")
        records.append(
            {
                "record_id": _identifier("TD", entry),
                "page": entry.get("page"),
                "subject": entry.get("subject"),
                "label": entry.get("label"),
                "raw_value": entry.get("value"),
                "raw_values": entry.get("values", []),
                "raw_variants": entry.get("variants", []),
                "raw_unit": entry.get("unit"),
                "verification_status": "ocr_transcription_unverified",
            }
        )
    return {
        "schema_version": "1.0.0",
        "specification_set_id": "SPEC-PF-993-TECH-DATA",
        "title": "Porsche 993 technical data transcribed by PorscheFanatics",
        "kind": "technical_data",
        "source": _source(
            "SRC-PORSCHEFANATICS-993-TECH-DATA",
            "https://porschefanatics.com/993/technical-data/",
            upstream,
        ),
        "records": records,
        "notes": "Valeurs brutes conservees. Toute normalisation et utilisation CAO exigent une verification independante.",
    }


def import_torques(upstream: dict[str, Any]) -> dict[str, Any]:
    records = []
    for index, raw in enumerate(upstream["entries"]):
        entry = _check_keys(raw, TORQUE_KEYS, f"torque entries[{index}]")
        records.append(
            {
                "record_id": _identifier("TQ", entry),
                "page": entry.get("page"),
                "group": entry.get("group"),
                "model": entry.get("model"),
                "section": entry.get("section"),
                "location": entry.get("location"),
                "thread": entry.get("thread"),
                "stage": entry.get("stage"),
                "torque_nm": entry.get("torqueNm"),
                "torque_nm_max": entry.get("torqueNmMax"),
                "tolerance_nm": entry.get("toleranceNm"),
                "angle_degrees": entry.get("angleDegrees"),
                "torque_ft_lb": entry.get("torqueFtLb"),
                "raw_note": entry.get("note"),
                "verification_status": "ocr_transcription_unverified",
            }
        )
    return {
        "schema_version": "1.0.0",
        "specification_set_id": "SPEC-PF-993-TORQUES",
        "title": "Porsche 993 tightening data transcribed by PorscheFanatics",
        "kind": "tightening_torque",
        "source": _source(
            "SRC-PORSCHEFANATICS-993-TORQUES",
            "https://porschefanatics.com/993/torques/",
            upstream,
        ),
        "records": records,
        "notes": "Un couple seul ne constitue pas une procedure. Verifier sequence, lubrification et vis a usage unique dans la source primaire.",
    }


def _write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--technical-data", type=Path, required=True)
    parser.add_argument("--torques", type=Path, required=True)
    args = parser.parse_args()

    technical = import_technical(_load(args.technical_data))
    torques = import_torques(_load(args.torques))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _write(OUTPUT_DIR / "porschefanatics-993-technical-data.json", technical)
    _write(OUTPUT_DIR / "porschefanatics-993-torques.json", torques)
    print(f"technical specifications: {len(technical['records'])}")
    print(f"tightening specifications: {len(torques['records'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
