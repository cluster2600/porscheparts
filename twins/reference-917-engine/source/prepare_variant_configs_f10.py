#!/usr/bin/env python3
"""Validate F10 and materialize two explicit, non-manufacturing variant configs."""

from __future__ import annotations

import argparse
import copy
import json
import math
import re
from pathlib import Path
from typing import Any


EXPECTED_VARIANTS = {"type_912_4_5_na", "917_30_turbo_5374"}
EXPECTED_STATUS = "separate_sourced_variant_geometry_and_visual_kinematics_not_manufacturing_geometry"
REQUIRED_EVIDENCE_FIELDS = {
    "cylinder_count",
    "bore_mm",
    "stroke_mm",
    "documented_displacement_cm3",
}
CONFIG_READINESS_GATES = {
    "separate_visual_geometry_config_ready",
    "separate_visual_kinematics_config_ready",
}
PHYSICAL_RELEASE_GATES = {
    "measured_variant_geometry_ready",
    "physical_kinematics_ready",
    "manufacturing_geometry_ready",
    "clearance_validation_ready",
    "combustion_simulation_ready",
    "performance_claim_authorized",
}
EXPECTED_RELEASE_GATES = CONFIG_READINESS_GATES | PHYSICAL_RELEASE_GATES
REQUIRED_PROHIBITIONS = {
    "manufacturing_release",
    "claim_that_visual_hypotheses_are_factory_dimensions",
    "clearance_or_interference_release",
    "combustion_power_torque_or_durability_claim",
    "claim_that_F10_proves_1600_hp",
    "metal_print_or_engine_test_release",
}
FIELD_SOURCE_SUPPORT = {
    "cylinder_count": {
        "SRC-AMS-917-ENGINE-TECHNICAL-ANALYSIS",
        "SRC-KFZ-TECH-917-TYPE912-ENGINE",
        "SRC-PORSCHE-NEWSROOM-91730-TURBO",
    },
    "bore_mm": {
        "SRC-AMS-917-ENGINE-TECHNICAL-ANALYSIS",
        "SRC-KFZ-TECH-917-TYPE912-ENGINE",
        "SRC-STUTTCARS-917-TECHNICAL-DETAILS",
    },
    "stroke_mm": {
        "SRC-AMS-917-ENGINE-TECHNICAL-ANALYSIS",
        "SRC-KFZ-TECH-917-TYPE912-ENGINE",
        "SRC-STUTTCARS-917-TECHNICAL-DETAILS",
    },
    "documented_displacement_cm3": {
        "SRC-AMS-917-ENGINE-TECHNICAL-ANALYSIS",
        "SRC-PORSCHE-NEWSROOM-91730-TURBO",
    },
}
EXPECTED_VARIANT_GEOMETRY = {
    "type_912_4_5_na": {
        "values": {
            "cylinder_count": 12,
            "bore_mm": 85.0,
            "stroke_mm": 66.0,
            "documented_displacement_cm3": 4494.0,
        },
        "field_evidence": {
            "cylinder_count": {
                "SRC-AMS-917-ENGINE-TECHNICAL-ANALYSIS",
                "SRC-KFZ-TECH-917-TYPE912-ENGINE",
            },
            "bore_mm": {
                "SRC-AMS-917-ENGINE-TECHNICAL-ANALYSIS",
                "SRC-KFZ-TECH-917-TYPE912-ENGINE",
                "SRC-STUTTCARS-917-TECHNICAL-DETAILS",
            },
            "stroke_mm": {
                "SRC-AMS-917-ENGINE-TECHNICAL-ANALYSIS",
                "SRC-KFZ-TECH-917-TYPE912-ENGINE",
                "SRC-STUTTCARS-917-TECHNICAL-DETAILS",
            },
            "documented_displacement_cm3": {
                "SRC-AMS-917-ENGINE-TECHNICAL-ANALYSIS",
            },
        },
    },
    "917_30_turbo_5374": {
        "values": {
            "cylinder_count": 12,
            "bore_mm": 90.0,
            "stroke_mm": 70.4,
            "documented_displacement_cm3": 5374.0,
        },
        "field_evidence": {
            "cylinder_count": {
                "SRC-PORSCHE-NEWSROOM-91730-TURBO",
                "SRC-AMS-917-ENGINE-TECHNICAL-ANALYSIS",
            },
            "bore_mm": {
                "SRC-AMS-917-ENGINE-TECHNICAL-ANALYSIS",
            },
            "stroke_mm": {
                "SRC-AMS-917-ENGINE-TECHNICAL-ANALYSIS",
            },
            "documented_displacement_cm3": {
                "SRC-PORSCHE-NEWSROOM-91730-TURBO",
            },
        },
    },
}
SAFE_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def calculated_displacement_cm3(cylinders: int, bore_mm: float, stroke_mm: float) -> float:
    return math.pi / 4.0 * bore_mm**2 * stroke_mm * cylinders / 1000.0


