#!/usr/bin/env python3
"""Validate and materialize the fail-closed F41 component-factory plan.

This runner expands component-family quantities into semantic occurrences and
creates deterministic CAD/Vast job manifests.  It deliberately does not author
geometry: planned paths are never reported as generated artifacts.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONTRACT = REPO_ROOT / "twins/reference-917-engine/component-factory-f41.json"
DEFAULT_OUTPUT = REPO_ROOT / "work/917-component-factory-f41"

ALLOWED_CLASSIFICATIONS = {"measured", "documentary", "design_hypothesis", "unknown"}
ALLOWED_ROUTES = {
    "reuse_f35_seed",
    "reuse_f34_seed",
    "new_parametric_prototype",
    "supplier_envelope",
    "interface_definition_required",
}
ALLOWED_AXES = {"singleton", "bank", "per_bank", "cylinder", "per_cylinder", "sequential", "unknown"}
CAD_ROUTES = {"reuse_f35_seed", "reuse_f34_seed", "new_parametric_prototype"}
F35_FAMILIES = {
    "crankshaft",
    "main_bearing_pair",
    "connecting_rod",
    "piston",
    "piston_pin",
    "piston_ring",
}
F35_HASH_BOUND_PATHS = {
    "contract": "twins/reference-917-engine/rotating-assembly-cad-f35.json",
    "generator": "twins/reference-917-engine/source/build_rotating_assembly_cad_f35.py",
    "math_module": "twins/reference-917-engine/source/rotating_assembly_f35_math.py",
}


class ContractError(RuntimeError):
    """Raised when an F41 invariant is not satisfied."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ContractError(f"missing_input:{path}") from exc
    except json.JSONDecodeError as exc:
        raise ContractError(f"invalid_json:{path}:{exc}") from exc
    require(isinstance(value, dict), f"json_object_required:{path}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    except FileNotFoundError as exc:
        raise ContractError(f"missing_input:{path}") from exc
    return digest.hexdigest()


def canonical_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def resolve(project_root: Path, value: str) -> Path:
    candidate = Path(value)
    return candidate if candidate.is_absolute() else project_root / candidate


def topological_order(nodes: list[dict[str, Any]], label: str) -> list[str]:
    node_by_id: dict[str, dict[str, Any]] = {}
    for node in nodes:
        require(isinstance(node, dict), f"{label}:node_object_required")
        node_id = node.get("id")
        require(isinstance(node_id, str) and node_id, f"{label}:node_id_required")
        require(node_id not in node_by_id, f"{label}:duplicate_node:{node_id}")
        node_by_id[node_id] = node

    indegree = {node_id: 0 for node_id in node_by_id}
    children: dict[str, list[str]] = defaultdict(list)
    for node_id, node in node_by_id.items():
        dependencies = node.get("depends_on")
        require(isinstance(dependencies, list), f"{label}:depends_on_array_required:{node_id}")
        require(len(dependencies) == len(set(dependencies)), f"{label}:duplicate_dependency:{node_id}")
        for dependency in dependencies:
            require(dependency in node_by_id, f"{label}:unknown_dependency:{node_id}:{dependency}")
            require(dependency != node_id, f"{label}:self_dependency:{node_id}")
            indegree[node_id] += 1
            children[dependency].append(node_id)

    ready = deque(sorted(node_id for node_id, degree in indegree.items() if degree == 0))
    order: list[str] = []
    while ready:
        node_id = ready.popleft()
        order.append(node_id)
        for child in sorted(children[node_id]):
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)
    require(len(order) == len(node_by_id), f"{label}:cycle_detected")
    return order


def cylinder_labels(engine: dict[str, Any]) -> list[str]:
    per_bank = engine["cylinders_per_bank"]
    return [
        f"bank_{bank}_cyl_{index:02d}"
        for bank in ("L", "R")
        for index in range(1, per_bank + 1)
    ]


