#!/usr/bin/env python3
"""Extract fail-closed Porsche 993 applicability evidence from PET model columns."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_ROOT = ROOT.parent / "porschefanatics.com"
DEFAULT_PET_TEXT = Path("/tmp/kat517-993.txt")
OUTPUT = ROOT / "twins" / "pet-993" / "applicability-evidence-f0.json"
PET_SOURCE_ID = "pet-classic-993"
GENERATION = "993"

DIRECT_VARIANT_MAP = {
    "CARRERA": ["993-carrera"],
    "CARRERA 2": ["993-carrera"],
    "CARRERA 4": ["993-carrera-4"],
    "CARRERA S": ["993-carrera-s"],
    "CARRERA 4 S": ["993-carrera-4s"],
    "CARRERA RS": ["993-rs"],
    "TURBO": ["993-turbo"],
    "TURBO S": ["993-turbo-s"],
}


class ContractError(ValueError):
    """Raised when PET applicability evidence does not close."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot_load:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"expected_object:{path}")
    return value


def render_json(value: dict[str, Any]) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_reference(value: str) -> str:
    return "".join(character for character in value.upper() if character.isalnum())


def occurrence_twin_id(source_id: str, illustration: str, reference: str) -> str:
    key = f"{source_id}::{illustration}::{reference}"
    return f"TWIN-PET-993-{sha256_text(key)[:20].upper()}"


def part_master_twin_id(reference: str) -> str:
    return f"TWIN-PET-993-PART-{sha256_text(normalize_reference(reference))[:20].upper()}"


def normalize_annotation(value: str) -> str:
    value = value.upper().replace("‐", "-").replace("–", "-")
    return " ".join(value.split()).strip(" .;:")


def classify_annotation(value: str) -> tuple[str | None, list[str]]:
    token = normalize_annotation(value)
    if token in DIRECT_VARIANT_MAP:
        return "direct_variant", list(DIRECT_VARIANT_MAP[token])
    if re.fullmatch(r"(?:COUPE|CABRIO|TARGA)(?:[/,](?:COUPE|CABRIO|TARGA))*", token):
        return "body_style", []
    if re.fullmatch(r"(?:C\.? ?[24]|CAR\.? ?2)(?:/(?:C\.? ?[24]|CABRIO|COUPE|TARGA))*", token):
        return "compound_model_shorthand", []
    if re.fullmatch(r"M64\.\d{2}(?:/\d{2})*", token):
        return "engine_code", []
    if re.fullmatch(r"Z64\.\d{2}(?:/\d{2})*", token):
        return "front_axle_drive_code", []
    if re.fullmatch(r"(?:G(?:50|64)|A50)\.\d{2}(?:/\d{2})*", token):
        return "transmission_code", []
    if re.fullmatch(r"M\d{3}(?:/\d{3})*", token):
        return "option_code", []
    if any(word in token for word in ("CARRERA", "TURBO", "CABRIO", "COUPE", "TARGA")):
        return "compound_model_annotation", []
    return None, []


def listed_rows(source_root: Path) -> list[dict[str, Any]]:
    payload = load_json(source_root / "data" / "oem-listed.json")
    rows = payload.get("listings")
    if not isinstance(rows, list):
        raise ContractError("oem_listed_rows")
    return [
        row
        for row in rows
        if isinstance(row, dict)
        and row.get("generationId") == GENERATION
        and row.get("petSourceId") == PET_SOURCE_ID
    ]