def stage_provenance_payload(
    variant_id: str,
    documented_displacement_cm3: float,
    field_evidence: dict[str, list[str]],
) -> dict[str, Any]:
    """Return the exact documentary payload that every F10 USD stage must carry."""
    return {
        "variant_id": variant_id,
        "documented_displacement_cm3": documented_displacement_cm3,
        "field_evidence": {
            field: sorted(source_ids) for field, source_ids in sorted(field_evidence.items())
        },
    }


def evaluate_stage_provenance(
    expected: dict[str, Any],
    *,
    documented_displacement_cm3: Any,
    calculated_displacement_cm3: Any,
    field_evidence_json: Any,
    expected_calculated_displacement_cm3: float,
) -> dict[str, Any]:
    """Compare USD documentary metadata to an immutable F10 expectation."""
    try:
        field_evidence = (
            json.loads(field_evidence_json) if isinstance(field_evidence_json, str) else None
        )
    except json.JSONDecodeError:
        field_evidence = None
    calculated_is_number = type(calculated_displacement_cm3) in (int, float)
    return {
        "documented_displacement": {
            "passed": documented_displacement_cm3
            == expected["documented_displacement_cm3"],
            "actual": documented_displacement_cm3,
            "expected": expected["documented_displacement_cm3"],
        },
        "calculated_displacement": {
            "passed": calculated_is_number
            and abs(calculated_displacement_cm3 - expected_calculated_displacement_cm3)
            <= 1e-9,
            "actual": calculated_displacement_cm3,
            "expected": expected_calculated_displacement_cm3,
        },
        "field_evidence_exact": {
            "passed": field_evidence == expected["field_evidence"],
            "actual": field_evidence,
            "expected": expected["field_evidence"],
        },
    }


def source_registry(project_root: Path) -> set[str]:
    result: set[str] = set()
    for path in (project_root / "catalog" / "sources").glob("*.json"):
        try:
            source_id = load_json(path).get("source_id")
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(source_id, str):
            result.add(source_id)
    return result


