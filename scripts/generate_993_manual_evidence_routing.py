#!/usr/bin/env python3
"""Route the 993 workshop-manual ledger to vehicle systems and PET review candidates."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "catalog" / "manual" / "993-workshop-manual-measurements.json"
PET_INDEX = ROOT / "twins" / "pet-993" / "index-f0.json"
PROGRAM_DEFINITION = ROOT / "twins" / "vehicle-993" / "program-definition.json"
OUTPUT = ROOT / "twins" / "vehicle-993" / "manual-evidence-routing-f0.json"
SYSTEM_IDS = tuple(f"{value}xx" for value in range(10))


class ContractError(ValueError):
    """Raised when the manual evidence routing contract does not close."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot_load:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"expected_object:{path}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


def render(value: dict[str, Any]) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def normalize_text(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ContractError(f"expected_jsonl_object:{path}:{line_number}")
                records.append(value)
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot_load_jsonl:{path}:{exc}") from exc
    return records


def load_part_masters(index: dict[str, Any]) -> list[dict[str, Any]]:
    shards = index.get("output", {}).get("part_master_shards")
    if not isinstance(shards, list):
        raise ContractError("part_master_shards")
    masters: list[dict[str, Any]] = []
    for shard in shards:
        if not isinstance(shard, dict) or not isinstance(shard.get("path"), str):
            raise ContractError("part_master_shard_record")
        path = ROOT / shard["path"]
        if sha256_file(path) != shard.get("sha256"):
            raise ContractError(f"part_master_shard_digest:{shard['path']}")
        records = read_jsonl(path)
        if len(records) != shard.get("record_count"):
            raise ContractError(f"part_master_shard_count:{shard['path']}")
        masters.extend(records)
    expected = index.get("scope", {}).get("part_master_twins")
    if len(masters) != expected:
        raise ContractError(f"part_master_total:{len(masters)}:{expected}")
    return masters


def validate_program_systems(definition: dict[str, Any]) -> None:
    routes = definition.get("system_routes")
    if not isinstance(routes, list):
        raise ContractError("program_system_routes")
    route_ids = {str(item.get("system_id")) for item in routes if isinstance(item, dict)}
    if route_ids != set(SYSTEM_IDS):
        raise ContractError("program_system_ids")


def technical_system(row: dict[str, Any]) -> tuple[str | None, str]:
    subject = normalize_text(row.get("subject"))
    if "overall vehicle" in subject:
        return "0xx", "structured_subject_overall_vehicle"
    if "transmission" in subject:
        return "3xx", "structured_subject_transmission"
    if "brake" in subject:
        return "4xx", "structured_subject_brake"
    return None, "unresolved_structured_subject"


def torque_system(row: dict[str, Any]) -> tuple[str | None, str]:
    group = normalize_text(row.get("group"))
    if "engine" in group:
        return "1xx", "structured_group_engine"
    if "transmission" in group:
        return "3xx", "structured_group_transmission"
    if any(
        value in group
        for value in ("suspension", "drive shaft", "brake", "steering")
    ):
        return "4xx", "structured_group_chassis"
    return None, "unresolved_structured_group"


def occurrence_system(row: dict[str, Any]) -> tuple[str | None, str]:
    header = str(row.get("page_header") or "")
    repair_groups = re.findall(r"(?<!\d)(\d{2})(?!\d)", header)
    if repair_groups:
        group = repair_groups[-1]
        return f"{int(group) // 10}xx", f"repair_group_{group}"

    normalized = normalize_text(header)
    rules = (
        (("overall vehicle", "maintenance"), "0xx", "header_general"),
        (("engine", "cylinder head", "valve drive"), "1xx", "header_engine"),
        (("fuel", "exhaust", "dme"), "2xx", "header_fuel_or_engine_management"),
        (("transmission", "differential", "clutch", "tiptronic"), "3xx", "header_transmission"),
        (("chassis", "suspension", "wheel", "brake", "steering"), "4xx", "header_chassis"),
        (("body", "roof", "frame"), "5xx", "header_body"),
        (("seat", "interior"), "7xx", "header_interior"),
        (("heater", "air conditioning", "ventilation"), "8xx", "header_hvac"),
        (("windshield wiper", "washer", "electrical", "wiring"), "9xx", "header_electrical"),
    )
    for terms, system_id, basis in rules:
        if any(term in normalized for term in terms):
            return system_id, basis
    return None, "unresolved_page_header"


def evidence_id(collection: str, index: int, row: dict[str, Any]) -> str:
    identity = json.dumps(
        {
            "collection": collection,
            "index": index,
            "page": row.get("pdf_page"),
            "record_type": row.get("record_type"),
            "value_text": row.get("value_text"),
        },
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return f"MANUAL-993-{sha256_text(identity)[:20].upper()}"


def description_index(
    masters: list[dict[str, Any]],
) -> dict[str, dict[str, set[str]]]:
    result: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for master in masters:
        master_id = master.get("twin_id")
        graph = master.get("documentary_graph", {})
        subject = master.get("subject", {})
        if not isinstance(master_id, str):
            raise ContractError("part_master_id")
        for system_id in graph.get("system_ids", []):
            if system_id not in SYSTEM_IDS:
                raise ContractError(f"part_master_system:{master_id}:{system_id}")
            for description in subject.get("descriptions", []):
                phrase = normalize_text(description)
                if len(phrase) >= 8 and len(phrase.split()) >= 2:
                    result[system_id][phrase].add(master_id)
    return result


def lexical_candidates(
    *,
    system_id: str | None,
    source_text: Any,
    phrases: dict[str, dict[str, set[str]]],
) -> tuple[list[str], list[str]]:
    if system_id is None:
        return [], []
    normalized_source = f" {normalize_text(source_text)} "
    matched_phrases: list[str] = []
    master_ids: set[str] = set()
    for phrase, candidates in phrases[system_id].items():
        if f" {phrase} " in normalized_source:
            matched_phrases.append(phrase)
            master_ids.update(candidates)
    return sorted(matched_phrases), sorted(master_ids)


def build() -> dict[str, Any]:
    manual = load_json(MANUAL)
    pet_index = load_json(PET_INDEX)
    definition = load_json(PROGRAM_DEFINITION)
    validate_program_systems(definition)
    masters = load_part_masters(pet_index)
    phrases = description_index(masters)

    collections: tuple[
        tuple[str, list[dict[str, Any]], Callable[[dict[str, Any]], tuple[str | None, str]], str | None],
        ...,
    ] = (
        ("technical_data", manual.get("technical_data", []), technical_system, None),
        ("torque_specs", manual.get("torque_specs", []), torque_system, "label"),
        (
            "measurement_occurrences",
            manual.get("measurement_occurrences", []),
            occurrence_system,
            "context",
        ),
    )
    routing_records: list[dict[str, Any]] = []
    part_candidates: list[dict[str, Any]] = []
    routing_counts: Counter[str] = Counter()
    unresolved_by_collection: Counter[str] = Counter()
    for collection, rows, router, lexical_field in collections:
        if not isinstance(rows, list):
            raise ContractError(f"manual_collection:{collection}")
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                raise ContractError(f"manual_row:{collection}:{index}")
            record_id = evidence_id(collection, index, row)
            system_id, basis = router(row)
            if system_id is not None and system_id not in SYSTEM_IDS:
                raise ContractError(f"manual_system:{collection}:{index}:{system_id}")
            routing_counts[system_id or "unresolved"] += 1
            if system_id is None:
                unresolved_by_collection[collection] += 1
            routing_records.append(
                {
                    "manual_evidence_id": record_id,
                    "source_collection": collection,
                    "source_index": index,
                    "pdf_page": row.get("pdf_page"),
                    "record_type": row.get("record_type"),
                    "kind": row.get("kind"),
                    "unit": row.get("unit"),
                    "extraction_status": row.get("extraction_status"),
                    "system_id": system_id,
                    "routing_basis": basis,
                    "routing_status": (
                        "candidate_system_route_not_engineering_proof"
                        if system_id is not None
                        else "unresolved"
                    ),
                }
            )
            if lexical_field is None:
                continue
            matched_phrases, master_ids = lexical_candidates(
                system_id=system_id,
                source_text=row.get(lexical_field),
                phrases=phrases,
            )
            if not master_ids:
                continue
            part_candidates.append(
                {
                    "manual_evidence_id": record_id,
                    "source_collection": collection,
                    "source_index": index,
                    "pdf_page": row.get("pdf_page"),
                    "system_id": system_id,
                    "matched_description_phrases": matched_phrases,
                    "candidate_part_master_count": len(master_ids),
                    "candidate_part_master_twin_ids": master_ids,
                    "lexically_unambiguous": len(master_ids) == 1,
                    "review_status": "manual_review_required_exact_lexical_match_only",
                    "claims": {
                        "part_identity": False,
                        "dimension_or_torque_assigned_to_part": False,
                        "load_case_or_boundary_condition": False,
                        "manufacturing_release": False,
                    },
                }
            )

    expected_counts = manual.get("counts", {})
    expected_total = expected_counts.get("total_records")
    if len(routing_records) != expected_total:
        raise ContractError(f"manual_total:{len(routing_records)}:{expected_total}")
    candidate_links = sum(item["candidate_part_master_count"] for item in part_candidates)
    candidate_masters = {
        master_id
        for item in part_candidates
        for master_id in item["candidate_part_master_twin_ids"]
    }
    index = {
        "$comment": (
            "Routage conservateur des faits du manuel 993 vers les systemes et candidats PET. "
            "Les transcriptions OCR restent non verifiees et ne sont jamais promues en cotes de piece."
        ),
        "schema_version": "1.0.0",
        "generated_by": relative(Path(__file__).resolve()),
        "source_boundary": {
            "manual_ledger": relative(MANUAL),
            "manual_ledger_sha256": sha256_file(MANUAL),
            "manual_source_id": manual.get("source_id"),
            "manual_pdf_pages": manual.get("manual_pdf_pages"),
            "pet_twin_index": relative(PET_INDEX),
            "pet_twin_index_sha256": sha256_file(PET_INDEX),
            "source_master_shards_verified": True,
            "program_definition": relative(PROGRAM_DEFINITION),
            "program_definition_sha256": sha256_file(PROGRAM_DEFINITION),
            "manual_pdf_copied": False,
        },
        "scope": {
            "manual_records": len(routing_records),
            "technical_data_records": len(manual["technical_data"]),
            "torque_spec_records": len(manual["torque_specs"]),
            "measurement_occurrence_records": len(manual["measurement_occurrences"]),
            "system_routed_records": len(routing_records) - routing_counts["unresolved"],
            "unresolved_system_records": routing_counts["unresolved"],
            "part_review_candidate_records": len(part_candidates),
            "part_review_candidate_links": candidate_links,
            "part_master_twins_with_candidates": len(candidate_masters),
            "lexically_unambiguous_candidate_records": sum(
                item["lexically_unambiguous"] for item in part_candidates
            ),
            "promoted_part_measurements_or_torques": 0,
        },
        "coverage": {
            "records_by_system": {
                system_id: routing_counts[system_id] for system_id in SYSTEM_IDS
            },
            "unresolved_records_by_collection": dict(sorted(unresolved_by_collection.items())),
        },
        "routing_policy": {
            "structured_data": "manual subject or group mapped to one PET system family",
            "ocr_occurrences": (
                "two-digit repair group in page header, otherwise conservative header keyword"
            ),
            "part_candidates": (
                "whole normalized PET description phrase contained in the manual row within the same system"
            ),
            "automatic_promotion_allowed": False,
        },
        "routing_records": routing_records,
        "part_review_candidates": part_candidates,
        "prohibited_claims": [
            "system_route_proves_part_identity",
            "lexical_candidate_assigns_dimension_or_torque_to_part",
            "ocr_occurrence_is_verified_measurement",
            "manual_fact_is_load_case_without_engineering_interpretation",
            "manual_routing_authorizes_simulation_manufacturing_or_road_use",
        ],
    }
    return index


def validate_index(index: dict[str, Any]) -> None:
    scope = index.get("scope", {})
    total = scope.get("manual_records")
    if total != 2496:
        raise ContractError(f"manual_record_count:{total}")
    if scope.get("technical_data_records") != 111:
        raise ContractError("technical_data_count")
    if scope.get("torque_spec_records") != 195:
        raise ContractError("torque_spec_count")
    if scope.get("measurement_occurrence_records") != 2190:
        raise ContractError("measurement_occurrence_count")
    if scope.get("system_routed_records") + scope.get("unresolved_system_records") != total:
        raise ContractError("system_route_partition")
    if scope.get("promoted_part_measurements_or_torques") != 0:
        raise ContractError("manual_promotion_overclaim")
    routing_records = index.get("routing_records")
    if not isinstance(routing_records, list) or len(routing_records) != total:
        raise ContractError("routing_records")
    record_ids = [item.get("manual_evidence_id") for item in routing_records]
    if None in record_ids or len(record_ids) != len(set(record_ids)):
        raise ContractError("manual_evidence_ids")
    routed = [item for item in routing_records if item.get("system_id") is not None]
    if len(routed) != scope.get("system_routed_records"):
        raise ContractError("routed_record_count")
    if any(item.get("system_id") not in SYSTEM_IDS for item in routed):
        raise ContractError("routed_system_id")
    coverage = index.get("coverage", {}).get("records_by_system", {})
    if set(coverage) != set(SYSTEM_IDS) or sum(coverage.values()) != len(routed):
        raise ContractError("system_coverage")
    candidates = index.get("part_review_candidates")
    if not isinstance(candidates, list) or len(candidates) != scope.get(
        "part_review_candidate_records"
    ):
        raise ContractError("part_review_candidates")
    if sum(item.get("candidate_part_master_count", 0) for item in candidates) != scope.get(
        "part_review_candidate_links"
    ):
        raise ContractError("part_candidate_links")
    if any(any(item.get("claims", {}).values()) for item in candidates):
        raise ContractError("manual_candidate_claim_overreach")
    boundary = index.get("source_boundary", {})
    if boundary.get("source_master_shards_verified") is not True:
        raise ContractError("source_master_shards_not_verified")
    if boundary.get("manual_pdf_copied") is not False:
        raise ContractError("manual_pdf_boundary")


def run(*, write: bool, check_index: bool = False) -> int:
    if check_index:
        validate_index(load_json(OUTPUT))
        print(f"valid {relative(OUTPUT)}")
        return 0
    expected = build()
    validate_index(expected)
    content = render(expected)
    if write:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(content, encoding="utf-8")
        print(
            f"wrote {expected['scope']['manual_records']} manual records and "
            f"{expected['scope']['part_review_candidate_links']} part candidate links to "
            f"{relative(OUTPUT)}"
        )
        return 0
    if not OUTPUT.is_file():
        print(f"missing:{relative(OUTPUT)}", file=sys.stderr)
        return 1
    if OUTPUT.read_text(encoding="utf-8") != content:
        print(f"stale:{relative(OUTPUT)}", file=sys.stderr)
        return 1
    print(f"current {relative(OUTPUT)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--check-index", action="store_true")
    args = parser.parse_args(argv)
    try:
        return run(write=args.write, check_index=args.check_index)
    except ContractError as exc:
        print(f"993 manual evidence routing error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
