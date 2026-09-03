#!/usr/bin/env python3
"""Publie atomiquement l'allowlist des preuves F37 et leur manifeste.

Le script refuse une chaîne de SHA incohérente, tout fichier résiduel et toute
porte de libération ouverte. Les maillages complets restent volontairement dans
``work/``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_copy(source: Path, destination: Path) -> None:
    temporary = destination.with_name(destination.name + ".publishing")
    shutil.copyfile(source, temporary)
    os.replace(temporary, destination)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path("."))
    return parser.parse_args()


def main() -> int:
    root = parse_args().project_root.resolve()
    work = root / "work/917-scan-conforming-f37"
    evidence = root / "twins/reference-917-engine/evidence/f37-manufacturing-definition"
    contract_path = root / "twins/reference-917-engine/f37-manufacturing-definition.json"
    cfd_path = root / "twins/reference-917-engine/evidence/f36-final-cfd-thermal/cross-solver-report.json"

    sources = {
        "README.md": evidence / "README.md",
        "917-head-f37-manufacturing-definition.png": work / "917-head-f37-manufacturing-definition.png",
        "917-head-f37-printable-proof.png": work / "head-mesh-proof/917-head-f37-printable-proof.png",
        "917-head-f37-rocker-kinematic-screen.png": work / "kinematics/917-head-f37-rocker-kinematic-screen.png",
        "917-head-f37-oil-hydraulic-screen.png": work / "oil/917-head-f37-oil-hydraulic-screen.png",
        "917-head-f37-carrier-strength-screen.png": work / "strength/917-head-f37-carrier-strength-screen.png",
        "917-head-f37-lpbf-manufacturing.png": work / "lpbf/917-head-f37-lpbf-manufacturing.png",
        "917-head-f37-nvidia-repair-diagnostic.png": work / "nvidia-repair-candidate/917-head-f37-nvidia-welded-candidate.png",
        "f37-cad-report.json": work / "cad/f37-cad-report.json",
        "f37-carrier-calculix-report.json": work / "carrier-calculix/f37-carrier-calculix-report.json",
        "f37-carrier-strength-report.json": work / "strength/f37-carrier-strength-report.json",
        "f37-lpbf-manufacturing-report.json": work / "lpbf/f37-lpbf-manufacturing-report.json",
        "f37-oil-hydraulic-report.json": work / "oil/f37-oil-hydraulic-report.json",
        "f37-printable-head-mesh-report.json": work / "head-mesh-proof/f37-printable-head-mesh-report.json",
        "f37-rocker-kinematic-report.json": work / "kinematics/f37-rocker-kinematic-report.json",
        "f37-nvidia-mesh-repair-report.json": work / "nvidia-repair-candidate/f37-nvidia-mesh-repair-report.json",
        "f37-nvidia-geometry-validation-attestation.json": work / "nvidia-repair-candidate/f37-nvidia-geometry-validation-attestation.json",
        "f37-nvidia-direct-usda-normals-geometry.json": work / "nvidia-repair-validation/direct-usda-normals-geometry.json",
        "finish-machining-cutters.step": work / "cad/finish-machining-cutters.step",
        "four-rocker-envelopes.step": work / "cad/four-rocker-envelopes.step",
        "machining-allowance-volumes.step": work / "cad/machining-allowance-volumes.step",
        "oil-gallery-core.step": work / "cad/oil-gallery-core.step",
        "rocker-carrier-as-printed.step": work / "cad/rocker-carrier-as-printed.step",
        "two-rocker-shafts.step": work / "cad/two-rocker-shafts.step",
    }
    missing = [str(path.relative_to(root)) for path in sources.values() if not path.is_file()]
    if missing:
        raise SystemExit("preuves F37 absentes: " + ", ".join(missing))

    contract_sha = sha256(contract_path)
    cad = load(sources["f37-cad-report.json"])
    kinematics = load(sources["f37-rocker-kinematic-report.json"])
    oil = load(sources["f37-oil-hydraulic-report.json"])
    strength = load(sources["f37-carrier-strength-report.json"])
    calculix = load(sources["f37-carrier-calculix-report.json"])
    head = load(sources["f37-printable-head-mesh-report.json"])
    lpbf = load(sources["f37-lpbf-manufacturing-report.json"])
    repair = load(sources["f37-nvidia-mesh-repair-report.json"])
    attestation = load(sources["f37-nvidia-geometry-validation-attestation.json"])
    cfd = load(cfd_path)

    cad_sha = sha256(sources["f37-cad-report.json"])
    head_sha = sha256(sources["f37-printable-head-mesh-report.json"])
    expected = {
        "cad_contract": (cad["inputs"]["contract_sha256"], contract_sha),
        "kinematics_contract": (kinematics["inputs"]["contract_sha256"], contract_sha),
        "oil_contract": (oil["inputs"]["contract_sha256"], contract_sha),
        "strength_contract": (strength["inputs"]["contract_sha256"], contract_sha),
        "calculix_contract": (calculix["inputs"]["contract_sha256"], contract_sha),
        "head_contract": (head["inputs"]["contract_sha256"], contract_sha),
        "head_cad": (head["inputs"]["cad_report_sha256"], cad_sha),
        "lpbf_contract": (lpbf["inputs"]["f37_contract"]["sha256"], contract_sha),
        "lpbf_cad": (lpbf["inputs"]["f37_cad_report"]["sha256"], cad_sha),
        "lpbf_head_report": (lpbf["inputs"]["f37_head_mesh_report"]["sha256"], head_sha),
        "calculix_carrier": (
            calculix["inputs"]["carrier_step_sha256"],
            sha256(sources["rocker-carrier-as-printed.step"]),
        ),
        "head_nvidia_attestation": (
            head["nvidia_asset_validator_observation"]["evidence"]["sha256"],
            sha256(sources["f37-nvidia-geometry-validation-attestation.json"]),
        ),
        "repair_source_stl": (
            repair["inputs"]["source_head"]["sha256"],
            head["local_only_artifacts"]["917-head-f37-printable-proof.local.stl"]["sha256"],
        ),
        "repair_source_report": (repair["inputs"]["source_report"]["sha256"], head_sha),
        "repair_contract": (repair["inputs"]["contract_sha256"], contract_sha),
        "attestation_source_stl": (
            attestation["linkage"]["source_stl"]["sha256"],
            head["local_only_artifacts"]["917-head-f37-printable-proof.local.stl"]["sha256"],
        ),
        "attestation_normalized_report": (
            attestation["linkage"]["normalized_report"]["sha256"],
            sha256(sources["f37-nvidia-direct-usda-normals-geometry.json"]),
        ),
        "repair_normalized_report": (
            repair["inputs"]["nvidia_evidence"]["direct_indexed_usda"]["sha256"],
            sha256(sources["f37-nvidia-direct-usda-normals-geometry.json"]),
        ),
    }
    failures = [name for name, pair in expected.items() if pair[0] != pair[1]]
    if failures:
        raise SystemExit("chaîne SHA F37 incohérente: " + ", ".join(failures))
    if not lpbf["validated_linkage"]["head_sha256_equal"]:
        raise SystemExit("le rapport LPBF ne confirme pas le STL F37 exact")
    if calculix["gates"].get("multiaxial_valve_axis_load_case_complete") is not True:
        raise SystemExit("le cas CalculiX suivant les axes de soupape manque")

    contract = load(contract_path)
    load_cfg = contract["component_material_and_load_screen"]
    pivot_cfg = contract["rocker_pivot_reaction_screen"]
    spring_design_load = (
        float(load_cfg["worst_open_spring_load_per_valve_n"])
        * float(load_cfg["dynamic_load_factor"])
    )
    pivot_envelope_load = spring_design_load * float(
        pivot_cfg["collinear_upper_envelope_factor"]
    )
    load_failures = []
    if not math.isclose(
        float(strength["loads"]["spring_only_design_load_per_valve_n"]),
        spring_design_load,
        rel_tol=0.0,
        abs_tol=1.0e-9,
    ):
        load_failures.append("strength_spring_load")
    if not math.isclose(
        float(strength["loads"]["pivot_reaction_upper_envelope_per_valve_n"]),
        pivot_envelope_load,
        rel_tol=0.0,
        abs_tol=1.0e-9,
    ):
        load_failures.append("strength_pivot_envelope")
    for index, case in enumerate(calculix["cases"]):
        if not math.isclose(
            float(case["mesh"]["design_load_per_zone_n"]),
            pivot_envelope_load,
            rel_tol=0.0,
            abs_tol=1.0e-9,
        ):
            load_failures.append(f"calculix_pivot_envelope_{index}")
    if load_failures:
        raise SystemExit("cas de charge pivot F37 incohérent: " + ", ".join(load_failures))
    for report_name, report in (("analytique", strength), ("CalculiX", calculix)):
        gates = report["gates"]
        if gates.get("pivot_reaction_magnitude_upper_envelope_applied") is not True:
            raise SystemExit(f"enveloppe de réaction pivot absente du rapport {report_name}")
        if gates.get("actual_resultant_direction_complete") is not False:
            raise SystemExit(f"direction réelle du pivot indûment complète dans le rapport {report_name}")
        if gates.get("rocker_pivot_resultant_load_complete") is not False:
            raise SystemExit(f"charge résultante pivot indûment complète dans le rapport {report_name}")

    forbidden_true = (
        head["gates"].get("metal_print_authorized"),
        lpbf["gates"].get("metal_print_authorized"),
        lpbf["decision"].get("metal_print_authorized"),
        contract["release_gates"].get("rocker_pivot_resultant_load_complete"),
    )
    if any(value is not False for value in forbidden_true):
        raise SystemExit("une porte de fabrication F37 n'est pas fermée")

    evidence.mkdir(parents=True, exist_ok=True)
    allowed = set(sources) | {"publication.json"}
    residues = sorted(path.name for path in evidence.iterdir() if path.is_file() and path.name not in allowed)
    if residues:
        raise SystemExit("fichiers résiduels hors allowlist: " + ", ".join(residues))
    for name, source in sources.items():
        if source.resolve() == (evidence / name).resolve():
            continue
        atomic_copy(source, evidence / name)

    cross = cfd["cross_solver_comparison"]
    openfoam_solid = cfd["solid_conduction"]["openfoam_linked_case"]
    publication = {
        "schema_version": "1.1.0",
        "phase": "F37",
        "status": "published_virtual_definition_evidence_not_manufacturing_or_engine_release",
        "publication_method": "fail_closed_allowlist_atomic_file_replacement_manifest_written_last",
        "contract": {
            "path": "twins/reference-917-engine/f37-manufacturing-definition.json",
            "sha256": contract_sha,
        },
        "files": {
            name: sha256(evidence / name)
            for name in sorted(sources)
        },
        "known_conflicts": {
            "stl_vertex_manifold": {
                "local_custom_audit_non_manifold_vertices": head["strict_vertex_manifold_audit"]["non_manifold_vertex_count"],
                "nvidia_exact_validator_non_manifold_vertices": head["nvidia_asset_validator_observation"]["non_manifold_vertex_count"],
                "official_stl_or_obj_conversion_geometry_clear": False,
                "diagnostic_direct_usda_geometry_clear": bool(attestation["result"]["geometry_clear"]),
                "resolved": False,
                "blocking": True,
                "note": "La route USDA est diagnostique; VG.007 sur la conversion officielle du STL exact reste bloquant.",
            },
            "external_cooling_cross_solver": {
                "fluidx3d_openfoam_heat_relative_difference": cross["heat_relative_difference"],
                "openfoam_linked_solid_maximum_c": openfoam_solid["maximum_temperature_c"],
                "resolved": False,
                "blocking": True,
            },
            "rocker_pivot_resultant": {
                "spring_only_design_load_per_valve_n": spring_design_load,
                "collinear_magnitude_upper_envelope_factor": float(
                    pivot_cfg["collinear_upper_envelope_factor"]
                ),
                "pivot_magnitude_upper_envelope_per_valve_n": pivot_envelope_load,
                "actual_resultant_direction_complete": False,
                "resolved": False,
                "blocking": True,
                "note": "L'enveloppe borne la magnitude; sans géométrie de came mesurée, direction réelle, contact, inertie et précharge restent inconnus.",
            },
        },
        "release_gates": {
            "absolute_scale_confirmed": False,
            "porsche_917_mating_interfaces_confirmed": False,
            "whole_head_single_valid_brep": False,
            "rocker_pivot_resultant_load_complete": False,
            "vertex_manifold_validators_agree": False,
            "hot_material_card_qualified": False,
            "nonlinear_contact_and_thermomechanical_fatigue_complete": False,
            "lpbf_machine_parameter_set_qualified": False,
            "ct_ndt_and_cmm_complete": False,
            "physical_flow_oil_thermal_and_engine_correlation_complete": False,
            "professional_engineering_review_approved": False,
            "metal_print_authorized": False,
            "engine_start_authorized": False,
        },
    }
    temporary_manifest = evidence / "publication.json.publishing"
    temporary_manifest.write_text(
        json.dumps(publication, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary_manifest, evidence / "publication.json")
    print(json.dumps({"status": publication["status"], "files": len(sources)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