def expand_occurrence_ids(family: dict[str, Any], engine: dict[str, Any]) -> list[str]:
    family_id = family["id"]
    quantity = family.get("quantity")
    axis = family["occurrence_axis"]
    if axis == "unknown":
        require(quantity is None, f"unknown_axis_requires_null_quantity:{family_id}")
        return []
    require(isinstance(quantity, int) and not isinstance(quantity, bool) and quantity > 0, f"positive_quantity_required:{family_id}")
    if axis == "singleton":
        require(quantity == 1, f"singleton_quantity_must_be_one:{family_id}")
        result = [family_id]
    elif axis == "bank":
        require(quantity == engine["bank_count"], f"bank_quantity_mismatch:{family_id}")
        result = [f"{family_id}_bank_{bank}" for bank in ("L", "R")]
    elif axis == "per_bank":
        multiplicity = family.get("multiplicity")
        require(isinstance(multiplicity, int) and multiplicity > 0, f"per_bank_multiplicity_required:{family_id}")
        require(quantity == engine["bank_count"] * multiplicity, f"per_bank_quantity_mismatch:{family_id}")
        result = [
            f"{family_id}_bank_{bank}_{index:02d}"
            for bank in ("L", "R")
            for index in range(1, multiplicity + 1)
        ]
    elif axis == "cylinder":
        require(quantity == engine["cylinder_count"], f"cylinder_quantity_mismatch:{family_id}")
        result = [f"{family_id}_{cylinder}" for cylinder in cylinder_labels(engine)]
    elif axis == "per_cylinder":
        multiplicity = family.get("multiplicity")
        require(isinstance(multiplicity, int) and multiplicity > 0, f"per_cylinder_multiplicity_required:{family_id}")
        require(quantity == engine["cylinder_count"] * multiplicity, f"per_cylinder_quantity_mismatch:{family_id}")
        result = [
            f"{family_id}_{cylinder}_{index:02d}"
            for cylinder in cylinder_labels(engine)
            for index in range(1, multiplicity + 1)
        ]
    elif axis == "sequential":
        result = [f"{family_id}_{index:02d}" for index in range(1, quantity + 1)]
    else:
        raise ContractError(f"unsupported_occurrence_axis:{family_id}:{axis}")
    require(len(result) == quantity, f"expanded_quantity_mismatch:{family_id}")
    require(len(result) == len(set(result)), f"duplicate_occurrence_id:{family_id}")
    return result


