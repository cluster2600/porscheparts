#!/usr/bin/env python3
"""Generate a fail-closed Porsche 993 configuration roster from PET summaries."""

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
DEFAULT_PET_TEXT = Path("/tmp/kat517-993.txt")
APPLICABILITY_EVIDENCE = ROOT / "twins" / "pet-993" / "applicability-evidence-f0.json"
CONFIGURATION_AXES = ROOT / "twins" / "vehicle-993" / "configuration-axes-f0.json"
OUTPUT = ROOT / "twins" / "vehicle-993" / "configuration-roster-f0.json"
PET_SOURCE_ID = "pet-classic-993"


class ContractError(ValueError):
    """Raised when the PET configuration roster cannot close."""


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


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


def stable_id(prefix: str, *values: object) -> str:
    key = "::".join(str(value) for value in values)
    return f"{prefix}-{sha256_text(key)[:20].upper()}"


def section(lines: list[str], start_label: str, end_label: str) -> tuple[int, int]:
    try:
        start = next(index for index, line in enumerate(lines) if start_label in line)
        end = next(
            index for index, line in enumerate(lines[start + 1 :], start + 1) if end_label in line
        )
    except StopIteration as exc:
        raise ContractError(f"missing_section:{start_label}:{end_label}") from exc
    return start, end


def continuation_lines(lines: list[str], row_index: int, section_end: int) -> list[tuple[int, str]]:
    continuations: list[tuple[int, str]] = []
    for index in range(row_index + 1, min(row_index + 3, section_end)):
        value = lines[index].strip()
        if not value or value.startswith("911"):
            break
        if value.startswith("(") or value.startswith("/4S"):
            continuations.append((index + 1, value))
            continue
        break
    return continuations


def parenthetical_tokens(*values: str) -> list[str]:
    tokens: set[str] = set()
    for value in values:
        for token in re.findall(r"\(([^)]+)\)", value.upper()):
            compact = " ".join(token.split())
            if compact:
                tokens.add(compact)
    return sorted(tokens)


def option_tokens(*values: str) -> list[str]:
    tokens: set[str] = set()
    for value in values:
        normalized = re.sub(r"M\s+(\d{3})", r"M\1", value.upper())
        tokens.update(re.findall(r"\bM\d{3}\b", normalized))
    return sorted(tokens)


def market_group(markers: list[str]) -> str:
    marker_set = set(markers)
    if marker_set.intersection({"USA", "CDN", "RC"}):
        return "north_america"
    if "BR" in marker_set:
        return "brazil"
    if "MEX" in marker_set:
        return "mexico"
    if marker_set:
        return "other_explicit_markets"
    return "rest_of_world_unmarked"


def expand_engine_codes(value: str) -> list[str]:
    head, *suffixes = value.split("/")
    prefix = head.rsplit(".", 1)[0]
    return [head, *(f"{prefix}.{suffix}" for suffix in suffixes)]


def normalized_family(model_token: str, qualifier: str = "", body_token: str = "") -> str:
    compact_model = " ".join(model_token.upper().replace("CARERRA", "CARRERA").split())
    qualifier_upper = qualifier.upper()
    if compact_model == "TURBO":
        return "turbo"
    if compact_model == "CARRERA 4" or "4/4S" in qualifier_upper:
        return "carrera_4_family"
    if body_token.upper() == "RS" or re.search(r"\bRS\b", qualifier_upper):
        return "carrera_rs"
    return "carrera_family"


TYPE_PATTERN = re.compile(
    r"^\s*911\s+(?P<model>CAR+ER+A(?:\s+4)?|CARRERA(?:\s+4)?|TURBO)\s+"
    r"(?P<body>COUPE|CABRIO|TARGA|RS)(?P<qualifier>.*?)\s+"
    r"(?P<year>9[4-8])\s+(?P<year_code>[RSTVW])\s+"
    r"(?P<vin_type>99[RSTVW]S3)\s+(?P<vin_start>\d+)>(?P<vin_end>\d+)\s+"
    r"(?P<engine>M64\.\d{2}(?:/\d{2})*)\s+(?P<power_kw>\d+)\s+KW\s*$"
)