def parse_pet_model_columns(
    text: str, known_rows: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    known: dict[tuple[str, str], dict[str, Any]] = {}
    for row in known_rows:
        illustration = row.get("petIllustration")
        reference = row.get("oemReference")
        if not isinstance(illustration, str) or not isinstance(reference, str):
            continue
        key = (illustration, normalize_reference(reference))
        if key in known:
            raise ContractError(f"duplicate_known_occurrence:{key}")
        known[key] = row

    illustration: str | None = None
    columns: dict[str, int] | None = None
    parsed_tables = 0
    matched_part_rows = 0
    nonempty_model_rows = 0
    recognized_rows = 0
    unknown_tokens: Counter[str] = Counter()
    observations: dict[tuple[str, str], dict[str, Any]] = {}
    illustration_re = re.compile(r"Illustration:\s*([0-9]{3}-[0-9]{2,3})")

    for line_number, line in enumerate(text.splitlines(), start=1):
        illustration_match = illustration_re.search(line)
        if illustration_match:
            illustration = illustration_match.group(1)
            columns = None
            continue
        if all(label in line for label in ("Pos", "Part Number", "Description", "Qty", "Model")):
            try:
                columns = {
                    "part": line.index("Part Number"),
                    "description": line.index("Description"),
                    "qty": line.index("Qty"),
                    "model": line.index("Model", line.index("Qty") + len("Qty")),
                }
            except ValueError:
                columns = None
                continue
            if not (
                columns["part"] < columns["description"] < columns["qty"] < columns["model"]
            ):
                columns = None
                continue
            parsed_tables += 1
            continue
        if illustration is None or columns is None or len(line) <= columns["part"]:
            continue

        part_cell = line[columns["part"] : columns["description"]].strip()
        normalized_part = normalize_reference(part_cell)
        key = (illustration, normalized_part)
        source_row = known.get(key)
        if source_row is None:
            continue
        matched_part_rows += 1
        raw_model = line[columns["model"] :].strip() if len(line) > columns["model"] else ""
        if not raw_model:
            continue
        nonempty_model_rows += 1
        token = normalize_annotation(raw_model)
        kind, resolved_vehicle_ids = classify_annotation(token)
        if kind is None:
            unknown_tokens[token] += 1
            continue
        recognized_rows += 1
        quantity_cell = line[columns["qty"] : columns["model"]].strip()
        quantity_match = re.fullmatch(r"([0-9]+)", quantity_cell)
        quantity = int(quantity_match.group(1)) if quantity_match else None
        observation = observations.setdefault(
            key,
            {
                "oem_reference": source_row["oemReference"],
                "pet_illustration": illustration,
                "pet_page": source_row.get("petPage"),
                "occurrence_twin_id": occurrence_twin_id(
                    PET_SOURCE_ID, illustration, source_row["oemReference"]
                ),
                "part_master_twin_id": part_master_twin_id(source_row["oemReference"]),
                "annotations": {},
                "quantities": set(),
            },
        )
        annotation = observation["annotations"].setdefault(
            token,
            {
                "token": token,
                "kind": kind,
                "resolved_vehicle_ids": resolved_vehicle_ids,
                "logical_text_line_numbers": [],
            },
        )
        annotation["logical_text_line_numbers"].append(line_number)
        if quantity is not None and quantity > 0:
            observation["quantities"].add(quantity)

    records: list[dict[str, Any]] = []
    for observation in observations.values():
        annotations = sorted(observation.pop("annotations").values(), key=lambda item: item["token"])
        for annotation in annotations:
            annotation["logical_text_line_numbers"] = sorted(
                set(annotation["logical_text_line_numbers"])
            )
        quantities = sorted(observation.pop("quantities"))
        resolved_ids = sorted(
            {
                vehicle_id
                for annotation in annotations
                if annotation["kind"] == "direct_variant"
                for vehicle_id in annotation["resolved_vehicle_ids"]
            }
        )
        non_direct = [annotation["token"] for annotation in annotations if annotation["kind"] != "direct_variant"]
        bom_eligible = bool(resolved_ids) and len(quantities) == 1 and not non_direct
        records.append(
            {
                **observation,
                "annotations": annotations,
                "directly_resolved_vehicle_ids": resolved_ids,
                "observed_quantities_per_car": quantities,
                "candidate_quantity_per_car": quantities[0] if len(quantities) == 1 else None,
                "resolution_status": (
                    "exact_direct_model_column"
                    if resolved_ids and not non_direct
                    else "mixed_or_indirect_model_column"
                ),
                "machine_bom_candidate": bom_eligible,
                "claims": {
                    "human_reviewed": False,
                    "universal_variant_fitment": False,
                    "geometry_fit": False,
                    "manufacturing_release": False,
                },
            }
        )
    records.sort(key=lambda item: item["occurrence_twin_id"])
    diagnostics = {
        "source_line_count": len(text.splitlines()),
        "parsed_table_count": parsed_tables,
        "matched_part_row_sightings": matched_part_rows,
        "nonempty_model_row_sightings": nonempty_model_rows,
        "recognized_model_row_sightings": recognized_rows,
        "unrecognized_model_tokens": [
            {"token": token, "sightings": count}
            for token, count in sorted(unknown_tokens.items(), key=lambda item: (-item[1], item[0]))
        ],
    }
    return records, diagnostics


def build(source_root: Path, pet_text_path: Path) -> dict[str, Any]:
    try:
        text = pet_text_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ContractError(f"cannot_load_pet_text:{pet_text_path}:{exc}") from exc
    rows = listed_rows(source_root)
    records, diagnostics = parse_pet_model_columns(text, rows)
    candidate_records = [record for record in records if record["machine_bom_candidate"]]
    vehicle_counts = Counter(
        vehicle_id
        for record in candidate_records
        for vehicle_id in record["directly_resolved_vehicle_ids"]
    )
    return {
        "$comment": (
            "Preuves F0 extraites uniquement de la colonne Model portee par une ligne PET. Les titres de "
            "section ne sont pas propages; les candidats BOM restent des extractions machine a relire."
        ),
        "schema_version": "1.0.0",
        "generated_by": str(Path(__file__).resolve().relative_to(ROOT)),
        "source_boundary": {
            "pet_source_id": PET_SOURCE_ID,
            "pet_text_expected_path": str(pet_text_path),
            "pet_text_sha256": sha256_file(pet_text_path),
            "raw_pet_text_copied": False,
            "raw_pet_pdf_copied": False,
            "oem_listed_path": "../porschefanatics.com/data/oem-listed.json",
            "oem_listed_sha256": sha256_file(source_root / "data" / "oem-listed.json"),
        },
        "scope": {
            "generation": GENERATION,
            "source_listed_occurrences": len(rows),
            "annotated_occurrence_records": len(records),
            "machine_bom_candidate_occurrences": len(candidate_records),
            "machine_bom_candidate_vehicle_links": sum(vehicle_counts.values()),
            "candidate_vehicle_counts": dict(sorted(vehicle_counts.items())),
            "human_reviewed_occurrences": 0,
            "complete_variant_boms": 0,
        },
        "diagnostics": diagnostics,
        "records": records,
        "prohibited_claims": [
            "machine_model_column_extraction_is_human_pet_review",
            "absence_of_model_annotation_means_part_is_excluded",
            "body_option_engine_transmission_or_drivetrain_code_is_exact_variant_without_review",
            "machine_bom_candidate_is_complete_vehicle_bom",
            "applicability_evidence_proves_geometry_material_or_function",
        ],
    }


def validate_contract(contract: dict[str, Any]) -> None:
    scope = contract.get("scope", {})
    records = contract.get("records")
    if not isinstance(records, list) or scope.get("annotated_occurrence_records") != len(records):
        raise ContractError("record_count")
    if scope.get("human_reviewed_occurrences") != 0 or scope.get("complete_variant_boms") != 0:
        raise ContractError("must_fail_closed")
    twin_ids = [record.get("occurrence_twin_id") for record in records]
    if None in twin_ids or len(twin_ids) != len(set(twin_ids)):
        raise ContractError("duplicate_or_missing_occurrence_twin")
    candidate_count = 0
    vehicle_links = 0
    known_vehicle_ids = {vehicle_id for values in DIRECT_VARIANT_MAP.values() for vehicle_id in values}
    for record in records:
        claims = record.get("claims", {})
        for claim in ("human_reviewed", "universal_variant_fitment", "geometry_fit", "manufacturing_release"):
            if claims.get(claim) is not False:
                raise ContractError(f"overclaim:{record.get('occurrence_twin_id')}:{claim}")
        resolved = record.get("directly_resolved_vehicle_ids")
        if not isinstance(resolved, list) or not set(resolved).issubset(known_vehicle_ids):
            raise ContractError(f"resolved_vehicle_ids:{record.get('occurrence_twin_id')}")
        if record.get("machine_bom_candidate"):
            candidate_count += 1
            vehicle_links += len(resolved)
            if not resolved or not isinstance(record.get("candidate_quantity_per_car"), int):
                raise ContractError(f"invalid_bom_candidate:{record.get('occurrence_twin_id')}")
            if any(annotation.get("kind") != "direct_variant" for annotation in record.get("annotations", [])):
                raise ContractError(f"indirect_bom_candidate:{record.get('occurrence_twin_id')}")
    if candidate_count != scope.get("machine_bom_candidate_occurrences"):
        raise ContractError("candidate_count")
    if vehicle_links != scope.get("machine_bom_candidate_vehicle_links"):
        raise ContractError("candidate_vehicle_link_count")
    source = contract.get("source_boundary", {})
    if source.get("raw_pet_text_copied") is not False or source.get("raw_pet_pdf_copied") is not False:
        raise ContractError("raw_source_boundary")
    if not isinstance(source.get("pet_text_sha256"), str) or len(source["pet_text_sha256"]) != 64:
        raise ContractError("pet_text_digest")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--check-index", action="store_true")
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--pet-text", type=Path, default=DEFAULT_PET_TEXT)
    args = parser.parse_args(argv)
    try:
        if args.check_index:
            validate_contract(load_json(OUTPUT))
            print(f"valid {OUTPUT.relative_to(ROOT)}")
            return 0
        contract = build(args.source_root, args.pet_text)
        validate_contract(contract)
        expected = render_json(contract)
        if args.write:
            OUTPUT.parent.mkdir(parents=True, exist_ok=True)
            OUTPUT.write_text(expected, encoding="utf-8")
            print(
                f"wrote {OUTPUT.relative_to(ROOT)} with "
                f"{contract['scope']['machine_bom_candidate_occurrences']} machine BOM candidates"
            )
            return 0
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != expected:
            print(f"stale:{OUTPUT}", file=sys.stderr)
            return 1
        print(f"current {OUTPUT.relative_to(ROOT)}")
        return 0
    except ContractError as exc:
        print(f"PET 993 applicability contract error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