def validate_sources(project_root: Path, contract: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    evidence: list[dict[str, Any]] = []
    loaded: dict[str, dict[str, Any]] = {}
    source_ids: set[str] = set()
    for source in contract.get("source_contracts", []):
        source_id = source.get("id")
        require(isinstance(source_id, str) and source_id, "source_id_required")
        require(source_id not in source_ids, f"duplicate_source_id:{source_id}")
        source_ids.add(source_id)
        path = resolve(project_root, str(source.get("path", "")))
        actual = sha256(path)
        require(actual == source.get("sha256"), f"source_hash_mismatch:{source_id}:{actual}")
        loaded[source_id] = read_json(path)
        evidence.append({
            "id": source_id,
            "path": path.relative_to(project_root).as_posix(),
            "sha256": actual,
            "size_bytes": path.stat().st_size,
            "use": source.get("use"),
        })
    require(source_ids == {
        "complete_engine_f1",
        "aircooled_4v_f34",
        "rotating_assembly_f35",
        "integrated_bench_f37",
        "manufacturing_routing_f19",
        "parametric_cad_assembly_f22",
    }, "unexpected_source_contract_set")
    return evidence, loaded


def validate_contract(project_root: Path, contract: dict[str, Any]) -> dict[str, Any]:
    require(contract.get("phase") == "F41", "expected_F41_contract")
    require(contract.get("schema_version") == "1.0.0", "unsupported_schema_version")
    engine = contract.get("engine")
    require(isinstance(engine, dict), "engine_object_required")
    require(engine.get("architecture", "").startswith("horizontally_opposed_flat_12"), "flat_12_architecture_required")
    require(engine.get("cylinder_count") == 12, "exactly_12_cylinders_required")
    require(engine.get("bank_count") == 2 and engine.get("cylinders_per_bank") == 6, "two_banks_of_six_required")
    require(engine.get("valves_per_cylinder") == 4, "four_valves_per_cylinder_required")
    require(engine.get("intake_valves_per_cylinder") == 2, "two_intake_valves_per_cylinder_required")
    require(engine.get("exhaust_valves_per_cylinder") == 2, "two_exhaust_valves_per_cylinder_required")
    require(engine.get("total_valve_count") == 48, "exactly_48_valves_required")
    require(engine.get("camshaft_count") == 4, "exactly_4_camshafts_required")
    require(engine.get("turbocharger_count") == 2, "exactly_2_turbochargers_required")
    require(engine.get("target_power_status") == "unvalidated_design_target_not_a_simulation_or_dyno_result", "power_target_must_be_unvalidated")

    vocabulary = contract.get("classification_vocabulary")
    require(isinstance(vocabulary, dict) and set(vocabulary) == ALLOWED_CLASSIFICATIONS, "classification_vocabulary_mismatch")
    require(set(contract.get("route_vocabulary", {})) == ALLOWED_ROUTES, "route_vocabulary_mismatch")
    source_evidence, sources = validate_sources(project_root, contract)
    require(sources["complete_engine_f1"].get("topology", {}).get("cylinders") == 12, "F1_cylinder_count_mismatch")
    f35_counts = sources["rotating_assembly_f35"].get("expected_component_counts_per_variant", {})
    require(f35_counts.get("connecting_rod") == 12 and f35_counts.get("piston") == 12, "F35_rotating_count_mismatch")
    require(sources["integrated_bench_f37"].get("f35_expected", {}).get("component_occurrence_total") == 81, "F37_F35_occurrence_count_mismatch")

    node_order = topological_order(contract.get("assembly_nodes", []), "assembly_dag")
    node_ids = set(node_order)
    job_order = topological_order(contract.get("vast_jobs", []), "vast_job_dag")
    job_ids = set(job_order)
    families = contract.get("families")
    require(isinstance(families, list) and families, "families_array_required")
    family_ids: set[str] = set()
    occurrence_ids: set[str] = set()
    for family in families:
        require(isinstance(family, dict), "family_object_required")
        family_id = family.get("id")
        require(isinstance(family_id, str) and family_id, "family_id_required")
        require(family_id not in family_ids, f"duplicate_family_id:{family_id}")
        family_ids.add(family_id)
        require(family.get("knowledge_classification") in ALLOWED_CLASSIFICATIONS, f"invalid_classification:{family_id}")
        require(family.get("route") in ALLOWED_ROUTES, f"invalid_route:{family_id}")
        require(family.get("occurrence_axis") in ALLOWED_AXES, f"invalid_occurrence_axis:{family_id}")
        require(family.get("assembly_node") in node_ids, f"invalid_assembly_node:{family_id}")
        require(family.get("cad_job") in job_ids, f"invalid_cad_job:{family_id}")
        if family.get("route") == "interface_definition_required":
            require(family.get("knowledge_classification") == "unknown", f"blocked_route_must_be_unknown:{family_id}")
        ids = expand_occurrence_ids(family, engine)
        require(not occurrence_ids.intersection(ids), f"global_duplicate_occurrence_id:{family_id}")
        occurrence_ids.update(ids)

    for required_id, expected in {
        "individual_cylinder": 12,
        "cylinder_head": 12,
        "connecting_rod": 12,
        "piston": 12,
        "intake_valve": 24,
        "exhaust_valve": 24,
        "spark_plug": 24,
        "camshaft": 4,
        "turbine_wheel": 2,
        "compressor_wheel": 2,
    }.items():
        family = next((item for item in families if item["id"] == required_id), None)
        require(family is not None and family.get("quantity") == expected, f"required_family_quantity_mismatch:{required_id}")

    seeds = contract.get("prototype_seeds")
    require(isinstance(seeds, dict), "prototype_seeds_required")
    seeded_families: dict[str, str] = {}
    for seed_id, seed in seeds.items():
        generator = resolve(project_root, str(seed.get("generator", "")))
        require(generator.is_file(), f"missing_seed_generator:{seed_id}:{generator}")
        for family_id in seed.get("families", []):
            require(family_id in family_ids, f"seed_unknown_family:{seed_id}:{family_id}")
            require(family_id not in seeded_families, f"family_has_multiple_seeds:{family_id}")
            seeded_families[family_id] = seed_id
    f35_seed = seeds["f35_rotating"]
    require(set(f35_seed["families"]) == F35_FAMILIES, "F35_seed_family_set_mismatch")
    hash_bound_inputs = f35_seed.get("hash_bound_inputs")
    require(isinstance(hash_bound_inputs, list), "F35_hash_bound_inputs_required")
    require(len(hash_bound_inputs) == len(F35_HASH_BOUND_PATHS), "F35_hash_bound_input_count_mismatch")
    by_role: dict[str, dict[str, Any]] = {}
    for item in hash_bound_inputs:
        require(isinstance(item, dict), "F35_hash_bound_input_object_required")
        role = item.get("role")
        require(role in F35_HASH_BOUND_PATHS, f"F35_hash_bound_input_role_invalid:{role}")
        require(role not in by_role, f"F35_hash_bound_input_role_duplicate:{role}")
        expected_path = F35_HASH_BOUND_PATHS[role]
        require(item.get("path") == expected_path, f"F35_hash_bound_input_path_mismatch:{role}")
        actual = sha256(resolve(project_root, expected_path))
        require(actual == item.get("sha256"), f"F35_hash_bound_input_hash_mismatch:{role}:{actual}")
        by_role[role] = item
    require(set(by_role) == set(F35_HASH_BOUND_PATHS), "F35_hash_bound_input_role_set_mismatch")
    require(f35_seed.get("generator") == F35_HASH_BOUND_PATHS["generator"], "F35_generator_path_mismatch")
    require(seeds["f1_legacy_two_valve"].get("families") == [], "F1_two_valve_geometry_must_not_be_reused")

    executable = contract.get("executable_factory")
    require(isinstance(executable, dict), "executable_factory_required")
    require(executable.get("generateable_family_count") == 6, "exactly_six_F35_families_required")
    require(executable.get("blocked_family_count_before_new_sources") == 132, "exactly_132_blocked_families_required")
    require(executable.get("generated_occurrence_coverage_if_successful") == 81, "F35_occurrence_coverage_must_be_81")
    require(set(executable.get("cad_runtime", {}).get("families", [])) == F35_FAMILIES, "cad_runtime_must_contain_only_F35_families")
    require(set(executable.get("usd_runtime", {}).get("families", [])) == F35_FAMILIES, "usd_runtime_must_contain_only_F35_families")
    require("f34_step_seed" not in executable, "F34_step_seed_must_not_be_executable")

    gates = contract.get("release_gates")
    require(isinstance(gates, dict) and gates, "release_gates_required")
    require(all(value is False for value in gates.values()), "all_release_gates_must_be_false")
    output = contract.get("output_contract")
    require(isinstance(output, dict), "output_contract_required")
    for key in ("editable_master", "editable_master_alternative", "neutral_cad", "prototype_mesh", "display_mesh", "usd_asset"):
        require("{family_id}" in str(output.get(key, "")), f"family_output_template_required:{key}")
    require(output.get("generated_artifacts_committed") is False, "generated_artifacts_must_not_be_committed")
    require(output.get("purchased_parts_three_mf_allowed") is False, "purchased_parts_3mf_must_be_forbidden")
    expected_simready = [
        "preflight",
        "content_agents_readiness",
        "convert_to_usd",
        "validate_usd_minimum",
        "material_assignment",
        "physics_assignment",
        "simready_conformance",
        "asset_geometry_physics_profile_validation",
    ]
    require(output.get("simready_stage_order") == expected_simready, "simready_stage_order_mismatch")

    return {
        "source_evidence": source_evidence,
        "assembly_order": node_order,
        "job_order": job_order,
        "family_count": len(families),
        "known_occurrence_count": len(occurrence_ids),
    }


def output_plan(contract: dict[str, Any], family: dict[str, Any]) -> dict[str, Any]:
    template = contract["output_contract"]
    family_id = family["id"]
    if family["route"] == "interface_definition_required":
        return {
            "status": "blocked_missing_interface_or_quantity",
            "geometry_generated": False,
            "planned_outputs": {},
        }
    planned = {
        "family_report": template["family_report"].format(family_id=family_id),
        "usd": template["usd_asset"].format(family_id=family_id),
    }
    if family["route"] == "supplier_envelope":
        planned.update({
            "editable_wrapper": f"{family_id}/source/{family_id}-vendor-envelope.json",
            "vendor_step": template["neutral_cad"].format(family_id=family_id),
        })
        return {
            "status": "planned_vendor_envelope_not_acquired",
            "geometry_generated": False,
            "planned_outputs": planned,
            "3mf": "not_applicable_purchased_component",
            "stl": "not_applicable_purchased_component",
        }
    planned.update({
        "editable_master": template["editable_master"].format(family_id=family_id),
        "editable_master_alternative": template["editable_master_alternative"].format(family_id=family_id),
        "step": template["neutral_cad"].format(family_id=family_id),
        "3mf": template["prototype_mesh"].format(family_id=family_id),
        "stl": template["display_mesh"].format(family_id=family_id),
    })
    return {
        "status": "planned_parametric_research_prototype_not_generated",
        "geometry_generated": False,
        "planned_outputs": planned,
    }


def materialize(project_root: Path, contract_path: Path, output_root: Path) -> dict[str, Any]:
    contract = read_json(contract_path)
    validated = validate_contract(project_root, contract)
    engine = contract["engine"]
    families = contract["families"]

    occurrences: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    family_plans: list[dict[str, Any]] = []
    for family in families:
        ids = expand_occurrence_ids(family, engine)
        if not ids:
            unresolved.append({
                "family_id": family["id"],
                "system": family["system"],
                "reason": "quantity_or_interface_unknown_no_occurrence_invented",
                "assembly_node": family["assembly_node"],
            })
        for occurrence_id in ids:
            occurrences.append({
                "occurrence_id": occurrence_id,
                "family_id": family["id"],
                "system": family["system"],
                "assembly_node": family["assembly_node"],
                "knowledge_classification": family["knowledge_classification"],
                "route": family["route"],
                "geometry_status": "not_generated",
                "physical_release": False,
            })
        plan = {
            "family_id": family["id"],
            "system": family["system"],
            "quantity": family.get("quantity"),
            "occurrence_ids": ids,
            "knowledge_classification": family["knowledge_classification"],
            "route": family["route"],
            "assembly_node": family["assembly_node"],
            "cad_job": family["cad_job"],
            **output_plan(contract, family),
        }
        family_plans.append(plan)

    family_plans.sort(key=lambda item: item["family_id"])
    occurrences.sort(key=lambda item: item["occurrence_id"])
    unresolved.sort(key=lambda item: item["family_id"])
    classification_counts = Counter(item["knowledge_classification"] for item in families)
    system_families = Counter(item["system"] for item in families)
    system_occurrences = Counter(item["system"] for item in occurrences)
    route_counts = Counter(item["route"] for item in families)

    dag_payload = {
        "schema_version": "1.0.0",
        "phase": "F41",
        "status": "assembly_dependency_plan_only",
        "topological_order": validated["assembly_order"],
        "nodes": contract["assembly_nodes"],
        "physical_joint_count": 0,
        "assembly_clearance_validated": False,
    }

    families_by_job: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for family in families:
        families_by_job[family["cad_job"]].append(family)
    jobs: list[dict[str, Any]] = []
    profiles = contract["compute_profiles"]
    for job in contract["vast_jobs"]:
        assigned = sorted(families_by_job.get(job["id"], []), key=lambda item: item["id"])
        profile = profiles[job["profile"]]
        if job["id"] == "blocked-interfaces":
            status = "blocked_until_inputs_exist"
        elif job["id"] == "usd-convert-minimum-validate":
            status = "waiting_for_cad_outputs"
        elif job["id"] == "material-physics-conformance":
            status = "blocked_pending_content_agents_preflight_and_gpu_service"
        else:
            status = "planned_not_executed"
        jobs.append({
            **job,
            "status": status,
            "family_ids": [item["id"] for item in assigned],
            "family_count": len(assigned),
            "known_occurrence_count": sum(item.get("quantity") or 0 for item in assigned),
            "compute_profile": profile,
            "paid_instance_launched": False,
        })

    bom_payload = {
        "schema_version": "1.0.0",
        "phase": "F41",
        "status": "semantic_occurrence_register_complete_unknown_counts_fail_closed",
        "engine_architecture": engine["architecture"],
        "cylinder_count": engine["cylinder_count"],
        "total_valve_count": engine["total_valve_count"],
        "family_count": len(families),
        "known_occurrence_count": len(occurrences),
        "unresolved_family_count": len(unresolved),
        "unresolved_families": unresolved,
        "classification_family_counts": dict(sorted(classification_counts.items())),
        "route_family_counts": dict(sorted(route_counts.items())),
        "system_family_counts": dict(sorted(system_families.items())),
        "system_known_occurrence_counts": dict(sorted(system_occurrences.items())),
        "occurrences": occurrences,
        "dimensional_geometry_count": 0,
        "manufacturing_released_occurrence_count": 0,
    }
    jobs_payload = {
        "schema_version": "1.0.0",
        "phase": "F41",
        "status": "vast_execution_plan_only_no_instance_launched",
        "topological_order": validated["job_order"],
        "jobs": jobs,
        "machine_384_cpu_eligible_profiles": ["cpu_cad", "cpu_vendor_envelope"],
        "machine_384_cpu_note": "Les maitres repetes sont generes une fois par famille puis instances; 1265 occurrences ne justifient pas 1265 calculs CAO.",
        "large_gpu_needed_now": False,
        "large_gpu_needed_later_for": ["content_agents_if_self_hosted", "high_fidelity_rendering", "large_cfd_or_physicsnemo_training_after_validated_dataset_exists"],
    }

    canonical_write(output_root / contract["output_contract"]["bom_occurrences"], bom_payload)
    canonical_write(output_root / contract["output_contract"]["assembly_dag"], dag_payload)
    canonical_write(output_root / contract["output_contract"]["vast_job_manifest"], jobs_payload)
    for plan in family_plans:
        canonical_write(output_root / "family-plans" / f"{plan['family_id']}.json", plan)

    report = {
        "schema_version": "1.0.0",
        "phase": "F41",
        "status": "passed_plan_generation_geometry_not_generated",
        "contract_path": contract_path.relative_to(project_root).as_posix(),
        "contract_sha256": sha256(contract_path),
        "source_evidence": validated["source_evidence"],
        "family_count": len(families),
        "known_occurrence_count": len(occurrences),
        "unresolved_family_count": len(unresolved),
        "family_plan_count": len(family_plans),
        "generated_geometry_family_count": 0,
        "generated_step_count": 0,
        "generated_3mf_count": 0,
        "generated_stl_count": 0,
        "generated_usd_count": 0,
        "planned_parametric_family_count": sum(item["route"] in CAD_ROUTES for item in families),
        "planned_vendor_envelope_family_count": sum(item["route"] == "supplier_envelope" for item in families),
        "blocked_family_count": sum(item["route"] == "interface_definition_required" for item in families),
        "assembly_node_count": len(contract["assembly_nodes"]),
        "vast_job_count": len(contract["vast_jobs"]),
        "paid_instance_launched": False,
        "release_gates": contract["release_gates"],
        "prohibited_claims": contract["prohibited_claims"],
        "outputs": {
            "bom_occurrences": contract["output_contract"]["bom_occurrences"],
            "assembly_dag": contract["output_contract"]["assembly_dag"],
            "vast_job_manifest": contract["output_contract"]["vast_job_manifest"],
            "family_plans": "family-plans/*.json",
        },
    }
    canonical_write(output_root / contract["output_contract"]["generation_report"], report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--project-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    contract_path = args.contract.resolve()
    contract = read_json(contract_path)
    if args.validate_only:
        validated = validate_contract(project_root, contract)
        print(json.dumps({
            "status": "passed_contract_validation",
            "family_count": validated["family_count"],
            "known_occurrence_count": validated["known_occurrence_count"],
            "geometry_generated": False,
        }, indent=2, sort_keys=True))
        return 0
    report = materialize(project_root, contract_path, args.output.resolve())
    print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