def parse_type_records(lines: list[str], start: int, end: int) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for index in range(start, end):
        match = TYPE_PATTERN.match(lines[index])
        if not match:
            continue
        values = match.groupdict()
        continuations = continuation_lines(lines, index, end)
        continuation_values = [value for _, value in continuations]
        model_token = " ".join(values["model"].upper().replace("CARERRA", "CARRERA").split())
        qualifier = " ".join(values["qualifier"].split())
        markers = parenthetical_tokens(qualifier, *continuation_values)
        anomalies = []
        if "CARERRA" in lines[index].upper():
            anomalies.append("source_model_token_carerra_normalized_to_carrera")
        body_style = {
            "COUPE": "Coupé",
            "CABRIO": "Cabriolet",
            "TARGA": "Targa",
        }.get(values["body"])
        family = normalized_family(model_token, qualifier, values["body"])
        key_fields = (
            index + 1,
            model_token,
            values["body"],
            values["year"],
            values["vin_type"],
            values["vin_start"],
            values["vin_end"],
        )
        records.append(
            {
                "type_record_id": stable_id("PET993-TYPE", *key_fields),
                "model_family": family,
                "source_model_token": model_token,
                "body_or_variant_token": values["body"],
                "body_style": body_style,
                "model_year": 1900 + int(values["year"]),
                "model_year_code": values["year_code"],
                "market_markers": markers,
                "market_group": market_group(markers),
                "vin_type": values["vin_type"],
                "vin_serial_start": int(values["vin_start"]),
                "vin_serial_end": int(values["vin_end"]),
                "engine_codes": expand_engine_codes(values["engine"]),
                "declared_power_kw": int(values["power_kw"]),
                "source_qualifier": qualifier or None,
                "source_anomalies": anomalies,
                "source_evidence": {
                    "pet_source_id": PET_SOURCE_ID,
                    "summary_table": "SUMMARY TYPES",
                    "logical_text_line_numbers": [
                        index + 1,
                        *(line_number for line_number, _ in continuations),
                    ],
                },
                "claims": {
                    "human_reviewed": False,
                    "complete_vehicle_configuration": False,
                    "vehicle_bom": False,
                },
            }
        )
    records.sort(key=lambda item: item["type_record_id"])
    if not records:
        raise ContractError("no_type_records")
    return records


ENGINE_PATTERN = re.compile(
    r"\b(?P<engine>M64\.\d{2})\b\s+(?P<year>9[4-8])\s+(?P<year_code>[RSTVW])\s+"
    r"(?P<number_prefix>[0-9A-Z]+)\s+(?P<number_start>\d+)>(?P<number_end>\d+)\s+"
    r"6ZYL/3(?P<decimal>[,.]\d+)L\s*/?(?P<power_kw>\d+)\s+KW\s*$"
)


def parse_model_prefix(prefix: str) -> tuple[str, str, str]:
    normalized = " ".join(prefix.upper().replace("TIPTRINIC", "TIPTRONIC").split())
    if not normalized.startswith("911 "):
        raise ContractError(f"invalid_model_prefix:{prefix}")
    value = normalized[4:]
    if value.startswith("TURBO"):
        return "TURBO", "turbo", value[len("TURBO") :].strip()
    if value.startswith("CARRERA 4"):
        qualifier = value[len("CARRERA 4") :].strip()
        return "CARRERA 4", "carrera_4_family", qualifier
    if value.startswith("CARRERA"):
        qualifier = value[len("CARRERA") :].strip()
        return "CARRERA", normalized_family("CARRERA", qualifier), qualifier
    raise ContractError(f"unknown_model_prefix:{prefix}")


