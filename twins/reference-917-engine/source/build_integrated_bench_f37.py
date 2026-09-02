#!/usr/bin/env python3
"""Build the fail-closed F37 semantic dual-variant bench registry."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG = REPO_ROOT / "twins/reference-917-engine/integrated-bench-assembly-f37.json"
DEFAULT_F35_WORK_ROOT = REPO_ROOT / "work/917-rotating-assembly-f35"
DEFAULT_OUTPUT = REPO_ROOT / "work/917-integrated-bench-f37"
VARIANT_TAGS = {
    "type_912_4_5_na": {"all", "type_912_4_5_na"},
    "917_30_turbo_5374": {"all", "917_30_only"},
}
GEOMETRY_TO_F37_FAMILY = {"main_bearing_pair": "main_bearing"}
FALSE_F35_ROOT_GATES = (
    "physical_kinematics_ready",
    "manufacturing_geometry_ready",
    "engine_power_proven",
)
FALSE_USD_FLAGS = (
    "simulationValidated",
    "manufacturingReleased",
    "powerValidated",
)
FORBIDDEN_USDA_TOKENS = (
    "PhysicsJoint",
    "PhysicsRigidBodyAPI",
    "PhysicsCollisionAPI",
    "PhysicsScene",
    "def Mesh",
    "def Volume",
)


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"missing input: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except FileNotFoundError as exc:
        raise ValueError(f"missing input: {path}") from exc
    return digest.hexdigest()


def resolve(project_root: Path, value: str) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (project_root / path).resolve()


def display_path(project_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def evidence(project_root: Path, path: Path) -> dict:
    return {
        "path": display_path(project_root, path),
        "sha256": sha256(path),
        "size_bytes": path.stat().st_size,
    }


def identifier(value: str) -> str:
    result = re.sub(r"[^A-Za-z0-9_]", "_", value)
    if not result or result[0].isdigit():
        result = f"id_{result}"
    return result


def literal(value: str) -> str:
    return json.dumps(value, ensure_ascii=True)


def applies(item: dict, variant_id: str) -> bool:
    return item.get("variant") in VARIANT_TAGS[variant_id]


def require_all_false(values: object, label: str, errors: list[str]) -> None:
    if not isinstance(values, dict) or not values:
        errors.append(f"{label}: non-empty false gate object required")
        return
    for key, value in values.items():
        if value is not False:
            errors.append(f"{label}.{key}: must be explicitly false")


def validate_contract(config: dict, errors: list[str]) -> None:
    if config.get("phase") != "F37":
        errors.append("config.phase must be F37")
    if set(config.get("classification_vocabulary", {})) != {"proxy", "not_modelled"}:
        errors.append("classification vocabulary must be exactly proxy/not_modelled")
    variants = config.get("variants")
    if not isinstance(variants, list) or {item.get("variant_id") for item in variants} != set(VARIANT_TAGS):
        errors.append("config must declare exactly the two F35 variant ids")
    require_all_false(config.get("release_gates"), "config.release_gates", errors)
    output_policy = config.get("output_policy", {})
    for key in (
        "f35_usdc_copied_or_embedded",
        "geometry_authored",
        "physics_schema_authored",
        "cfd_volume_authored",
        "material_assignment_authored",
    ):
        if output_policy.get(key) is not False:
            errors.append(f"config.output_policy.{key}: must be explicitly false")


def load_source_contracts(project_root: Path, config: dict, errors: list[str]) -> tuple[dict, list[dict]]:
    loaded: dict[str, dict] = {}
    source_evidence: list[dict] = []
    for source_id, entry in config.get("source_contracts", {}).items():
        if not isinstance(entry, dict):
            errors.append(f"source_contracts.{source_id}: object required")
            continue
        path = resolve(project_root, str(entry.get("path", "")))
        try:
            actual_sha = sha256(path)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        expected_sha = entry.get("expected_sha256")
        if actual_sha != expected_sha:
            errors.append(
                f"source hash mismatch {source_id}: actual {actual_sha}, expected {expected_sha}"
            )
            continue
        try:
            loaded[source_id] = read_json(path)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        source_evidence.append(
            {
                "source_id": source_id,
                "path": display_path(project_root, path),
                "sha256": actual_sha,
                "size_bytes": path.stat().st_size,
            }
        )
    expected_ids = {
        "mechanical_connections_f8",
        "ducts_f8",
        "sealing_interfaces_f8",
        "external_interfaces_f8",
        "bench_executable_f14",
        "dual_variant_parametric_cad_f28",
    }
    if set(config.get("source_contracts", {})) != expected_ids:
        errors.append("source_contracts must contain the exact F8/F14/F28 input set")
    return loaded, source_evidence


def validate_cfd_claims(project_root: Path, config: dict, ducts: dict, errors: list[str]) -> None:
    policy = config["closed_cfd_geometry_policy"]
    required = set(policy["required_evidence_fields_when_claimed"])
    for item in ducts.get("ducts", []):
        claimed = any(item.get(field) is True for field in policy["claim_fields"])
        if not claimed:
            continue
        proof = item.get("closed_volume_evidence")
        label = f"ducts_f8.{item.get('id', '<unknown>')}.closed_volume_evidence"
        if not isinstance(proof, dict) or not required.issubset(proof):
            errors.append(f"{label}: complete proof required for a closed/flow-ready claim")
            continue
        if proof.get("watertight_check_passed") is not True:
            errors.append(f"{label}.watertight_check_passed: must be true")
            continue
        proof_path = resolve(project_root, str(proof["path"]))
        try:
            actual_sha = sha256(proof_path)
        except ValueError as exc:
            errors.append(f"{label}: {exc}")
            continue
        if actual_sha != proof.get("sha256"):
            errors.append(f"{label}: SHA-256 mismatch")


def normalize_geometry_counts(values: object) -> dict[str, int]:
    if not isinstance(values, dict):
        return {}
    result: dict[str, int] = {}
    for family, count in values.items():
        result[GEOMETRY_TO_F37_FAMILY.get(family, family)] = count
    return result


def validate_f35(
    project_root: Path,
    f35_root: Path,
    config: dict,
    errors: list[str],
) -> tuple[list[dict], list[dict]]:
    file_evidence: list[dict] = []
    variants_result: list[dict] = []
    run_path = f35_root / config["runtime_inputs"]["run_report"]
    try:
        run = read_json(run_path)
        file_evidence.append({"role": "f35_run_report", **evidence(project_root, run_path)})
    except ValueError as exc:
        errors.append(str(exc))
        return variants_result, file_evidence

    expected_variants = [item["variant_id"] for item in config["variants"]]
    run_variants = run.get("variants")
    if not isinstance(run_variants, list):
        errors.append("F35 run report variants must be an array")
        return variants_result, file_evidence
    run_by_id = {item.get("variant_id"): item for item in run_variants if isinstance(item, dict)}
    if set(run_by_id) != set(expected_variants) or run.get("variant_count") != 2:
        errors.append("F35 run report must contain exactly the two configured variants")
    for key in FALSE_F35_ROOT_GATES:
        if run.get(key) is not False:
            errors.append(f"F35 run report {key} must be explicitly false")

    expected_counts = config["f35_expected"]["component_family_counts"]
    expected_total = config["f35_expected"]["component_occurrence_total"]
    expected_frame_total = config["f35_expected"]["interface_frame_total"]
    expected_frame_families = config["f35_expected"]["interface_frame_family_counts"]
    expected_candidate_joints = config["f35_expected"]["candidate_joint_count"]
    expected_contract_sha = run.get("contract_sha256")

    for variant_id in expected_variants:
        run_variant = run_by_id.get(variant_id)
        if not isinstance(run_variant, dict):
            errors.append(f"F35 run report missing variant {variant_id}")
            continue
        geometry_path = f35_root / config["runtime_inputs"]["geometry_report_template"].format(
            variant_id=variant_id
        )
        usd_report_path = f35_root / config["runtime_inputs"]["usd_report_template"].format(
            variant_id=variant_id
        )
        usdc_path = f35_root / config["runtime_inputs"]["usdc_template"].format(
            variant_id=variant_id
        )
        try:
            geometry = read_json(geometry_path)
            geometry_evidence = evidence(project_root, geometry_path)
            usd_report = read_json(usd_report_path)
            usd_report_evidence = evidence(project_root, usd_report_path)
            usdc_evidence = evidence(project_root, usdc_path)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        file_evidence.extend(
            [
                {"role": f"{variant_id}:geometry_report", **geometry_evidence},
                {"role": f"{variant_id}:usd_report", **usd_report_evidence},
                {"role": f"{variant_id}:usdc", **usdc_evidence},
            ]
        )
        if run_variant.get("report_sha256") != geometry_evidence["sha256"]:
            errors.append(f"{variant_id}: F35 geometry report hash is not bound by run-report.json")
        if usd_report.get("usd_sha256") != usdc_evidence["sha256"]:
            errors.append(f"{variant_id}: F35 USDC hash is not bound by its USD report")
        for label, payload in (("geometry", geometry), ("usd", usd_report)):
            if payload.get("variant_id") != variant_id:
                errors.append(f"{variant_id}: {label} report variant id mismatch")
            if payload.get("contract_sha256") != expected_contract_sha:
                errors.append(f"{variant_id}: {label} report contract hash mismatch")

        geometry_counts = normalize_geometry_counts(geometry.get("component_instance_counts"))
        usd_counts = usd_report.get("component_occurrence_counts")
        if geometry_counts != expected_counts:
            errors.append(f"{variant_id}: F35 geometry component counts mismatch")
        if usd_counts != expected_counts:
            errors.append(f"{variant_id}: F35 USD component counts mismatch")
        if sum(geometry_counts.values()) != expected_total or usd_report.get("component_occurrence_total") != expected_total:
            errors.append(f"{variant_id}: F35 component occurrence total mismatch")

        frames = geometry.get("interface_frames")
        if not isinstance(frames, list):
            errors.append(f"{variant_id}: F35 interface_frames must be an array")
            frames = []
        derived_frame_families = Counter(
            frame.get("family") for frame in frames if isinstance(frame, dict)
        )
        frame_ids = [frame.get("id") for frame in frames if isinstance(frame, dict)]
        if (
            geometry.get("interface_frame_total") != expected_frame_total
            or len(frames) != expected_frame_total
        ):
            errors.append(f"{variant_id}: F35 interface frame total must be {expected_frame_total}")
        if (
            geometry.get("interface_frame_family_counts") != expected_frame_families
            or dict(derived_frame_families) != expected_frame_families
        ):
            errors.append(f"{variant_id}: F35 interface frame family counts mismatch")
        if len(frame_ids) != len(set(frame_ids)) or any(frame_id is None for frame_id in frame_ids):
            errors.append(f"{variant_id}: F35 interface frame ids must be present and unique")
        if any(
            not isinstance(frame, dict) or frame.get("physical_joint_enabled") is not False
            for frame in frames
        ):
            errors.append(f"{variant_id}: F35 interface frames must keep physical joints disabled")
        usd_datum_frames = usd_report.get("datum_frames")
        if not isinstance(usd_datum_frames, dict):
            errors.append(f"{variant_id}: F35 USD datum_frames object is required")
        elif (
            usd_datum_frames.get("total") != expected_frame_total
            or usd_datum_frames.get("family_counts") != expected_frame_families
            or usd_datum_frames.get("measured") != 0
            or usd_datum_frames.get("physical_joint_authored") != 0
        ):
            errors.append(
                f"{variant_id}: F35 USD datum frame totals/families must match and remain unmeasured/non-physical"
            )

        geometry_joints = geometry.get("candidate_joint_counts", {})
        usd_joints = usd_report.get("candidate_interfaces", {})
        if geometry_joints.get("total") != expected_candidate_joints or geometry_joints.get("enabled") != 0:
            errors.append(f"{variant_id}: F35 geometry candidate-joint gate mismatch")
        if (
            usd_joints.get("total") != expected_candidate_joints
            or usd_joints.get("enabled") != 0
            or usd_joints.get("physical_joint_authored") != 0
        ):
            errors.append(f"{variant_id}: F35 USD candidate-joint gate mismatch")

        authored = usd_report.get("authored_physics", {})
        for report_key, config_key in (
            ("active_joint_count", "physical_joint_count"),
            ("rigid_body_count", "rigid_body_count"),
            ("collider_count", "collider_count"),
            ("mass_property_count", "mass_property_count"),
            ("inertia_property_count", "inertia_property_count"),
        ):
            if authored.get(report_key) != config["f35_expected"][config_key]:
                errors.append(f"{variant_id}: authored_physics.{report_key} must remain zero")
        require_all_false(geometry.get("release_gates"), f"{variant_id}.geometry.release_gates", errors)
        require_all_false(usd_report.get("release_gates"), f"{variant_id}.usd.release_gates", errors)
        for key in FALSE_USD_FLAGS:
            if usd_report.get(key) is not False:
                errors.append(f"{variant_id}: USD report {key} must be explicitly false")

        variants_result.append(
            {
                "variant_id": variant_id,
                "f35_geometry_report": geometry_evidence,
                "f35_usd_report": usd_report_evidence,
                "f35_usdc": usdc_evidence,
                "component_counts": expected_counts,
                "component_occurrence_total": expected_total,
                "interface_frame_total": expected_frame_total,
                "interface_frame_family_counts": expected_frame_families,
                "candidate_joint_count": expected_candidate_joints,
                "physical_joint_count": 0,
            }
        )
    return variants_result, file_evidence


def registry_item(item_id: str, count: int, state: str, source: str, **extra: object) -> dict:
    result = {
        "id": item_id,
        "declared_instance_count": count,
        "model_state": state,
        "source": source,
    }
    result.update(extra)
    return result


def build_registry(config: dict, sources: dict, variant_id: str) -> dict:
    variant = next(item for item in config["variants"] if item["variant_id"] == variant_id)
    f28 = sources["dual_variant_parametric_cad_f28"]
    f28_variant = next(
        item for item in f28["variant_contracts"] if item["variant_id"] == variant["f28_variant_id"]
    )
    f35_counts = config["f35_expected"]["component_family_counts"]
    families = [
        registry_item(
            family_id,
            f35_counts.get(family_id, 0),
            "proxy" if family_id in f35_counts else "not_modelled",
            "F35" if family_id in f35_counts else "F28",
            proxy_kind="display_geometry" if family_id in f35_counts else None,
        )
        for family_id in f28_variant["family_refs"]
    ]

    f14 = sources["bench_executable_f14"]
    bench = [
        registry_item(item["id"], item["count"], "proxy", "F14", proxy_kind="semantic_bench")
        for item in f14["bench_equipment"]
    ]
    instrumentation = [
        registry_item(item["id"], item["count"], "proxy", "F14", proxy_kind="semantic_endpoint")
        for item in f14["instrumentation"]
    ]

    collections = {
        "mechanical_connections": (
            sources["mechanical_connections_f8"]["mechanical_connections"],
            "proxy",
            "semantic_connection_no_physics",
        ),
        "ducts": (sources["ducts_f8"]["ducts"], "not_modelled", None),
        "sealing_interfaces": (
            sources["sealing_interfaces_f8"]["sealing_interfaces"],
            "not_modelled",
            None,
        ),
        "external_interfaces": (
            sources["external_interfaces_f8"]["external_interfaces"],
            "proxy",
            "semantic_boundary_no_geometry_or_boundary_condition",
        ),
    }
    registry = {
        "component_families": families,
        "bench_equipment": bench,
        "instrumentation": instrumentation,
    }
    for name, (items, state, proxy_kind) in collections.items():
        registry[name] = [
            registry_item(
                item["id"],
                item["count"],
                state,
                "F8",
                proxy_kind=proxy_kind,
                physics_enabled=False,
            )
            for item in items
            if applies(item, variant_id)
        ]
    return registry


def summarize_registry(registry: dict) -> dict:
    per_collection: dict[str, dict] = {}
    states = {
        "proxy": {"group_count": 0, "declared_instance_count": 0},
        "not_modelled": {"group_count": 0, "declared_instance_count": 0},
    }
    for name, items in registry.items():
        per_collection[name] = {
            "group_count": len(items),
            "declared_instance_count": sum(item["declared_instance_count"] for item in items),
            "proxy_group_count": sum(item["model_state"] == "proxy" for item in items),
            "not_modelled_group_count": sum(item["model_state"] == "not_modelled" for item in items),
        }
        for item in items:
            bucket = states[item["model_state"]]
            bucket["group_count"] += 1
            bucket["declared_instance_count"] += item["declared_instance_count"]
    return {"collections": per_collection, "model_states": states}


def author_usda(config: dict, variant: dict, registry: dict, summary: dict) -> str:
    lines = [
        "#usda 1.0",
        "(",
        '    defaultPrim = "World"',
        "    metersPerUnit = 0.001",
        '    upAxis = "Z"',
        ")",
        "",
        'def Xform "World"',
        "{",
        f"    custom string phase = {literal('F37')}",
        f"    custom string variantId = {literal(variant['variant_id'])}",
        f"    custom string status = {literal('semantic_registry_only_all_physical_gates_blocked')}",
        "    custom bool sourceIntegrityComplete = false",
        "    custom bool physicalJointsValidated = false",
        "    custom bool closedCfdGeometryValidated = false",
        "    custom bool engineStartAuthorized = false",
        "    custom bool manufacturingGeometryReady = false",
        "    custom bool performance1600HpClaimAuthorized = false",
        f"    custom string f35UsdcPath = {literal(variant['f35_usdc']['path'])}",
        f"    custom string f35UsdcSha256 = {literal(variant['f35_usdc']['sha256'])}",
        f"    custom int f35InterfaceFrameTotal = {variant['interface_frame_total']}",
        "    custom int f35MeasuredInterfaceFrameCount = 0",
        f"    custom string f28ReuseScope = {literal(variant['f28_reuse_scope'])}",
        "",
        '    def Scope "IntegratedRegistry"',
        "    {",
    ]
    for collection_name, items in registry.items():
        lines.extend(
            [
                f'        def Scope "{identifier(collection_name)}"',
                "        {",
            ]
        )
        for item in items:
            lines.extend(
                [
                    f'            def Scope "{identifier(item["id"])}"',
                    "            {",
                    f"                custom string registryId = {literal(item['id'])}",
                    f"                custom token modelState = {literal(item['model_state'])}",
                    f"                custom string sourcePhase = {literal(item['source'])}",
                    f"                custom int declaredInstanceCount = {item['declared_instance_count']}",
                    "            }",
                ]
            )
        lines.extend(["        }", ""])
    lines.extend(
        [
            "    }",
            "",
            '    def Scope "CountSummary"',
            "    {",
            f"        custom int proxyGroupCount = {summary['model_states']['proxy']['group_count']}",
            f"        custom int notModelledGroupCount = {summary['model_states']['not_modelled']['group_count']}",
            f"        custom int proxyDeclaredInstanceCount = {summary['model_states']['proxy']['declared_instance_count']}",
            f"        custom int notModelledDeclaredInstanceCount = {summary['model_states']['not_modelled']['declared_instance_count']}",
            "    }",
            "}",
            "",
        ]
    )
    payload = "\n".join(lines)
    for token in FORBIDDEN_USDA_TOKENS:
        if token in payload:
            raise ValueError(f"forbidden USDA token authored: {token}")
    return payload


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).resolve()
    config_path = Path(args.config).resolve()
    f35_root = Path(args.f35_work_root).resolve()
    output = Path(args.output).resolve()
    work_root = (project_root / "work").resolve()
    errors: list[str] = []

    try:
        config = read_json(config_path)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    validate_contract(config, errors)
    try:
        output.relative_to(work_root)
    except ValueError:
        errors.append("output must remain below the project work/ directory")
    if output.exists():
        errors.append(f"output already exists: {output}")

    sources, contract_evidence = load_source_contracts(project_root, config, errors)
    if "ducts_f8" in sources:
        validate_cfd_claims(project_root, config, sources["ducts_f8"], errors)
    f35_variants, f35_evidence = validate_f35(project_root, f35_root, config, errors)

    report = {
        "schema_version": "1.0.0",
        "phase": "F37",
        "status": "blocked_before_authoring" if errors else "pending_authoring",
        "config": evidence(project_root, config_path),
        "source_contract_evidence": contract_evidence,
        "f35_runtime_evidence": f35_evidence,
        "errors": errors,
        "source_integrity_checked": not errors,
        "physical_joint_count": 0,
        "rigid_body_count": 0,
        "collider_count": 0,
        "mass_property_count": 0,
        "inertia_property_count": 0,
        "closed_cfd_volume_count": 0,
        "engine_start_authorized": False,
        "manufacturing_geometry_ready": False,
        "performance_1600_hp_claim_authorized": False,
        "release_gates": config.get("release_gates", {}),
        "variants": [],
    }
    if errors:
        if not output.exists():
            output.mkdir(parents=True)
            write_json(output / "integrated-bench-f37-report.json", report)
        print("\n".join(errors), file=sys.stderr)
        return 2

    f35_by_id = {item["variant_id"]: item for item in f35_variants}
    temp_parent = output.parent
    temp_parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output.name}-", dir=temp_parent))
    try:
        for configured_variant in config["variants"]:
            variant_id = configured_variant["variant_id"]
            f35 = f35_by_id[variant_id]
            integrated_variant = {**configured_variant, **f35}
            registry = build_registry(config, sources, variant_id)
            summary = summarize_registry(registry)
            variant_dir = temporary / variant_id
            variant_dir.mkdir()
            registry_path = variant_dir / "integrated-registry-f37.json"
            stage_path = variant_dir / "integrated-bench-f37.usda"
            write_json(
                registry_path,
                {
                    "schema_version": "1.0.0",
                    "phase": "F37",
                    "variant_id": variant_id,
                    "f28_variant_id": configured_variant["f28_variant_id"],
                    "f28_identity_match": configured_variant["f28_identity_match"],
                    "f28_reuse_scope": configured_variant["f28_reuse_scope"],
                    "f35_usdc": f35["f35_usdc"],
                    "f35_component_counts": f35["component_counts"],
                    "f35_interface_frame_total": f35["interface_frame_total"],
                    "f35_interface_frame_family_counts": f35["interface_frame_family_counts"],
                    "registry": registry,
                    "counts": summary,
                    "release_gates": config["release_gates"],
                },
            )
            stage_path.write_text(
                author_usda(config, integrated_variant, registry, summary),
                encoding="utf-8",
            )
            report["variants"].append(
                {
                    "variant_id": variant_id,
                    "f28_variant_id": configured_variant["f28_variant_id"],
                    "f28_identity_match": configured_variant["f28_identity_match"],
                    "f28_reuse_scope": configured_variant["f28_reuse_scope"],
                    "f35_component_counts": f35["component_counts"],
                    "f35_component_occurrence_total": f35["component_occurrence_total"],
                    "f35_interface_frame_total": f35["interface_frame_total"],
                    "f35_interface_frame_family_counts": f35["interface_frame_family_counts"],
                    "registry_path": f"{variant_id}/{registry_path.name}",
                    "registry_sha256": sha256(registry_path),
                    "usda_path": f"{variant_id}/{stage_path.name}",
                    "usda_sha256": sha256(stage_path),
                    "counts": summary,
                }
            )
        report.update(
            {
                "status": "semantic_integrated_bench_built_all_physical_gates_blocked",
                "source_integrity_checked": True,
                "semantic_registry_built": True,
                "openusd_runtime_used": False,
                "usda_scope": "self_contained_semantic_registry_no_live_geometry_reference",
            }
        )
        write_json(temporary / "integrated-bench-f37-report.json", report)
        os.replace(temporary, output)
    except Exception:
        for path in sorted(temporary.rglob("*"), reverse=True):
            if path.is_file() or path.is_symlink():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        temporary.rmdir()
        raise

    print(json.dumps({"status": "passed", "output": display_path(project_root, output)}))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=str(REPO_ROOT))
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--f35-work-root", default=str(DEFAULT_F35_WORK_ROOT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(build(parse_args()))