def _variants_by_id(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    variants = manifest.get("variants", [])
    if not isinstance(variants, list):
        return {}
    return {
        item.get("variant_id"): item
        for item in variants
        if isinstance(item, dict) and isinstance(item.get("variant_id"), str)
    }


def validate_contract(manifest: dict[str, Any], project_root: Path) -> list[str]:
    errors: list[str] = []
    if manifest.get("phase") != "F10":
        errors.append("phase: expected F10")
    if manifest.get("status") != EXPECTED_STATUS:
        errors.append(f"status: expected {EXPECTED_STATUS}")
    if manifest.get("units") != "mm":
        errors.append("units: expected mm")

    policy = manifest.get("stage_policy", {})
    if policy.get("mode") != "one_geometry_and_kinematic_stage_per_variant":
        errors.append("stage_policy.mode: variants must use separate stages")
    if policy.get("engine_variant_set_allowed") is not False:
        errors.append("stage_policy.engine_variant_set_allowed: must be false")
    if policy.get("shared_85x66_core_between_variants_allowed") is not False:
        errors.append("stage_policy.shared_85x66_core_between_variants_allowed: must be false")
    if policy.get("generated_outputs_root") != "work/917-variant-geometry-f10":
        errors.append("stage_policy.generated_outputs_root: must remain under the canonical work directory")

    upstream = manifest.get("upstream_contracts", {})
    upstream_docs: dict[str, dict[str, Any]] = {}
    for key in ("base_geometry", "base_kinematics", "detail_families", "turbo_performance_envelope"):
        relative = upstream.get(key)
        if not isinstance(relative, str):
            errors.append(f"upstream_contracts.{key}: missing path")
            continue
        path = project_root / relative
        if not path.is_file():
            errors.append(f"upstream_contracts.{key}: file does not exist")
            continue
        try:
            upstream_docs[key] = load_json(path)
        except json.JSONDecodeError:
            errors.append(f"upstream_contracts.{key}: invalid JSON")

    variants = _variants_by_id(manifest)
    if set(variants) != EXPECTED_VARIANTS:
        errors.append(f"variants: expected exactly {sorted(EXPECTED_VARIANTS)}")
    if len(manifest.get("variants", [])) != len(variants):
        errors.append("variants: duplicate or invalid variant_id")

    known_sources = source_registry(project_root)
    output_paths: list[str] = []
    output_slugs: list[str] = []
    for variant_id, variant in variants.items():
        slug = variant.get("output_slug")
        if not isinstance(slug, str) or not SAFE_SLUG.fullmatch(slug):
            errors.append(f"variants.{variant_id}.output_slug: must be a safe lowercase slug")
            slug = ""
        else:
            output_slugs.append(slug)
        geometry = variant.get("geometry", {})
        cylinders = geometry.get("cylinder_count")
        bore = geometry.get("bore_mm")
        stroke = geometry.get("stroke_mm")
        documented = geometry.get("documented_displacement_cm3")
        if not all(isinstance(value, (int, float)) and value > 0 for value in (cylinders, bore, stroke, documented)):
            errors.append(f"variants.{variant_id}.geometry: positive numeric dimensions are required")
        else:
            if cylinders != 12:
                errors.append(f"variants.{variant_id}.geometry.cylinder_count: must be 12")
            calculated = calculated_displacement_cm3(int(cylinders), float(bore), float(stroke))
            if abs(calculated - float(documented)) / float(documented) > 0.001:
                errors.append(f"variants.{variant_id}.geometry: documented displacement differs by more than 0.1%")

        evidence = geometry.get("field_evidence", {})
        if set(evidence) != REQUIRED_EVIDENCE_FIELDS:
            errors.append(f"variants.{variant_id}.geometry.field_evidence: incomplete field mapping")
        for field in REQUIRED_EVIDENCE_FIELDS:
            ids = evidence.get(field, [])
            if not isinstance(ids, list) or not ids:
                errors.append(f"variants.{variant_id}.geometry.field_evidence.{field}: at least one source is required")
                continue
            unknown = sorted(set(ids) - known_sources)
            if unknown:
                errors.append(f"variants.{variant_id}.geometry.field_evidence.{field}: unknown sources {unknown}")
            incompatible = sorted(set(ids) - FIELD_SOURCE_SUPPORT[field])
            if incompatible:
                errors.append(
                    f"variants.{variant_id}.geometry.field_evidence.{field}: "
                    f"sources do not support this field {incompatible}"
                )
        expected_geometry = EXPECTED_VARIANT_GEOMETRY.get(variant_id)
        if expected_geometry:
            for field, expected_value in expected_geometry["values"].items():
                if geometry.get(field) != expected_value:
                    errors.append(
                        f"variants.{variant_id}.geometry.{field}: expected documented value {expected_value}"
                    )
            for field, expected_ids in expected_geometry["field_evidence"].items():
                actual_ids = set(evidence.get(field, []))
                if actual_ids != expected_ids:
                    errors.append(
                        f"variants.{variant_id}.geometry.field_evidence.{field}: "
                        f"expected exactly {sorted(expected_ids)}"
                    )

        kinematics = variant.get("kinematics", {})
        if kinematics.get("stroke_mm") != stroke:
            errors.append(f"variants.{variant_id}.kinematics.stroke_mm: must equal geometry stroke")
        rod_status = str(kinematics.get("connecting_rod_status", ""))
        if "hypothesis" not in rod_status or "not_sourced" not in rod_status:
            errors.append(f"variants.{variant_id}.kinematics.connecting_rod_status: must remain an unsourced hypothesis")
        if kinematics.get("physical_kinematics_ready") is not False:
            errors.append(f"variants.{variant_id}.kinematics.physical_kinematics_ready: must be false")

        assembly_filter = variant.get("assembly_filter", {})
        f1_tags = assembly_filter.get("f1_variant_tags", [])
        f3_tags = assembly_filter.get("f3_variant_tags", [])
        turbo_expected = assembly_filter.get("turbocharger_expected_count")
        plenum_expected = assembly_filter.get("charge_plenum_expected_count")
        if variant_id == "type_912_4_5_na":
            if f1_tags != ["base"] or f3_tags != ["all"] or turbo_expected != 0 or plenum_expected != 0:
                errors.append("variants.type_912_4_5_na.assembly_filter: turbo families must be absent")
        elif variant_id == "917_30_turbo_5374":
            if set(f1_tags) != {"base", "917_30_only"} or set(f3_tags) != {"all", "917_30_only"}:
                errors.append("variants.917_30_turbo_5374.assembly_filter: turbo families must be included")
            if turbo_expected != 2 or plenum_expected != 2:
                errors.append("variants.917_30_turbo_5374.assembly_filter: expected two turbos and two plenums")

        outputs = variant.get("outputs", {})
        expected_outputs = {
            "geometry_stage": f"{slug}/stages/{slug}-geometry-f10.usda",
            "kinematic_stage": f"{slug}/stages/{slug}-kinematic-f10.usda",
            "detail_stage": f"{slug}/stages/{slug}-detail-f10.usda",
        }
        for output_kind in ("geometry_stage", "kinematic_stage", "detail_stage"):
            output = outputs.get(output_kind)
            if isinstance(output, str):
                output_paths.append(output)
            safe_relative = isinstance(output, str) and not Path(output).is_absolute() and ".." not in Path(output).parts
            if not safe_relative or not output.startswith(f"{slug}/stages/"):
                errors.append(f"variants.{variant_id}.outputs.{output_kind}: must be inside its variant directory")
            elif output != expected_outputs[output_kind]:
                errors.append(
                    f"variants.{variant_id}.outputs.{output_kind}: expected {expected_outputs[output_kind]}"
                )
    if len(output_paths) != len(set(output_paths)):
        errors.append("variants.outputs: every stage path must be unique")
    if len(output_slugs) != len(set(output_slugs)):
        errors.append("variants.output_slug: every variant slug must be unique")

    if {"base_geometry", "base_kinematics", "turbo_performance_envelope"} <= set(upstream_docs):
        na = variants.get("type_912_4_5_na", {}).get("geometry", {})
        turbo = variants.get("917_30_turbo_5374", {}).get("geometry", {})
        f1_dims = upstream_docs["base_geometry"].get("declared_dimensions", {})
        f2_slider = upstream_docs["base_kinematics"].get("crank_slider", {})
        f9_geometry = upstream_docs["turbo_performance_envelope"].get("geometry", {})
        if (na.get("cylinder_count"), na.get("bore_mm"), na.get("stroke_mm")) != (
            upstream_docs["base_geometry"].get("topology", {}).get("cylinders"),
            f1_dims.get("bore_mm"),
            f1_dims.get("stroke_mm"),
        ):
            errors.append("type_912_4_5_na: geometry must match the sourced F1 85 x 66 definition")
        if na.get("stroke_mm") != f2_slider.get("stroke_mm"):
            errors.append("type_912_4_5_na: stroke must match the F2 kinematic source")
        if (turbo.get("cylinder_count"), turbo.get("bore_mm"), turbo.get("stroke_mm")) != (
            f9_geometry.get("cylinder_count"),
            f9_geometry.get("bore_mm"),
            f9_geometry.get("stroke_mm"),
        ):
            errors.append("917_30_turbo_5374: geometry must match the F9 90 x 70.4 contract")

    missing = manifest.get("missing_variant_inputs", {})
    for variant_id in EXPECTED_VARIANTS:
        if not isinstance(missing.get(variant_id), list) or not missing[variant_id]:
            errors.append(f"missing_variant_inputs.{variant_id}: missing-input list cannot be empty")

    gates = manifest.get("release_gates", {})
    if set(gates) != EXPECTED_RELEASE_GATES:
        errors.append(f"release_gates: expected exactly {sorted(EXPECTED_RELEASE_GATES)}")
    for gate in CONFIG_READINESS_GATES:
        if gates.get(gate) is not True:
            errors.append(f"release_gates.{gate}: config contract must be true")
    for gate in PHYSICAL_RELEASE_GATES:
        if gates.get(gate) is not False:
            errors.append(f"release_gates.{gate}: must remain false in F10")
    prohibited = set(manifest.get("prohibited_use", []))
    missing_prohibitions = sorted(REQUIRED_PROHIBITIONS - prohibited)
    if missing_prohibitions:
        errors.append(f"prohibited_use: missing required prohibitions {missing_prohibitions}")
    change_scope = manifest.get("variant_change_scope", {})
    unchanged = set(change_scope.get("intentionally_unchanged_visual_hypotheses", []))
    if "crankshaft_body_throw_and_counterweight_proxy_geometry" not in unchanged:
        errors.append("variant_change_scope: unchanged crankshaft proxy geometry must be explicit")
    if "ne reconstruit pas un vilebrequin 917/30" not in str(change_scope.get("explicit_limit", "")):
        errors.append("variant_change_scope.explicit_limit: missing 917/30 crankshaft limitation")
    return errors


def _allowed(item: dict[str, Any], allowed_tags: set[str], default_tag: str) -> bool:
    return item.get("variant", default_tag) in allowed_tags


def generated_configs(
    manifest: dict[str, Any],
    project_root: Path,
    variant: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    upstream = manifest["upstream_contracts"]
    f1 = copy.deepcopy(load_json(project_root / upstream["base_geometry"]))
    f2 = copy.deepcopy(load_json(project_root / upstream["base_kinematics"]))
    f3 = copy.deepcopy(load_json(project_root / upstream["detail_families"]))
    variant_id = variant["variant_id"]
    geometry = variant["geometry"]
    filters = variant["assembly_filter"]

    f1["status"] = "F10_variant_specific_visual_geometry_not_manufacturing_geometry"
    f1["base_variant"] = variant_id
    f1["declared_dimensions"]["bore_mm"] = geometry["bore_mm"]
    f1["declared_dimensions"]["stroke_mm"] = geometry["stroke_mm"]
    dimensional_sources = {source for ids in geometry["field_evidence"].values() for source in ids}
    f1["source_ids"] = sorted(set(f1["source_ids"]) | dimensional_sources)
    f1["component_families"] = [
        item for item in f1["component_families"]
        if _allowed(item, set(filters["f1_variant_tags"]), "base")
    ]
    f1["f10_variant"] = {
        "variant_id": variant_id,
        "architecture": variant["architecture"],
        "documented_displacement_cm3": geometry["documented_displacement_cm3"],
        "field_evidence": geometry["field_evidence"],
        "geometry_role": "sourced_bore_and_stroke_with_visual_proxy_surroundings",
        "variant_change_scope": manifest["variant_change_scope"],
        "manufacturing_geometry_ready": False,
    }
    f1["prohibited_use"] = sorted(set(f1["prohibited_use"] + manifest["prohibited_use"]))

    f2["status"] = "F10_variant_specific_visual_kinematics_not_physical_validation"
    f2["crank_slider"]["stroke_mm"] = variant["kinematics"]["stroke_mm"]
    f2["crank_slider"]["connecting_rod_center_distance_mm"] = variant["kinematics"][
        "connecting_rod_center_distance_mm"
    ]
    f2["crank_slider"]["source_status"] = variant["kinematics"]["connecting_rod_status"]
    f2["acceptance"]["required_variants"] = [variant_id]
    f2["f10_variant"] = {
        "variant_id": variant_id,
        "bore_mm": geometry["bore_mm"],
        "stroke_mm": geometry["stroke_mm"],
        "physical_kinematics_ready": False,
    }
    f2["prohibited_use"] = sorted(set(f2["prohibited_use"] + manifest["prohibited_use"]))

    f3["status"] = "F10_variant_filtered_detail_proxies_not_manufacturing_geometry"
    f3["families"] = [
        item for item in f3["families"]
        if _allowed(item, set(filters["f3_variant_tags"]), "all")
    ]
    f3["acceptance"]["added_family_count"] = len(f3["families"])
    f3["acceptance"]["added_instance_count"] = sum(item["count"] for item in f3["families"])
    f3["acceptance"]["required_variants"] = [variant_id]
    f3["f10_variant"] = {
        "variant_id": variant_id,
        "allowed_placement_tags": filters["f3_variant_tags"],
        "manufacturing_geometry_ready": False,
    }
    f3["prohibited_use"] = sorted(set(f3["prohibited_use"] + manifest["prohibited_use"]))
    return f1, f2, f3


def write_configs(manifest: dict[str, Any], project_root: Path, output_root: Path) -> dict[str, Any]:
    records = []
    resolved_output_root = output_root.resolve()
    for variant in manifest["variants"]:
        variant_root = (resolved_output_root / variant["output_slug"] / "configs").resolve()
        if not variant_root.is_relative_to(resolved_output_root):
            raise RuntimeError("F10 variant config path escapes the output root")
        variant_root.mkdir(parents=True, exist_ok=True)
        f1, f2, f3 = generated_configs(manifest, project_root, variant)
        paths = {
            "geometry_config": variant_root / "complete-engine-f10.json",
            "kinematics_config": variant_root / "kinematics-f10.json",
            "detail_config": variant_root / "detail-expansion-f10.json",
        }
        for key, document in (
            ("geometry_config", f1),
            ("kinematics_config", f2),
            ("detail_config", f3),
        ):
            paths[key].write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        geometry = variant["geometry"]
        records.append(
            {
                "variant_id": variant["variant_id"],
                "output_slug": variant["output_slug"],
                "bore_mm": geometry["bore_mm"],
                "stroke_mm": geometry["stroke_mm"],
                "calculated_displacement_cm3": calculated_displacement_cm3(
                    geometry["cylinder_count"], geometry["bore_mm"], geometry["stroke_mm"]
                ),
                "configs": {key: str(path.resolve()) for key, path in paths.items()},
                "stage_outputs": variant["outputs"],
                "manufacturing_geometry_ready": False,
                "physical_kinematics_ready": False,
            }
        )
    report = {
        "schema_version": "1.0.0",
        "phase": "F10",
        "status": "passed",
        "stage_mode": manifest["stage_policy"]["mode"],
        "variant_count": len(records),
        "variants": records,
        "release_gates": manifest["release_gates"],
        "prohibited_use": manifest["prohibited_use"],
    }
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "variant-config-generation-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    project_root = args.project_root.resolve()
    manifest = load_json(args.manifest)
    errors = validate_contract(manifest, project_root)
    if errors:
        print(json.dumps({"status": "failed", "errors": errors}, indent=2))
        raise SystemExit(1)
    if args.check:
        report = {
            "schema_version": "1.0.0",
            "phase": "F10",
            "status": "passed",
            "variant_count": len(manifest["variants"]),
            "write_performed": False,
        }
    elif args.output:
        report = write_configs(manifest, project_root, args.output)
    else:
        parser.error("--output is required unless --check is used")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