def parse_engine_options(lines: list[str], start: int, end: int) -> list[dict[str, Any]]:
    options: list[dict[str, Any]] = []
    for index in range(start, end):
        if not re.match(r"^\s*911\s+", lines[index]):
            continue
        match = ENGINE_PATTERN.search(lines[index])
        if not match:
            continue
        prefix = lines[index][: match.start()].strip()
        model_token, family, qualifier = parse_model_prefix(prefix)
        continuations = continuation_lines(lines, index, end)
        continuation_values = [value for _, value in continuations]
        markers = parenthetical_tokens(qualifier, *continuation_values)
        values = match.groupdict()
        transmission_family = (
            "tiptronic_4_speed" if "TIPTRONIC" in qualifier else "manual_6_speed"
        )
        displacement_l = float(f"3.{values['decimal'][1:]}")
        key_fields = (index + 1, values["engine"], values["year"], values["number_prefix"])
        options.append(
            {
                "engine_option_id": stable_id("PET993-ENGINE", *key_fields),
                "model_family": family,
                "source_model_token": model_token,
                "model_year": 1900 + int(values["year"]),
                "model_year_code": values["year_code"],
                "engine_code": values["engine"],
                "transmission_family": transmission_family,
                "market_markers": markers,
                "engine_number_prefix": values["number_prefix"],
                "engine_number_start": int(values["number_start"]),
                "engine_number_end": int(values["number_end"]),
                "cylinder_count": 6,
                "displacement_l": displacement_l,
                "declared_power_kw": int(values["power_kw"]),
                "source_qualifier": qualifier or None,
                "source_evidence": {
                    "pet_source_id": PET_SOURCE_ID,
                    "summary_table": "SUMMARY ENGINES",
                    "logical_text_line_numbers": [
                        index + 1,
                        *(line_number for line_number, _ in continuations),
                    ],
                },
                "claims": {
                    "human_reviewed": False,
                    "physical_engine_verified": False,
                },
            }
        )
    options.sort(key=lambda item: item["engine_option_id"])
    if not options:
        raise ContractError("no_engine_options")
    return options


TRANSMISSION_PATTERN = re.compile(
    r"\b(?P<code>(?:G50|G64|A50)\.\d{2})\b\s+(?P<year>9[4-8])\s+"
    r"(?P<year_code>[RSTVW])\s+(?P<number_prefix>[A-Z0-9]+)\s+"
    r"(?P<variant_index>[12])\s+(?P<number_start>\d+)>(?P<number_end>\d+)\s+"
    r"(?P<speed_count>[46])-SPEED\s*$"
)


def parse_transmission_options(lines: list[str], start: int, end: int) -> list[dict[str, Any]]:
    options: list[dict[str, Any]] = []
    for index in range(start, end):
        if not re.match(r"^\s*911\s+", lines[index]):
            continue
        match = TRANSMISSION_PATTERN.search(lines[index])
        if not match:
            continue
        prefix = lines[index][: match.start()].strip()
        model_token, family, qualifier = parse_model_prefix(prefix)
        continuations = continuation_lines(lines, index, end)
        continuation_values = [value for _, value in continuations]
        markers = parenthetical_tokens(qualifier, *continuation_values)
        values = match.groupdict()
        code_compact = values["code"].replace(".", "")
        prefix_matches_code = (
            None
            if values["code"].startswith("A50")
            else values["number_prefix"].startswith(code_compact)
        )
        anomalies = (
            ["transmission_code_number_prefix_mismatch"]
            if prefix_matches_code is False
            else []
        )
        transmission_family = (
            "tiptronic_4_speed" if values["code"].startswith("A50") else "manual_6_speed"
        )
        key_fields = (
            index + 1,
            values["code"],
            values["year"],
            values["number_prefix"],
            values["variant_index"],
        )
        options.append(
            {
                "transmission_option_id": stable_id("PET993-TRANS", *key_fields),
                "model_family": family,
                "source_model_token": model_token,
                "model_year": 1900 + int(values["year"]),
                "model_year_code": values["year_code"],
                "transmission_code": values["code"],
                "transmission_family": transmission_family,
                "speed_count": int(values["speed_count"]),
                "market_markers": markers,
                "market_scope": None,
                "option_codes": option_tokens(qualifier, *continuation_values),
                "transmission_number_prefix": values["number_prefix"],
                "transmission_variant_index": int(values["variant_index"]),
                "transmission_number_start": int(values["number_start"]),
                "transmission_number_end": int(values["number_end"]),
                "code_number_prefix_matches": prefix_matches_code,
                "source_qualifier": qualifier or None,
                "source_anomalies": anomalies,
                "source_evidence": {
                    "pet_source_id": PET_SOURCE_ID,
                    "summary_table": "SUMM.TRANSMISS.",
                    "logical_text_line_numbers": [
                        index + 1,
                        *(line_number for line_number, _ in continuations),
                    ],
                },
                "claims": {
                    "human_reviewed": False,
                    "physical_transmission_verified": False,
                },
            }
        )

    grouped: dict[tuple[str, int, str], list[dict[str, Any]]] = defaultdict(list)
    for option in options:
        grouped[
            (
                option["model_family"],
                option["model_year"],
                option["transmission_family"],
            )
        ].append(option)
    for group in grouped.values():
        has_north_america = any(
            set(option["market_markers"]).intersection({"USA", "CDN", "RC"})
            for option in group
        )
        for option in group:
            markers = set(option["market_markers"])
            has_na = bool(markers.intersection({"USA", "CDN", "RC"}))
            has_other = bool(markers - {"USA", "CDN", "RC"})
            if has_na and has_other:
                option["market_scope"] = "mixed_explicit_markets"
            elif has_na:
                option["market_scope"] = "north_america"
            elif has_other:
                option["market_scope"] = "other_explicit_markets"
            elif has_north_america:
                option["market_scope"] = "rest_of_world_candidate"
            else:
                option["market_scope"] = "all_markets_unresolved"
    options.sort(key=lambda item: item["transmission_option_id"])
    if not options:
        raise ContractError("no_transmission_options")
    return options


