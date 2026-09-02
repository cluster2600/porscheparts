#!/usr/bin/env python3
"""Build source-bounded F14 dimension guides, never engine solids."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any


EXPECTED_VARIANTS = {
    "type_912_4_5_na": {
        "branch_role": "requested_naturally_aspirated_baseline",
        "facts": {
            "cylinder_count": (12, "count"),
            "bore_diameter_mm": (85.0, "mm"),
            "stroke_mm": (66.0, "mm"),
            "documented_displacement_cm3": (4494.0, "cm3"),
            "regular_cylinder_pitch_mm": (118.0, "mm"),
            "intake_valve_head_diameter_mm": (47.5, "mm"),
            "exhaust_valve_head_diameter_mm": (40.5, "mm"),
        },
    },
    "917_5_0_na_4999": {
        "branch_role": "scan_comparison_candidate_not_selected",
        "facts": {
            "cylinder_count": (12, "count"),
            "bore_diameter_mm": (86.8, "mm"),
            "stroke_mm": (70.4, "mm"),
            "documented_displacement_cm3": (4999.0, "cm3"),
        },
    },
    "917_30_turbo_5374": {
        "branch_role": "requested_turbo_baseline",
        "facts": {
            "cylinder_count": (12, "count"),
            "bore_diameter_mm": (90.0, "mm"),
            "stroke_mm": (70.4, "mm"),
            "documented_displacement_cm3": (5374.0, "cm3"),
            "turbocharger_count": (2, "count"),
        },
    },
}

EXPECTED_STUD_FACTS = {
    "stud_count": (48, "count"),
    "shaft_diameter_mm": (9.0, "mm"),
    "free_length_mm": (149.5, "mm"),
    "mass_each_g": (65.0, "g"),
}

ALLOWED_GUIDES = {
    "bore_diameter_mm": "diameter_circle",
    "stroke_mm": "length_segment",
    "regular_cylinder_pitch_mm": "length_segment",
    "intake_valve_head_diameter_mm": "diameter_circle",
    "exhaust_valve_head_diameter_mm": "diameter_circle",
    "shaft_diameter_mm": "diameter_circle",
    "free_length_mm": "length_segment",
}

FORBIDDEN_CONTRACT_KEYS = {
    "layout_hypotheses",
    "translation_mm",
    "rotation_xyz_deg",
    "position_mm",
    "center_mm",
    "interface_frame_mm",
    "envelope_mm",
}

REQUIRED_PROHIBITIONS = {
    "treating_a_guide_curve_as_an_engine_component",
    "scaling_or_identifying_the_scan_from_published_dimensions",
    "placing_cylinders_studs_valves_or_turbos_without_measured_frames",
    "creating_pistons_rods_crankshafts_heads_ducts_or_turbos_from_incomplete_dimensions",
    "authoring_physics_joints_contacts_or_flow_boundaries",
    "functional_polymer_or_metal_manufacture",
    "claiming_engine_function_power_durability_or_1600_hp_proof",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fact_map(facts: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for fact in facts:
        fact_id = fact.get("fact_id")
        if not isinstance(fact_id, str) or not fact_id:
            continue
        if fact_id in result:
            raise ValueError(f"duplicate fact_id: {fact_id}")
        result[fact_id] = fact
    return result


def walk_keys(value: Any):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_keys(child)


def validate_sources(
    contract: dict[str, Any], root: Path, errors: list[str]
) -> list[dict[str, Any]]:
    records = contract.get("source_registry")
    if not isinstance(records, list) or not records:
        errors.append("source_registry: at least one source is required")
        return []

    verified: list[dict[str, Any]] = []
    seen: set[str] = set()
    root_resolved = root.resolve()
    for index, record in enumerate(records):
        prefix = f"source_registry[{index}]"
        source_id = record.get("source_id")
        relative = record.get("path")
        expected_url = record.get("expected_url")
        expected_sha256 = record.get("expected_sha256")
        tokens = record.get("claim_tokens")
        if not isinstance(source_id, str) or not source_id:
            errors.append(f"{prefix}.source_id: required")
            continue
        if source_id in seen:
            errors.append(f"{prefix}.source_id: duplicate {source_id}")
        seen.add(source_id)
        if not isinstance(relative, str) or not relative:
            errors.append(f"{prefix}.path: required")
            continue
        if not isinstance(expected_url, str) or not expected_url:
            errors.append(f"{prefix}.expected_url: required")
        if not isinstance(expected_sha256, str) or not re.fullmatch(
            r"[0-9a-f]{64}", expected_sha256
        ):
            errors.append(f"{prefix}.expected_sha256: lowercase SHA-256 required")
        candidate = (root / relative).resolve()
        try:
            candidate.relative_to(root_resolved)
        except ValueError:
            errors.append(f"{prefix}.path: must remain inside repository")
            continue
        if not candidate.is_file():
            errors.append(f"{prefix}.path: missing {relative}")
            continue
        try:
            payload = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{prefix}.path: unreadable source record: {exc}")
            continue
        if payload.get("source_id") != source_id:
            errors.append(f"{prefix}: source_id does not match source record")
        actual_url = payload.get("url")
        if actual_url != expected_url:
            errors.append(f"{prefix}: url does not match expected_url pin")
        actual_sha256 = sha256(candidate)
        if actual_sha256 != expected_sha256:
            errors.append(f"{prefix}: sha256 does not match expected_sha256 pin")
        if payload.get("quality", {}).get("evidence_level") != record.get(
            "evidence_grade"
        ):
            errors.append(f"{prefix}: evidence_grade does not match source record")
        if not isinstance(tokens, list) or not tokens or not all(
            isinstance(token, str) and token for token in tokens
        ):
            errors.append(f"{prefix}.claim_tokens: non-empty strings required")
            tokens = []
        notes = payload.get("notes", "")
        for token in tokens:
            if token not in notes:
                errors.append(f"{prefix}: claim token absent from source notes: {token}")
        verified.append(
            {
                "source_id": source_id,
                "path": relative,
                "url": actual_url,
                "sha256": actual_sha256,
                "evidence_grade": record.get("evidence_grade"),
                "claim_tokens_verified": list(tokens),
            }
        )
    return verified


def validate_facts(
    scope: str,
    facts: list[dict[str, Any]],
    expected: dict[str, tuple[float | int, str]],
    known_sources: set[str],
    errors: list[str],
) -> dict[str, dict[str, Any]]:
    try:
        mapped = fact_map(facts)
    except ValueError as exc:
        errors.append(f"{scope}: {exc}")
        return {}
    if set(mapped) != set(expected):
        errors.append(
            f"{scope}.facts: expected {sorted(expected)}, got {sorted(mapped)}"
        )
    for fact_id, (expected_value, expected_unit) in expected.items():
        fact = mapped.get(fact_id)
        if fact is None:
            continue
        if fact.get("value") != expected_value or fact.get("unit") != expected_unit:
            errors.append(
                f"{scope}.{fact_id}: expected {expected_value} {expected_unit}"
            )
        source_ids = fact.get("source_ids")
        if not isinstance(source_ids, list) or not source_ids:
            errors.append(f"{scope}.{fact_id}.source_ids: non-empty list required")
        elif any(source_id not in known_sources for source_id in source_ids):
            errors.append(f"{scope}.{fact_id}.source_ids: unknown source")
        if fact.get("manufacturing_dimension") is not False:
            errors.append(f"{scope}.{fact_id}: must not be a manufacturing dimension")
    return mapped


def validate_guides(
    scope: str,
    guides: list[dict[str, Any]],
    facts: dict[str, dict[str, Any]],
    errors: list[str],
) -> None:
    if not isinstance(guides, list):
        errors.append(f"{scope}.guides: list required")
        return
    seen: set[str] = set()
    for guide in guides:
        guide_id = guide.get("guide_id")
        fact_id = guide.get("fact_id")
        primitive = guide.get("primitive")
        if not isinstance(guide_id, str) or not guide_id:
            errors.append(f"{scope}.guides: guide_id required")
            continue
        if guide_id in seen:
            errors.append(f"{scope}.guides: duplicate guide_id {guide_id}")
        seen.add(guide_id)
        if fact_id not in facts:
            errors.append(f"{scope}.{guide_id}: unknown fact_id {fact_id}")
            continue
        if ALLOWED_GUIDES.get(fact_id) != primitive:
            errors.append(f"{scope}.{guide_id}: invalid primitive for {fact_id}")


def validate_contract(
    contract: dict[str, Any], root: Path
) -> tuple[list[str], list[dict[str, Any]]]:
    errors: list[str] = []
    if contract.get("schema_version") != "1.0.0":
        errors.append("schema_version: expected 1.0.0")
    if contract.get("phase") != "F14":
        errors.append("phase: expected F14")
    if contract.get("status") != "dimension_guides_only_source_bounded":
        errors.append("status: unexpected")
    if contract.get("verified_engine_level_after_generation") != "F0_source_integrity":
        errors.append("verified_engine_level_after_generation: must remain F0_source_integrity")

    used_forbidden = FORBIDDEN_CONTRACT_KEYS.intersection(set(walk_keys(contract)))
    if used_forbidden:
        errors.append(f"forbidden placement or layout keys: {sorted(used_forbidden)}")

    policy = contract.get("authoring_policy", {})
    required_policy = {
        "geometry_kind": "dimension_curves_and_unplaced_placeholders_only",
        "source_values_only": True,
        "metric_guides_are_not_scan_scale": True,
        "scan_geometry_consumed": False,
        "scan_units_converted_to_mm": False,
        "engine_component_solids_allowed": False,
        "maximum_solid_count": 0,
        "component_placement_allowed": False,
        "physics_schemas_allowed": False,
        "material_assignment_allowed": False,
        "manufacturing_tolerances_allowed": False,
        "step_scope_if_requested": "wire_guides_only",
    }
    if policy != required_policy:
        errors.append("authoring_policy: exact fail-closed policy required")

    verified_sources = validate_sources(contract, root, errors)
    known_sources = {item["source_id"] for item in verified_sources}

    variants = contract.get("variants")
    if not isinstance(variants, list):
        errors.append("variants: list required")
        variants = []
    mapped_variants = {
        item.get("variant_id"): item
        for item in variants
        if isinstance(item, dict) and isinstance(item.get("variant_id"), str)
    }
    if set(mapped_variants) != set(EXPECTED_VARIANTS):
        errors.append(
            f"variants: expected {sorted(EXPECTED_VARIANTS)}, got {sorted(mapped_variants)}"
        )
    if len(mapped_variants) != len(variants):
        errors.append("variants: duplicate or malformed variant_id")

    for variant_id, expected in EXPECTED_VARIANTS.items():
        variant = mapped_variants.get(variant_id)
        if variant is None:
            continue
        if variant.get("branch_role") != expected["branch_role"]:
            errors.append(f"variants.{variant_id}.branch_role: unexpected")
        if "not_identified" not in variant.get("identity_status", ""):
            errors.append(f"variants.{variant_id}.identity_status: scan identity must remain open")
        facts = validate_facts(
            f"variants.{variant_id}",
            variant.get("facts", []),
            expected["facts"],
            known_sources,
            errors,
        )
        validate_guides(f"variants.{variant_id}", variant.get("guides"), facts, errors)
        families = variant.get("unplaced_families")
        if not isinstance(families, list) or not families:
            errors.append(f"variants.{variant_id}.unplaced_families: required")
            continue
        for family in families:
            if family.get("placement_status") != "unknown_unplaced":
                errors.append(f"variants.{variant_id}: every family must remain unplaced")
            count_fact = facts.get(family.get("count_fact_id"))
            if not count_fact or count_fact.get("unit") != "count":
                errors.append(f"variants.{variant_id}: family count must reference a count fact")

    stud = contract.get("shared_references", {}).get("head_stud_reference", {})
    stud_facts = validate_facts(
        "shared_references.head_stud_reference",
        stud.get("facts", []),
        EXPECTED_STUD_FACTS,
        known_sources,
        errors,
    )
    validate_guides(
        "shared_references.head_stud_reference",
        stud.get("guides"),
        stud_facts,
        errors,
    )
    if stud.get("candidate_scope") != "917_engine_presented_for_1970":
        errors.append("head_stud_reference.candidate_scope: must remain narrow")
    if stud.get("assigned_variant_ids") != []:
        errors.append("head_stud_reference.assigned_variant_ids: must remain empty")
    if stud.get("automatic_turbo_application_allowed") is not False:
        errors.append("head_stud_reference: turbo application must remain blocked")
    if stud.get("placement_status") != "unknown_unplaced":
        errors.append("head_stud_reference: placement must remain unknown")
    for field in (
        "placement_coordinates_mm",
        "thread_geometry",
        "end_geometry",
        "sleeve_geometry",
    ):
        if stud.get(field) is not None:
            errors.append(f"head_stud_reference.{field}: must remain null")
    stud_family = stud.get("unplaced_family", {})
    if (
        stud_family.get("placement_status") != "unknown_unplaced"
        or stud_family.get("count_fact_id") != "stud_count"
    ):
        errors.append("head_stud_reference.unplaced_family: invalid")

    gates = contract.get("release_gates")
    if not isinstance(gates, dict) or not gates or any(value is not False for value in gates.values()):
        errors.append("release_gates: every gate must be explicitly false")
    prohibitions = set(contract.get("prohibited_uses", []))
    if not REQUIRED_PROHIBITIONS.issubset(prohibitions):
        errors.append("prohibited_uses: required fail-closed claims are missing")
    return errors, verified_sources


def usd_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=True)


def circle_points(diameter: float, samples: int = 64) -> list[tuple[float, float, float]]:
    radius = diameter / 2.0
    return [
        (
            radius * math.cos(2.0 * math.pi * index / samples),
            radius * math.sin(2.0 * math.pi * index / samples),
            0.0,
        )
        for index in range(samples + 1)
    ]


def format_points(points: list[tuple[float, float, float]]) -> str:
    return ",\n                    ".join(
        f"({x:.9f}, {y:.9f}, {z:.9f})" for x, y, z in points
    )


def guide_usda(guide: dict[str, Any], facts: dict[str, dict[str, Any]], indent: str) -> list[str]:
    fact = facts[guide["fact_id"]]
    value = float(fact["value"])
    source_json = json.dumps(fact["source_ids"], separators=(",", ":"))
    name = guide["guide_id"]
    if guide["primitive"] == "diameter_circle":
        points = circle_points(value)
    else:
        points = [(0.0, 0.0, 0.0), (value, 0.0, 0.0)]
    lines = [
        f'{indent}def BasisCurves "{name}" (',
        f"{indent}    customData = {{",
        f'{indent}        string "3dprinting993:classification" = "published_reference_guide_not_component"',
        f'{indent}        string "3dprinting993:factId" = {usd_string(guide["fact_id"])}',
        f'{indent}        string "3dprinting993:sourceIdsJson" = {usd_string(source_json)}',
        f'{indent}        string "3dprinting993:unit" = {usd_string(fact["unit"])}',
        f'{indent}        double "3dprinting993:value" = {value:.9f}',
        f"{indent}    }}",
        f"{indent})",
        f"{indent}{{",
        f"{indent}    int[] curveVertexCounts = [{len(points)}]",
        f"{indent}    point3f[] points = [",
        f"{indent}        {format_points(points)}",
        f"{indent}    ]",
        f'{indent}    uniform token purpose = "guide"',
        f'{indent}    uniform token type = "linear"',
        f'{indent}    uniform token wrap = "nonperiodic"',
        f"{indent}    float[] widths = [0.6]",
        f"{indent}}}",
    ]
    return lines


def placeholder_usda(
    name: str,
    family: str,
    index: int,
    source_scope: str,
    indent: str,
) -> list[str]:
    return [
        f'{indent}def Xform "{name}_{index:02d}" (',
        f"{indent}    customData = {{",
        f'{indent}        string "3dprinting993:family" = {usd_string(family)}',
        f'{indent}        string "3dprinting993:placementStatus" = "unknown_unplaced"',
        f'{indent}        string "3dprinting993:sourceScope" = {usd_string(source_scope)}',
        f"{indent}    }}",
        f"{indent})",
        f"{indent}{{",
        f"{indent}}}",
    ]


def build_usda(contract: dict[str, Any]) -> tuple[str, dict[str, int]]:
    lines = [
        "#usda 1.0",
        "(",
        '    defaultPrim = "F14DimensionalSkeleton"',
        "    metersPerUnit = 0.001",
        '    upAxis = "Z"',
        ")",
        "",
        'def Xform "F14DimensionalSkeleton" (',
        "    customData = {",
        '        string "3dprinting993:classification" = "dimension_guides_only_no_engine_solids"',
        '        string "3dprinting993:phase" = "F14"',
        '        string "3dprinting993:verifiedEngineLevel" = "F0_source_integrity"',
        "    }",
        '    kind = "assembly"',
        ")",
        "{",
        '    def Scope "Variants"',
        "    {",
    ]
    guide_count = 0
    cylinder_placeholders = 0
    turbo_placeholders = 0
    for variant in contract["variants"]:
        variant_id = variant["variant_id"]
        facts = fact_map(variant["facts"])
        lines.extend(
            [
                f'        def Xform "V_{variant_id}" (',
                "            customData = {",
                f'                string "3dprinting993:branchRole" = {usd_string(variant["branch_role"])}',
                f'                string "3dprinting993:identityStatus" = {usd_string(variant["identity_status"])}',
                '                string "3dprinting993:placementStatus" = "unknown_unplaced"',
                "            }",
                "        )",
                "        {",
                '            def Scope "DimensionGuides"',
                "            {",
            ]
        )
        for guide in variant["guides"]:
            lines.extend(guide_usda(guide, facts, "                "))
            guide_count += 1
        lines.extend(
            [
                "            }",
                '            def Scope "UnplacedOccurrences"',
                "            {",
            ]
        )
        for family in variant["unplaced_families"]:
            count = int(facts[family["count_fact_id"]]["value"])
            short_name = (
                "Cylinder"
                if family["family"] == "cylinder_axis_placeholder"
                else "Turbocharger"
            )
            for index in range(1, count + 1):
                lines.extend(
                    placeholder_usda(
                        short_name,
                        family["family"],
                        index,
                        variant_id,
                        "                ",
                    )
                )
            if short_name == "Cylinder":
                cylinder_placeholders += count
            else:
                turbo_placeholders += count
        lines.extend(["            }", "        }"])
    lines.extend(["    }"])

    stud = contract["shared_references"]["head_stud_reference"]
    stud_facts = fact_map(stud["facts"])
    lines.extend(
        [
            '    def Scope "UnplacedSharedReferences"',
            "    {",
            '        def Xform "HeadStudReference" (',
            "            customData = {",
            f'                string "3dprinting993:candidateScope" = {usd_string(stud["candidate_scope"])}',
            '                string "3dprinting993:placementStatus" = "unknown_unplaced"',
            '                string "3dprinting993:variantAssignment" = "none"',
            "            }",
            "        )",
            "        {",
            '            def Scope "DimensionGuides"',
            "            {",
        ]
    )
    for guide in stud["guides"]:
        lines.extend(guide_usda(guide, stud_facts, "                "))
        guide_count += 1
    lines.extend(
        [
            "            }",
            '            def Scope "UnplacedOccurrences"',
            "            {",
        ]
    )
    stud_count = int(stud_facts["stud_count"]["value"])
    for index in range(1, stud_count + 1):
        lines.extend(
            placeholder_usda(
                "HeadStud",
                "head_stud_reference_placeholder",
                index,
                stud["candidate_scope"],
                "                ",
            )
        )
    lines.extend(["            }", "        }", "    }", "}", ""])
    return "\n".join(lines), {
        "guide_curve_count": guide_count,
        "cylinder_placeholder_count": cylinder_placeholders,
        "turbocharger_placeholder_count": turbo_placeholders,
        "head_stud_placeholder_count": stud_count,
        "solid_count": 0,
        "placed_occurrence_count": 0,
    }


def write_optional_step(
    contract: dict[str, Any], output: Path
) -> dict[str, Any]:
    try:
        from build123d import Compound, Edge, Vector, export_step
    except ImportError as exc:
        return {
            "status": "requested_but_build123d_unavailable",
            "output": None,
            "reason": str(exc),
            "solid_count": 0,
        }

    edges = []
    for variant in contract["variants"]:
        facts = fact_map(variant["facts"])
        for guide in variant["guides"]:
            value = float(facts[guide["fact_id"]]["value"])
            if guide["primitive"] == "diameter_circle":
                edges.append(Edge.make_circle(value / 2.0))
            else:
                edges.append(Edge.make_line(Vector(0, 0, 0), Vector(value, 0, 0)))
    stud = contract["shared_references"]["head_stud_reference"]
    stud_facts = fact_map(stud["facts"])
    for guide in stud["guides"]:
        value = float(stud_facts[guide["fact_id"]]["value"])
        if guide["primitive"] == "diameter_circle":
            edges.append(Edge.make_circle(value / 2.0))
        else:
            edges.append(Edge.make_line(Vector(0, 0, 0), Vector(value, 0, 0)))
    export_step(
        Compound(children=edges, label="917 F14 DIMENSION GUIDES - NO ENGINE SOLIDS"),
        output,
    )
    return {
        "status": "wire_guides_generated",
        "output": str(output.resolve()),
        "edge_count": len(edges),
        "solid_count": 0,
        "fabrication_released": False,
    }


def build_report(
    contract_path: Path,
    verified_sources: list[dict[str, Any]],
    output_dir: Path,
    usd_counts: dict[str, int],
    step: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "phase": "F14",
        "status": "generated_dimension_guides_only",
        "classification": "source_bounded_guides_not_engine_geometry",
        "contract": {
            "path": str(contract_path.resolve()),
            "sha256": sha256(contract_path),
        },
        "sources": verified_sources,
        "outputs": {
            "usd": str((output_dir / "917-dimensional-skeleton-f14.usda").resolve()),
            "step": step,
        },
        "variant_ids": list(EXPECTED_VARIANTS),
        "geometry_counts": usd_counts,
        "units": {
            "published_reference_guides": "mm",
            "scan_scale_applied": False,
            "scan_geometry_consumed": False,
        },
        "release": {
            "scan_identity_confirmed": False,
            "scan_metric_scale_confirmed": False,
            "engine_geometry_released": False,
            "physics_released": False,
            "functional_release": False,
            "polymer_print_release": False,
            "metal_print_release": False,
            "manufacturing_release": False,
        },
        "verified_engine_level_after_generation": "F0_source_integrity",
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    root = repo_root()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--contract",
        type=Path,
        default=root / "twins/reference-917-engine/dimensional-skeleton-f14.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=root / "work/917-dimensional-skeleton-f14",
    )
    parser.add_argument(
        "--optional-step",
        action="store_true",
        help="Export wire guides to STEP when build123d is installed.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        contract = json.loads(args.contract.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "failed", "errors": [str(exc)]}, indent=2), file=sys.stderr)
        return 2
    errors, verified_sources = validate_contract(contract, repo_root())
    if errors:
        print(json.dumps({"status": "failed", "errors": errors}, indent=2), file=sys.stderr)
        return 2

    usda, counts = build_usda(contract)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    usd_path = args.output_dir / "917-dimensional-skeleton-f14.usda"
    usd_path.write_text(usda, encoding="utf-8")

    step: dict[str, Any] = {
        "status": "not_requested",
        "output": None,
        "solid_count": 0,
    }
    if args.optional_step:
        step = write_optional_step(
            contract, args.output_dir / "917-dimensional-skeleton-f14-guides.step"
        )
    report = build_report(
        args.contract, verified_sources, args.output_dir, counts, step
    )
    report_path = args.output_dir / "917-dimensional-skeleton-f14.report.json"
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