def market_alignment(type_record: dict[str, Any], transmission: dict[str, Any]) -> str:
    type_group = type_record["market_group"]
    scope = transmission["market_scope"]
    if scope == "north_america":
        return "exact" if type_group == "north_america" else "conflict"
    if scope == "rest_of_world_candidate":
        return "conflict" if type_group == "north_america" else "candidate"
    if scope == "other_explicit_markets":
        shared = set(type_record["market_markers"]).intersection(transmission["market_markers"])
        if shared:
            return "exact"
        return "conflict" if type_group == "north_america" else "unresolved"
    if scope == "mixed_explicit_markets":
        return "unresolved"
    return "unresolved"


def build_intersections(
    type_records: list[dict[str, Any]],
    engine_options: list[dict[str, Any]],
    transmission_options: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    intersections: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    for type_record in type_records:
        engines = [
            option
            for option in engine_options
            if option["model_family"] == type_record["model_family"]
            and option["model_year"] == type_record["model_year"]
            and option["engine_code"] in type_record["engine_codes"]
        ]
        if not engines:
            gaps.append(
                {
                    "gap_id": stable_id("PET993-GAP", type_record["type_record_id"], "engine"),
                    "type_record_id": type_record["type_record_id"],
                    "missing_dimension": "engine_option",
                    "status": "requires_human_pet_review",
                }
            )
            continue
        for engine in engines:
            transmissions = []
            for option in transmission_options:
                if (
                    option["model_family"] != type_record["model_family"]
                    or option["model_year"] != type_record["model_year"]
                    or option["transmission_family"] != engine["transmission_family"]
                ):
                    continue
                alignment = market_alignment(type_record, option)
                if alignment == "conflict":
                    continue
                transmissions.append((option, alignment))
            if not transmissions:
                gaps.append(
                    {
                        "gap_id": stable_id(
                            "PET993-GAP",
                            type_record["type_record_id"],
                            engine["engine_option_id"],
                            "transmission",
                        ),
                        "type_record_id": type_record["type_record_id"],
                        "engine_option_id": engine["engine_option_id"],
                        "missing_dimension": "transmission_option",
                        "status": "requires_human_pet_review",
                    }
                )
                continue
            for transmission, alignment in transmissions:
                candidate_id = stable_id(
                    "CONFIG-CANDIDATE-993",
                    type_record["type_record_id"],
                    engine["engine_option_id"],
                    transmission["transmission_option_id"],
                )
                intersections.append(
                    {
                        "configuration_candidate_id": candidate_id,
                        "type_record_id": type_record["type_record_id"],
                        "engine_option_id": engine["engine_option_id"],
                        "transmission_option_id": transmission["transmission_option_id"],
                        "model_family": type_record["model_family"],
                        "body_style": type_record["body_style"],
                        "body_or_variant_token": type_record["body_or_variant_token"],
                        "model_year": type_record["model_year"],
                        "market_group": type_record["market_group"],
                        "engine_code": engine["engine_code"],
                        "transmission_code": transmission["transmission_code"],
                        "transmission_family": transmission["transmission_family"],
                        "market_intersection_status": alignment,
                        "derivation_status": "deterministic_pet_summary_intersection_not_human_reviewed",
                        "source_anomalies": sorted(
                            set(type_record["source_anomalies"] + transmission["source_anomalies"])
                        ),
                        "promoted_to_configured_vehicle": False,
                        "complete_vehicle_bom": False,
                        "geometry_revision": None,
                        "selected_material_set": None,
                        "reference_solver_results": 0,
                        "physicsnemo_results": 0,
                        "omniverse_simready_result": None,
                    }
                )
    intersections.sort(key=lambda item: item["configuration_candidate_id"])
    gaps.sort(key=lambda item: item["gap_id"])
    return intersections, gaps


def build_review_queue(
    type_records: list[dict[str, Any]],
    intersections: list[dict[str, Any]],
    gaps: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    type_by_id = {item["type_record_id"]: item for item in type_records}
    queue: list[dict[str, Any]] = []
    for gap in gaps:
        type_record = type_by_id[gap["type_record_id"]]
        queue.append(
            {
                "review_id": stable_id("REVIEW-993-CONFIG", gap["gap_id"]),
                "priority": "P0",
                "priority_score": 0,
                "category": "blocking_configuration_gap",
                "reason": f"missing_{gap['missing_dimension']}",
                "type_record_id": type_record["type_record_id"],
                "configuration_candidate_id": None,
                "review_status": "not_started",
                "promoted": False,
            }
        )
    for candidate in intersections:
        if candidate["model_family"] == "turbo":
            score, priority, category = 10, "P0", "first_integration_target_turbo"
        elif candidate["source_anomalies"]:
            score, priority, category = 20, "P1", "source_anomaly"
        elif candidate["body_style"] in {"Cabriolet", "Targa"}:
            score, priority, category = 30, "P1", "missing_source_vehicle_body_style"
        else:
            score, priority, category = 40, "P2", "remaining_configuration_intersection"
        queue.append(
            {
                "review_id": stable_id(
                    "REVIEW-993-CONFIG", candidate["configuration_candidate_id"]
                ),
                "priority": priority,
                "priority_score": score,
                "category": category,
                "reason": "human_review_required_before_configuration_promotion",
                "type_record_id": candidate["type_record_id"],
                "configuration_candidate_id": candidate["configuration_candidate_id"],
                "review_status": "not_started",
                "promoted": False,
            }
        )
    queue.sort(key=lambda item: (item["priority_score"], item["review_id"]))
    return queue


def build(pet_text_path: Path) -> dict[str, Any]:
    applicability = load_json(APPLICABILITY_EVIDENCE)
    axes = load_json(CONFIGURATION_AXES)
    expected_sha256 = applicability.get("source_boundary", {}).get("pet_text_sha256")
    actual_sha256 = sha256_file(pet_text_path)
    if not isinstance(expected_sha256, str) or expected_sha256 != actual_sha256:
        raise ContractError("pet_text_sha256_mismatch")
    if axes.get("scope", {}).get("complete_vehicle_configuration_count") != 0:
        raise ContractError("configuration_axes_must_fail_closed")

    lines = pet_text_path.read_text(encoding="utf-8").splitlines()
    type_start, type_end = section(lines, "SUMMARY TYPES", "EXPL.ENGINE-NO.")
    engine_start, engine_end = section(lines, "SUMMARY ENGINES", "EXPL.TRANSM.NO.")
    transmission_start, transmission_end = section(lines, "SUMM.TRANSMISS.", "LEGENDS/NOTICES")
    type_records = parse_type_records(lines, type_start, type_end)
    engine_options = parse_engine_options(lines, engine_start, engine_end)
    transmission_options = parse_transmission_options(
        lines, transmission_start, transmission_end
    )
    intersections, gaps = build_intersections(type_records, engine_options, transmission_options)
    queue = build_review_queue(type_records, intersections, gaps)
    anomaly_count = sum(bool(item["source_anomalies"]) for item in type_records) + sum(
        bool(item["source_anomalies"]) for item in transmission_options
    )
    type_ids_with_candidates = {item["type_record_id"] for item in intersections}
    body_counts = Counter(item["body_or_variant_token"] for item in type_records)
    family_counts = Counter(item["model_family"] for item in type_records)
    priority_counts = Counter(item["priority"] for item in queue)
    return {
        "$comment": (
            "Registre F0 derive des tableaux de synthese PET. Chaque candidat joint une ligne type/VIN, "
            "une ligne moteur et une ligne boite; aucune jointure n'est une configuration ou un BOM valide."
        ),
        "schema_version": "1.0.0",
        "generated_by": relative(Path(__file__).resolve()),
        "source_boundary": {
            "pet_source_id": PET_SOURCE_ID,
            "pet_text_expected_path": str(pet_text_path),
            "pet_text_sha256": actual_sha256,
            "raw_pet_text_copied": False,
            "applicability_evidence": relative(APPLICABILITY_EVIDENCE),
            "applicability_evidence_sha256": sha256_file(APPLICABILITY_EVIDENCE),
            "configuration_axes": relative(CONFIGURATION_AXES),
            "configuration_axes_sha256": sha256_file(CONFIGURATION_AXES),
        },
        "scope": {
            "type_record_count": len(type_records),
            "engine_option_count": len(engine_options),
            "transmission_option_count": len(transmission_options),
            "configuration_candidate_count": len(intersections),
            "type_records_with_candidates": len(type_ids_with_candidates),
            "type_records_without_candidates": len(type_records) - len(type_ids_with_candidates),
            "configuration_gap_count": len(gaps),
            "source_anomaly_record_count": anomaly_count,
            "human_reviewed_configuration_candidates": 0,
            "promoted_vehicle_configurations": 0,
            "complete_vehicle_configurations": 0,
            "complete_vehicle_boms": 0,
        },
        "coverage": {
            "type_records_by_body_or_variant_token": dict(sorted(body_counts.items())),
            "type_records_by_model_family": dict(sorted(family_counts.items())),
            "review_queue_by_priority": dict(sorted(priority_counts.items())),
        },
        "type_records": type_records,
        "engine_options": engine_options,
        "transmission_options": transmission_options,
        "configuration_candidates": intersections,
        "configuration_gaps": gaps,
        "review_queue": {
            "status": "generated_not_human_reviewed",
            "entry_count": len(queue),
            "recommended_batch_size": 25,
            "next_review_ids": [item["review_id"] for item in queue[:25]],
            "entries": queue,
        },
        "join_policy": {
            "required_equal_dimensions": [
                "model_family",
                "model_year",
                "engine_code_membership",
                "transmission_family",
            ],
            "market_conflicts_excluded": True,
            "unresolved_market_alignment_allowed_as_candidate": True,
            "automatic_promotion_allowed": False,
        },
        "prohibited_claims": [
            "configuration_candidate_is_vehicle_configuration",
            "summary_intersection_is_complete_vehicle_bom",
            "vin_range_proves_individual_vehicle_identity",
            "pet_power_value_is_dyno_validation",
            "unreviewed_source_anomaly_is_corrected_fact",
            "virtual_roster_authorizes_manufacturing_or_road_use",
        ],
    }


def validate_contract(contract: dict[str, Any]) -> None:
    scope = contract.get("scope", {})
    type_records = contract.get("type_records")
    engines = contract.get("engine_options")
    transmissions = contract.get("transmission_options")
    candidates = contract.get("configuration_candidates")
    gaps = contract.get("configuration_gaps")
    if not isinstance(type_records, list) or len(type_records) != scope.get("type_record_count"):
        raise ContractError("type_record_count")
    if not isinstance(engines, list) or len(engines) != scope.get("engine_option_count"):
        raise ContractError("engine_option_count")
    if not isinstance(transmissions, list) or len(transmissions) != scope.get(
        "transmission_option_count"
    ):
        raise ContractError("transmission_option_count")
    if not isinstance(candidates, list) or len(candidates) != scope.get(
        "configuration_candidate_count"
    ):
        raise ContractError("configuration_candidate_count")
    if not isinstance(gaps, list) or len(gaps) != scope.get("configuration_gap_count"):
        raise ContractError("configuration_gap_count")
    for field in (
        "human_reviewed_configuration_candidates",
        "promoted_vehicle_configurations",
        "complete_vehicle_configurations",
        "complete_vehicle_boms",
    ):
        if scope.get(field) != 0:
            raise ContractError(f"scope_overclaim:{field}")
    if contract.get("join_policy", {}).get("automatic_promotion_allowed") is not False:
        raise ContractError("automatic_promotion_must_be_blocked")
    type_ids = {item.get("type_record_id") for item in type_records}
    engine_ids = {item.get("engine_option_id") for item in engines}
    transmission_ids = {item.get("transmission_option_id") for item in transmissions}
    if None in type_ids or len(type_ids) != len(type_records):
        raise ContractError("type_record_ids")
    if None in engine_ids or len(engine_ids) != len(engines):
        raise ContractError("engine_option_ids")
    if None in transmission_ids or len(transmission_ids) != len(transmissions):
        raise ContractError("transmission_option_ids")
    candidate_ids: set[str] = set()
    for candidate in candidates:
        candidate_id = candidate.get("configuration_candidate_id")
        if not isinstance(candidate_id, str) or candidate_id in candidate_ids:
            raise ContractError(f"configuration_candidate_id:{candidate_id}")
        candidate_ids.add(candidate_id)
        if candidate.get("type_record_id") not in type_ids:
            raise ContractError(f"candidate_type_record:{candidate_id}")
        if candidate.get("engine_option_id") not in engine_ids:
            raise ContractError(f"candidate_engine_option:{candidate_id}")
        if candidate.get("transmission_option_id") not in transmission_ids:
            raise ContractError(f"candidate_transmission_option:{candidate_id}")
        if candidate.get("promoted_to_configured_vehicle") is not False:
            raise ContractError(f"candidate_promotion:{candidate_id}")
        if candidate.get("complete_vehicle_bom") is not False:
            raise ContractError(f"candidate_complete_bom:{candidate_id}")
        for field in ("geometry_revision", "selected_material_set", "omniverse_simready_result"):
            if candidate.get(field) is not None:
                raise ContractError(f"candidate_engineering_overclaim:{candidate_id}:{field}")
        for field in ("reference_solver_results", "physicsnemo_results"):
            if candidate.get(field) != 0:
                raise ContractError(f"candidate_solver_overclaim:{candidate_id}:{field}")
    roster = contract.get("review_queue", {})
    queue = roster.get("entries")
    if not isinstance(queue, list) or roster.get("entry_count") != len(queue):
        raise ContractError("review_queue_count")
    if len(queue) != len(candidates) + len(gaps):
        raise ContractError("review_queue_coverage")
    if any(item.get("review_status") != "not_started" or item.get("promoted") is not False for item in queue):
        raise ContractError("review_queue_overclaim")
    if any(
        item.get("configuration_candidate_id") is not None
        and item.get("configuration_candidate_id") not in candidate_ids
        for item in queue
    ):
        raise ContractError("review_queue_candidate_reference")
    mismatch_rows = [
        item for item in transmissions if item.get("code_number_prefix_matches") is False
    ]
    if len(mismatch_rows) != 1 or mismatch_rows[0].get("transmission_code") != "G64.42":
        raise ContractError("expected_single_g64_42_source_anomaly")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--check-index", action="store_true")
    parser.add_argument("--pet-text", type=Path, default=DEFAULT_PET_TEXT)
    args = parser.parse_args(argv)
    try:
        if args.check_index:
            validate_contract(load_json(OUTPUT))
            print(f"valid {relative(OUTPUT)}")
            return 0
        contract = build(args.pet_text)
        validate_contract(contract)
        expected = render_json(contract)
        if args.write:
            OUTPUT.parent.mkdir(parents=True, exist_ok=True)
            OUTPUT.write_text(expected, encoding="utf-8")
            print(f"wrote {relative(OUTPUT)}")
            return 0
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != expected:
            print(f"stale:{OUTPUT}", file=sys.stderr)
            return 1
        print(f"current {relative(OUTPUT)}")
        return 0
    except ContractError as exc:
        print(f"993 configuration roster error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
