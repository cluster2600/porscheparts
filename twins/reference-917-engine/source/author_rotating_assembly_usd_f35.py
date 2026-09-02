#!/usr/bin/env python3
"""Compose les prototypes F35 en deux stages USD cinématiques display-only.

Ce script est volontairement limité à l'authoring de représentation. La
cinématique 0..720° provient exclusivement de ``rotating_assembly_f35_math``.
Les 37 interfaces sont des repères candidats désactivés : aucun joint PhysX,
corps rigide, collider, matériau physique, masse ou inertie n'est créé.

Les sorties restent sous ``work/917-rotating-assembly-f35/<variant>/usd/`` et
ne constituent ni une preuve historique, ni une validation de simulation, ni
une libération de fabrication ou de puissance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Iterable

from pxr import Gf, Sdf, Usd, UsdGeom

from rotating_assembly_f35_math import (
    BANK_AXES,
    CRANK_AXIS,
    DESIGN_CRANKPIN_PHASES_DEG,
    assembly_sample,
    cycle_angles_deg,
    paired_rod_axial_layout_mm,
    paired_rod_axial_offset_mm,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
CONTRACT_PATH = REPO_ROOT / "twins/reference-917-engine/rotating-assembly-cad-f35.json"
WORK_ROOT = REPO_ROOT / "work/917-rotating-assembly-f35"

EXPECTED_VARIANT_IDS = ("type_912_4_5_na", "917_30_turbo_5374")
COMPONENT_COUNTS = {
    "crankshaft": 1,
    "main_bearing": 8,
    "connecting_rod": 12,
    "piston": 12,
    "piston_pin": 12,
    "piston_ring": 36,
}
SOURCE_PROTOTYPE_FAMILIES = {
    "crankshaft": "crankshaft",
    "main_bearing": "main_bearing_pair",
    "connecting_rod": "connecting_rod",
    "piston": "piston",
    "piston_pin": "piston_pin",
    "piston_ring": "piston_ring",
}
EXPECTED_COMPONENT_TOTAL = 81
EXPECTED_CANDIDATE_INTERFACE_COUNT = 37
EXPECTED_DATUM_FRAME_COUNTS = {
    "crankshaft_axis": 1,
    "main_journal_centres_01_to_08": 8,
    "crankpin_centres_01_to_06": 6,
    "rod_big_end_axis": 12,
    "rod_small_end_axis": 12,
    "piston_pin_axis": 12,
    "piston_crown_datum": 12,
    "piston_ring_groove_datums": 36,
}
EXPECTED_DATUM_FRAME_TOTAL = sum(EXPECTED_DATUM_FRAME_COUNTS.values())
SAMPLE_STEP_DEG = 1.0
CRANK_DEGREES_PER_SECOND = 60.0
USD_FILENAME = "rotating-assembly-f35.usdc"
REPORT_FILENAME = "rotating-assembly-f35-report.json"
USD_METERS_PER_UNIT = 0.001
USD_UP_AXIS = "Z"

FALSE_STAGE_METADATA_KEYS = (
    "historicalCylinderMappingResolved",
    "simulationValidated",
    "manufacturingReleased",
    "powerValidated",
)

FORBIDDEN_PRIM_TYPES = {
    "PhysicsScene",
    "PhysicsJoint",
    "PhysicsFixedJoint",
    "PhysicsRevoluteJoint",
    "PhysicsPrismaticJoint",
    "PhysicsSphericalJoint",
    "PhysicsDistanceJoint",
}
FORBIDDEN_APPLIED_SCHEMA_FRAGMENTS = (
    "RigidBodyAPI",
    "CollisionAPI",
    "MassAPI",
    "PhysicsMaterialAPI",
    "Physx",
)


def require(condition: bool, message: str) -> None:
    """Lève une erreur déterministe lorsqu'un garde-fou F35 échoue."""

    if not condition:
        raise RuntimeError(message)


def load_json(path: Path) -> dict[str, Any]:
    """Charge un objet JSON sans accepter une racine d'un autre type."""

    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"expected_json_object:{path}")
    return value


def sha256(path: Path) -> str:
    """Calcule le SHA-256 d'un artefact sans charger tout le fichier."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_write_text(path: Path, content: str) -> None:
    """Publie un rapport par remplacement atomique dans son répertoire."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _temporary_stage_path(final_path: Path) -> Path:
    """Alloue un nom unique conservant le suffixe crate ``.usdc``."""

    with tempfile.NamedTemporaryFile(
        dir=final_path.parent,
        prefix=f".{final_path.stem}.",
        suffix=".tmp.usdc",
        delete=False,
    ) as stream:
        temporary = Path(stream.name)
    temporary.unlink()
    return temporary


def parameter(variant: dict[str, Any], name: str) -> float:
    """Retourne un paramètre numérique fini du contrat F35."""

    record = variant.get("parameters", {}).get(name)
    require(isinstance(record, dict), f"missing_parameter:{variant.get('id')}:{name}")
    value = record.get("value")
    require(
        isinstance(value, (int, float)) and not isinstance(value, bool),
        f"numeric_parameter_required:{variant.get('id')}:{name}",
    )
    numeric = float(value)
    require(numeric == numeric and abs(numeric) != float("inf"), f"finite_parameter_required:{name}")
    return numeric


def cylinder_stations(variant: dict[str, Any]) -> list[float]:
    """Dérive les six stations X de l'hypothèse d'implantation F35."""

    pitch = parameter(variant, "cylinder_pitch_mm")
    central = parameter(variant, "central_pair_pitch_mm")
    return [
        -(central / 2.0 + 2.0 * pitch),
        -(central / 2.0 + pitch),
        -central / 2.0,
        central / 2.0,
        central / 2.0 + pitch,
        central / 2.0 + 2.0 * pitch,
    ]


def main_bearing_stations(variant: dict[str, Any]) -> list[float]:
    """Dérive les huit stations de palier de la même étude géométrique F35."""

    throws = cylinder_stations(variant)
    envelope = parameter(variant, "crankshaft_envelope_length_mm")
    width = parameter(variant, "main_journal_width_mm")
    end = envelope / 2.0 - width / 2.0 - 3.0
    central_half_gap = (throws[3] - throws[2]) / 4.0
    return [
        -end,
        (throws[0] + throws[1]) / 2.0,
        (throws[1] + throws[2]) / 2.0,
        -central_half_gap,
        central_half_gap,
        (throws[3] + throws[4]) / 2.0,
        (throws[4] + throws[5]) / 2.0,
        end,
    ]


def ring_offsets_from_pin_mm(variant: dict[str, Any]) -> list[float]:
    """Retourne les trois datums visuels de segments depuis l'axe de piston."""

    count = int(round(parameter(variant, "ring_count")))
    require(count == 3, f"f35_ring_count_must_be_three:{variant.get('id')}")
    crown = parameter(variant, "piston_crown_to_pin_axis_mm")
    ring_height = parameter(variant, "ring_axial_height_mm")
    crown_thickness = max(7.0, parameter(variant, "bore_mm") * 0.085)
    first = crown - crown_thickness - ring_height
    return [first - index * (ring_height + 2.0) for index in range(count)]


def _normalise_relative(path: Path, base: Path) -> str:
    return os.path.relpath(path, base).replace(os.sep, "/")


def _repo_relative(path: Path) -> str:
    resolved = path.resolve()
    require(resolved.is_relative_to(REPO_ROOT), f"path_outside_repository:{path}")
    return resolved.relative_to(REPO_ROOT).as_posix()


def _physics_findings(stage: Usd.Stage) -> list[str]:
    """Signale les schémas/propriétés de physique actifs dans un stage USD."""

    findings: list[str] = []
    roots: list[Iterable[Usd.Prim]] = [stage.TraverseAll()]
    roots.extend(Usd.PrimRange(prototype) for prototype in stage.GetPrototypes())
    visited: set[str] = set()
    for traversal in roots:
        for prim in traversal:
            identity = f"{prim.GetStage().GetRootLayer().identifier}:{prim.GetPath()}"
            if identity in visited:
                continue
            visited.add(identity)
            type_name = prim.GetTypeName()
            if type_name in FORBIDDEN_PRIM_TYPES or type_name.endswith("Joint"):
                findings.append(f"forbidden_prim_type:{prim.GetPath()}:{type_name}")
            for schema in prim.GetAppliedSchemas():
                schema_name = str(schema)
                if any(fragment in schema_name for fragment in FORBIDDEN_APPLIED_SCHEMA_FRAGMENTS):
                    findings.append(f"forbidden_applied_schema:{prim.GetPath()}:{schema_name}")
            for prop in prim.GetProperties():
                name = str(prop.GetName()).lower()
                if name.startswith("physics:") or name.startswith("physx"):
                    findings.append(f"forbidden_physics_property:{prim.GetPath()}:{prop.GetName()}")
    return sorted(set(findings))


def _validate_contract(contract_path: Path, contract: dict[str, Any]) -> list[dict[str, Any]]:
    """Vérifie le verrou de variantes, de comptes et de release avant écriture."""

    require(contract_path.resolve() == CONTRACT_PATH.resolve(), "contract_path_must_be_f35_canonical")
    require(contract.get("phase") == "F35", "contract_phase_must_be_F35")
    require(contract.get("units") == "mm", "contract_units_must_be_mm")
    policy = contract.get("cad_policy")
    require(isinstance(policy, dict), "cad_policy_required")
    require(policy.get("separate_variant_output_required") is True, "separate_variant_output_required")
    require(policy.get("analytical_linkage_closure_required") is True, "analytical_closure_required")
    require(policy.get("physical_joint_authoring_allowed") is False, "physical_joint_authoring_must_be_false")
    require(policy.get("mass_or_inertia_assignment_allowed") is False, "mass_or_inertia_must_be_false")
    output_policy = contract.get("output_policy")
    require(isinstance(output_policy, dict), "output_policy_required")
    require(
        output_policy.get("generated_root") == "work/917-rotating-assembly-f35",
        "unexpected_generated_root",
    )
    require(
        set(output_policy.get("derived_formats", []))
        == {"STEP", "STL", "JSON", "USD", "USDC"},
        "unexpected_derived_formats",
    )
    output_layout = output_policy.get("derived_output_layout")
    require(isinstance(output_layout, dict), "derived_output_layout_required")
    require(
        output_layout.get("converted_usd_prototype")
        == "usd-conversion/{variant}/prototypes/{family}/{family}.usd",
        "unexpected_usd_prototype_layout",
    )
    require(
        output_layout.get("animated_usdc_stage")
        == "{variant}/usd/rotating-assembly-f35.usdc",
        "unexpected_usdc_stage_layout",
    )
    require(
        contract.get("required_interface_frames_per_variant")
        == list(EXPECTED_DATUM_FRAME_COUNTS),
        "unexpected_required_interface_frame_families",
    )
    require(
        contract.get("required_interface_frame_counts_per_variant")
        == EXPECTED_DATUM_FRAME_COUNTS,
        "unexpected_required_interface_frame_counts",
    )
    expected_counts = contract.get("expected_component_counts_per_variant")
    require(expected_counts == COMPONENT_COUNTS, "unexpected_component_counts")
    require(sum(expected_counts.values()) == EXPECTED_COMPONENT_TOTAL, "unexpected_component_total")
    gates = contract.get("release_gates")
    require(isinstance(gates, dict) and gates, "release_gates_required")
    require(
        all(value is False for value in gates.values()),
        "all_release_gates_must_be_explicitly_false",
    )
    require(gates.get("manufacturing_geometry_ready") is False, "manufacturing_gate_must_be_false")
    require(gates.get("engine_start_authorized") is False, "engine_start_gate_must_be_false")
    require(
        gates.get("performance_1600_hp_claim_authorized") is False,
        "performance_1600_hp_gate_must_be_false",
    )
    variants = contract.get("variants")
    require(isinstance(variants, list), "variants_list_required")
    require(tuple(item.get("id") for item in variants) == EXPECTED_VARIANT_IDS, "exact_variant_ids_required")
    return variants


def _resolve_prototype(variant_id: str, source_family: str) -> Path:
    directory = WORK_ROOT / "usd-conversion" / variant_id / "prototypes" / source_family
    candidates = [
        directory / f"{source_family}{suffix}"
        for suffix in (".usd", ".usda", ".usdc")
        if (directory / f"{source_family}{suffix}").is_file()
    ]
    require(len(candidates) == 1, f"exactly_one_usd_prototype_required:{variant_id}:{source_family}")
    return candidates[0].resolve()


def _prototype_freshness_record(
    variant_id: str,
    source_family: str,
    prototype_path: Path,
) -> dict[str, Any]:
    """Lie un prototype USD au STEP exact et à son rapport de conversion."""

    source_step = (WORK_ROOT / variant_id / "step" / f"{source_family}.step").resolve()
    report_path = prototype_path.parent / "conversion-report.json"
    require(source_step.is_file(), f"prototype_source_step_missing:{variant_id}:{source_family}")
    require(report_path.is_file(), f"prototype_conversion_report_missing:{variant_id}:{source_family}")
    report = load_json(report_path)
    require(report.get("status") == "passed", f"prototype_conversion_not_passed:{variant_id}:{source_family}")
    require(
        report.get("atomic_output_commit") is True,
        f"prototype_conversion_not_atomic:{variant_id}:{source_family}",
    )
    require(
        report.get("source_stable_during_conversion") is True,
        f"prototype_source_changed_during_conversion:{variant_id}:{source_family}",
    )
    report_source = report.get("source_asset")
    report_output = report.get("output_usd")
    require(isinstance(report_source, str), f"prototype_report_source_path_required:{variant_id}:{source_family}")
    require(isinstance(report_output, str), f"prototype_report_output_path_required:{variant_id}:{source_family}")
    require(
        Path(report_source).resolve() == source_step,
        f"prototype_report_source_path_mismatch:{variant_id}:{source_family}",
    )
    require(
        Path(report_output).resolve() == prototype_path.resolve(),
        f"prototype_report_output_path_mismatch:{variant_id}:{source_family}",
    )
    source_digest = sha256(source_step)
    output_digest = sha256(prototype_path)
    require(
        report.get("source_sha256") == source_digest,
        f"prototype_source_digest_stale:{variant_id}:{source_family}",
    )
    require(
        report.get("output_sha256") == output_digest,
        f"prototype_output_digest_stale:{variant_id}:{source_family}",
    )
    require(
        report.get("requested_up_axis") == USD_UP_AXIS,
        f"prototype_report_up_axis_mismatch:{variant_id}:{source_family}",
    )

    stage = Usd.Stage.Open(str(prototype_path))
    require(stage is not None, f"prototype_usd_open_failed:{variant_id}:{source_family}")
    require(stage.GetDefaultPrim().IsValid(), f"prototype_default_prim_required:{variant_id}:{source_family}")
    up_axis = str(UsdGeom.GetStageUpAxis(stage)).upper()
    meters_per_unit = float(UsdGeom.GetStageMetersPerUnit(stage))
    require(up_axis == USD_UP_AXIS, f"prototype_up_axis_must_be_Z:{variant_id}:{source_family}:{up_axis}")
    require(
        meters_per_unit == USD_METERS_PER_UNIT,
        f"prototype_meters_per_unit_must_be_0_001:{variant_id}:{source_family}:{meters_per_unit}",
    )
    findings = _physics_findings(stage)
    require(not findings, f"prototype_contains_active_physics:{variant_id}:{source_family}:{findings}")
    return {
        "source_family": source_family,
        "source_step_path": _repo_relative(source_step),
        "source_step_sha256": source_digest,
        "conversion_report_path": _repo_relative(report_path),
        "conversion_report_sha256": sha256(report_path),
        "path": _repo_relative(prototype_path),
        "sha256": output_digest,
        "atomic_output_commit": True,
        "up_axis": up_axis,
        "meters_per_unit": meters_per_unit,
    }


def _preflight_prototypes(variants: list[dict[str, Any]]) -> dict[str, dict[str, Path]]:
    """Résout et audite les douze prototypes avant de créer une sortie."""

    resolved: dict[str, dict[str, Path]] = {}
    for variant in variants:
        variant_id = variant["id"]
        sources: dict[str, Path] = {}
        for family, source_family in SOURCE_PROTOTYPE_FAMILIES.items():
            path = _resolve_prototype(variant_id, source_family)
            _prototype_freshness_record(variant_id, source_family, path)
            sources[family] = path
        require(len(sources) == len(SOURCE_PROTOTYPE_FAMILIES), f"six_prototypes_required:{variant_id}")
        resolved[variant_id] = sources
    return resolved


def _create_occurrence(
    stage: Usd.Stage,
    *,
    path: str,
    stage_path: Path,
    prototype_path: Path,
    family: str,
    variant_id: str,
) -> tuple[Usd.Prim, UsdGeom.Xformable]:
    """Crée une occurrence instanciée et une référence USD relative."""

    xform = UsdGeom.Xform.Define(stage, path)
    prim = xform.GetPrim()
    asset_path = _normalise_relative(prototype_path, stage_path.parent)
    prim.GetReferences().AddReference(asset_path)
    prim.SetInstanceable(True)
    # Le convertisseur CAO référence lui-même des prims ``component``. Le
    # conteneur d'occurrence doit donc être un modèle ``assembly`` afin de
    # conserver une hiérarchie Kind valide après composition.
    prim.SetMetadata("kind", "assembly")
    prim.SetCustomDataByKey("3dprinting993:family", family)
    prim.SetCustomDataByKey("3dprinting993:isOccurrence", True)
    prim.SetCustomDataByKey("3dprinting993:variantId", variant_id)
    prim.SetCustomDataByKey("3dprinting993:releaseStatus", "research_display_only")
    prim.SetCustomDataByKey("3dprinting993:propertyAssignmentIntent", "display_only_inherited")
    return prim, UsdGeom.Xformable(prim)


def _set_translation(op: UsdGeom.XformOp, value: Iterable[float], time: float | None = None) -> None:
    vector = Gf.Vec3d(*(float(component) for component in value))
    op.Set(vector) if time is None else op.Set(vector, Usd.TimeCode(time))


def _set_rotation_x(op: UsdGeom.XformOp, value: float, time: float | None = None) -> None:
    op.Set(float(value)) if time is None else op.Set(float(value), Usd.TimeCode(time))


def _flatten_sample(sample: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        piston["geometric_id"]: piston
        for crankpin in sample["crankpins"]
        for piston in crankpin["pistons"]
    }


def _define_candidate(
    stage: Usd.Stage,
    *,
    candidate_id: str,
    candidate_type: str,
    body0_path: str,
    body1_path: str,
    axis: Iterable[float],
) -> tuple[Usd.Prim, UsdGeom.XformOp]:
    """Crée un repère Xform descriptif, jamais un joint de physique."""

    xform = UsdGeom.Xform.Define(stage, f"/World/InterfaceCandidates/{candidate_id}")
    prim = xform.GetPrim()
    prim.SetCustomDataByKey("3dprinting993:candidateType", candidate_type)
    prim.SetCustomDataByKey("3dprinting993:body0Path", body0_path)
    prim.SetCustomDataByKey("3dprinting993:body1Path", body1_path)
    prim.SetCustomDataByKey("3dprinting993:axisJson", json.dumps([float(value) for value in axis]))
    prim.SetCustomDataByKey("3dprinting993:enabled", False)
    prim.SetCustomDataByKey("3dprinting993:physicsJointAuthored", False)
    prim.SetCustomDataByKey("3dprinting993:status", "candidate_frame_only")
    return prim, xform.AddTranslateOp(precision=UsdGeom.XformOp.PrecisionDouble)


def _define_datum(
    stage: Usd.Stage,
    *,
    family: str,
    datum_id: str,
    member_id: str,
    kind: str,
    axis: Iterable[float],
) -> tuple[Usd.Prim, UsdGeom.XformOp]:
    """Crée un datum contractuel descriptif, distinct des joints candidats."""

    xform = UsdGeom.Xform.Define(stage, f"/World/Datums/{family}/{datum_id}")
    prim = xform.GetPrim()
    direction = [float(value) for value in axis]
    require(len(direction) == 3, f"datum_axis_must_have_three_components:{datum_id}")
    require(
        abs(sum(value * value for value in direction) - 1.0) <= 1.0e-12,
        f"datum_axis_must_be_unit:{datum_id}",
    )
    prim.SetCustomDataByKey("3dprinting993:datumFamily", family)
    prim.SetCustomDataByKey("3dprinting993:datumId", datum_id)
    prim.SetCustomDataByKey("3dprinting993:memberId", member_id)
    prim.SetCustomDataByKey("3dprinting993:datumKind", kind)
    prim.SetCustomDataByKey("3dprinting993:axisJson", json.dumps(direction))
    prim.SetCustomDataByKey("3dprinting993:classification", "design_hypothesis_frame_not_measured")
    prim.SetCustomDataByKey("3dprinting993:measured", False)
    prim.SetCustomDataByKey("3dprinting993:physicsJointAuthored", False)
    prim.SetCustomDataByKey("3dprinting993:status", "contract_datum_display_only")
    return prim, xform.AddTranslateOp(precision=UsdGeom.XformOp.PrecisionDouble)


def _new_stage(stage_path: Path, variant: dict[str, Any], contract: dict[str, Any]) -> Usd.Stage:
    stage = Usd.Stage.CreateNew(str(stage_path))
    require(stage is not None, f"usd_stage_create_failed:{stage_path}")
    UsdGeom.SetStageMetersPerUnit(stage, USD_METERS_PER_UNIT)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    stage.SetStartTimeCode(0.0)
    stage.SetEndTimeCode(720.0)
    stage.SetTimeCodesPerSecond(CRANK_DEGREES_PER_SECOND)
    stage.SetFramesPerSecond(CRANK_DEGREES_PER_SECOND)
    stage.SetInterpolationType(Usd.InterpolationTypeLinear)
    world = UsdGeom.Xform.Define(stage, "/World").GetPrim()
    stage.SetDefaultPrim(world)
    world.SetMetadata("kind", "assembly")
    world.SetCustomDataByKey("3dprinting993:phase", "F35")
    world.SetCustomDataByKey("3dprinting993:variantId", variant["id"])
    world.SetCustomDataByKey("3dprinting993:architecture", variant["architecture"])
    world.SetCustomDataByKey("3dprinting993:status", "animated_display_only_no_active_physics")
    world.SetCustomDataByKey("3dprinting993:kinematicsAuthority", "rotating_assembly_f35_math.py")
    world.SetCustomDataByKey("3dprinting993:propertyAssignmentIntent", "skip_physical_properties")
    world.SetCustomDataByKey("3dprinting993:physicalJointCount", 0)
    world.SetCustomDataByKey("3dprinting993:rigidBodyCount", 0)
    world.SetCustomDataByKey("3dprinting993:colliderCount", 0)
    world.SetCustomDataByKey("3dprinting993:massOrInertiaAuthored", False)
    world.SetCustomDataByKey("3dprinting993:physicalMaterialAuthored", False)
    world.SetCustomDataByKey("3dprinting993:releaseGatesJson", json.dumps(contract["release_gates"], sort_keys=True))
    world.SetCustomDataByKey(
        "3dprinting993:geometricCrankpinPhasesDegJson",
        json.dumps(list(DESIGN_CRANKPIN_PHASES_DEG)),
    )
    world.SetCustomDataByKey("3dprinting993:firingOrderUsed", False)
    world.SetCustomDataByKey("3dprinting993:cycleStartDeg", 0.0)
    world.SetCustomDataByKey("3dprinting993:cycleEndDeg", 720.0)
    world.SetCustomDataByKey("3dprinting993:cycleStepDeg", SAMPLE_STEP_DEG)
    world.SetCustomDataByKey("3dprinting993:crankDegreesPerSecond", CRANK_DEGREES_PER_SECOND)
    world.SetCustomDataByKey("3dprinting993:upAxis", USD_UP_AXIS)
    world.SetCustomDataByKey("3dprinting993:metersPerUnit", USD_METERS_PER_UNIT)
    for key in FALSE_STAGE_METADATA_KEYS:
        world.SetCustomDataByKey(key, False)
        world.SetCustomDataByKey(f"3dprinting993:{key}", False)
    components = UsdGeom.Scope.Define(stage, "/World/Components").GetPrim()
    components.SetMetadata("kind", "group")
    for family in COMPONENT_COUNTS:
        family_group = UsdGeom.Scope.Define(stage, f"/World/Components/{family}").GetPrim()
        family_group.SetMetadata("kind", "group")
    interfaces = UsdGeom.Scope.Define(stage, "/World/InterfaceCandidates").GetPrim()
    interfaces.SetCustomDataByKey("3dprinting993:enabledCount", 0)
    interfaces.SetCustomDataByKey("3dprinting993:expectedCandidateCount", EXPECTED_CANDIDATE_INTERFACE_COUNT)
    interfaces.SetCustomDataByKey("3dprinting993:physicalJointAuthoringAllowed", False)
    datums = UsdGeom.Scope.Define(stage, "/World/Datums").GetPrim()
    datums.SetCustomDataByKey("3dprinting993:expectedDatumCount", EXPECTED_DATUM_FRAME_TOTAL)
    datums.SetCustomDataByKey("3dprinting993:measuredDatumCount", 0)
    datums.SetCustomDataByKey("3dprinting993:physicalJointAuthoringAllowed", False)
    for family, count in EXPECTED_DATUM_FRAME_COUNTS.items():
        family_scope = UsdGeom.Scope.Define(stage, f"/World/Datums/{family}").GetPrim()
        family_scope.SetCustomDataByKey("3dprinting993:expectedCount", count)

    review_camera = UsdGeom.Camera.Define(stage, "/World/ReviewCamera")
    review_camera.GetProjectionAttr().Set(UsdGeom.Tokens.perspective)
    review_camera.GetHorizontalApertureAttr().Set(36.0)
    review_camera.GetVerticalApertureAttr().Set(24.0)
    review_camera.GetFocalLengthAttr().Set(50.0)
    review_camera.GetClippingRangeAttr().Set(Gf.Vec2f(10.0, 5000.0))
    review_transform = Gf.Matrix4d().SetLookAt(
        Gf.Vec3d(1000.0, -1200.0, 900.0),
        Gf.Vec3d(0.0, 0.0, 0.0),
        Gf.Vec3d(0.0, 0.0, 1.0),
    ).GetInverse()
    UsdGeom.Xformable(review_camera.GetPrim()).AddTransformOp(
        precision=UsdGeom.XformOp.PrecisionDouble
    ).Set(review_transform)
    review_camera.GetPrim().SetCustomDataByKey("3dprinting993:status", "diagnostic_view_only")
    return stage


def _author_variant(
    *,
    contract_path: Path,
    contract: dict[str, Any],
    variant: dict[str, Any],
    prototypes: dict[str, Path],
) -> dict[str, Any]:
    """Compose un stage complet et son rapport JSON pour une variante."""

    variant_id = variant["id"]
    output_dir = WORK_ROOT / variant_id / "usd"
    output_dir.mkdir(parents=True, exist_ok=True)
    final_stage_path = output_dir / USD_FILENAME
    temporary_stage_path = _temporary_stage_path(final_stage_path)
    stage = _new_stage(temporary_stage_path, variant, contract)

    stations = cylinder_stations(variant)
    bearings = main_bearing_stations(variant)
    ring_offsets = ring_offsets_from_pin_mm(variant)
    crank_radius = parameter(variant, "crank_radius_mm")
    rod_length = parameter(variant, "rod_center_distance_mm")
    rod_width = parameter(variant, "rod_width_mm")
    paired_rod_layout = paired_rod_axial_layout_mm(rod_width)
    world = stage.GetPrimAtPath("/World")
    world.SetCustomDataByKey(
        "3dprinting993:pairedRodAxialLayoutJson",
        json.dumps(paired_rod_layout, sort_keys=True),
    )
    angles = cycle_angles_deg(SAMPLE_STEP_DEG)
    samples = [
        assembly_sample(
            crank_angle_deg=angle,
            station_x_mm=stations,
            crankpin_phases_deg=DESIGN_CRANKPIN_PHASES_DEG,
            crank_radius_mm=crank_radius,
            connecting_rod_length_mm=rod_length,
        )
        for angle in angles
    ]
    states_by_angle = [_flatten_sample(sample) for sample in samples]
    geometric_ids = sorted(states_by_angle[0])
    require(len(geometric_ids) == 12, f"twelve_geometric_pistons_required:{variant_id}")

    occurrence_paths: dict[str, list[str]] = {family: [] for family in COMPONENT_COUNTS}
    crank_path = "/World/Components/crankshaft/crankshaft"
    _, crank_xform = _create_occurrence(
        stage,
        path=crank_path,
        stage_path=temporary_stage_path,
        prototype_path=prototypes["crankshaft"],
        family="crankshaft",
        variant_id=variant_id,
    )
    crank_rotate = crank_xform.AddRotateXOp(precision=UsdGeom.XformOp.PrecisionDouble)
    occurrence_paths["crankshaft"].append(crank_path)
    for angle in angles:
        _set_rotation_x(crank_rotate, angle, angle)

    for index, station in enumerate(bearings, start=1):
        path = f"/World/Components/main_bearing/main_bearing_{index:02d}"
        _, xform = _create_occurrence(
            stage,
            path=path,
            stage_path=temporary_stage_path,
            prototype_path=prototypes["main_bearing"],
            family="main_bearing",
            variant_id=variant_id,
        )
        translate = xform.AddTranslateOp(precision=UsdGeom.XformOp.PrecisionDouble)
        _set_translation(translate, (station, 0.0, 0.0))
        occurrence_paths["main_bearing"].append(path)

    rod_ops: dict[str, tuple[UsdGeom.XformOp, UsdGeom.XformOp]] = {}
    piston_ops: dict[str, UsdGeom.XformOp] = {}
    pin_ops: dict[str, UsdGeom.XformOp] = {}
    ring_ops: dict[str, UsdGeom.XformOp] = {}
    for geometric_id in geometric_ids:
        initial = states_by_angle[0][geometric_id]
        bank = initial["bank"]
        bank_rotation = 0.0 if bank == "bank_A" else 180.0

        rod_path = f"/World/Components/connecting_rod/connecting_rod_{geometric_id}"
        rod_prim, rod_xform = _create_occurrence(
            stage,
            path=rod_path,
            stage_path=temporary_stage_path,
            prototype_path=prototypes["connecting_rod"],
            family="connecting_rod",
            variant_id=variant_id,
        )
        rod_translate = rod_xform.AddTranslateOp(precision=UsdGeom.XformOp.PrecisionDouble)
        rod_rotate = rod_xform.AddRotateXOp(precision=UsdGeom.XformOp.PrecisionDouble)
        rod_prim.SetCustomDataByKey(
            "3dprinting993:pairedRodAxialOffsetMm",
            paired_rod_axial_offset_mm(bank, rod_width),
        )
        rod_prim.SetCustomDataByKey(
            "3dprinting993:pairedRodTopology",
            paired_rod_layout["topology"],
        )
        rod_ops[geometric_id] = (rod_translate, rod_rotate)
        occurrence_paths["connecting_rod"].append(rod_path)

        piston_path = f"/World/Components/piston/piston_{geometric_id}"
        _, piston_xform = _create_occurrence(
            stage,
            path=piston_path,
            stage_path=temporary_stage_path,
            prototype_path=prototypes["piston"],
            family="piston",
            variant_id=variant_id,
        )
        piston_translate = piston_xform.AddTranslateOp(precision=UsdGeom.XformOp.PrecisionDouble)
        piston_rotate = piston_xform.AddRotateXOp(precision=UsdGeom.XformOp.PrecisionDouble)
        _set_rotation_x(piston_rotate, bank_rotation)
        piston_ops[geometric_id] = piston_translate
        occurrence_paths["piston"].append(piston_path)

        pin_path = f"/World/Components/piston_pin/piston_pin_{geometric_id}"
        _, pin_xform = _create_occurrence(
            stage,
            path=pin_path,
            stage_path=temporary_stage_path,
            prototype_path=prototypes["piston_pin"],
            family="piston_pin",
            variant_id=variant_id,
        )
        pin_translate = pin_xform.AddTranslateOp(precision=UsdGeom.XformOp.PrecisionDouble)
        pin_ops[geometric_id] = pin_translate
        occurrence_paths["piston_pin"].append(pin_path)

        for ring_index, _ in enumerate(ring_offsets, start=1):
            ring_id = f"{geometric_id}_{ring_index:02d}"
            ring_path = f"/World/Components/piston_ring/piston_ring_{ring_id}"
            _, ring_xform = _create_occurrence(
                stage,
                path=ring_path,
                stage_path=temporary_stage_path,
                prototype_path=prototypes["piston_ring"],
                family="piston_ring",
                variant_id=variant_id,
            )
            ring_translate = ring_xform.AddTranslateOp(precision=UsdGeom.XformOp.PrecisionDouble)
            ring_rotate = ring_xform.AddRotateXOp(precision=UsdGeom.XformOp.PrecisionDouble)
            _set_rotation_x(ring_rotate, bank_rotation)
            ring_ops[ring_id] = ring_translate
            occurrence_paths["piston_ring"].append(ring_path)

    datum_prims: list[Usd.Prim] = []
    datum_ops: dict[str, UsdGeom.XformOp] = {}

    def add_datum(
        *,
        family: str,
        datum_id: str,
        member_id: str,
        kind: str,
        axis: Iterable[float],
        origin: Iterable[float] | None = None,
    ) -> UsdGeom.XformOp:
        prim, op = _define_datum(
            stage,
            family=family,
            datum_id=datum_id,
            member_id=member_id,
            kind=kind,
            axis=axis,
        )
        datum_prims.append(prim)
        datum_ops[datum_id] = op
        if origin is not None:
            _set_translation(op, origin)
        return op

    add_datum(
        family="crankshaft_axis",
        datum_id="crankshaft_axis",
        member_id="crankshaft",
        kind="revolute_candidate_axis",
        axis=CRANK_AXIS,
        origin=(0.0, 0.0, 0.0),
    )
    for index, station in enumerate(bearings, start=1):
        add_datum(
            family="main_journal_centres_01_to_08",
            datum_id=f"main_journal_centre_{index:02d}",
            member_id=f"main_journal_{index:02d}",
            kind="revolute_candidate_load_station",
            axis=CRANK_AXIS,
            origin=(station, 0.0, 0.0),
        )

    crankpin_datum_ops: dict[str, UsdGeom.XformOp] = {}
    for crankpin in samples[0]["crankpins"]:
        station_id = str(crankpin["station_id"])
        crankpin_datum_ops[station_id] = add_datum(
            family="crankpin_centres_01_to_06",
            datum_id=f"crankpin_centre_{station_id}",
            member_id=station_id,
            kind="revolute_candidate_axis",
            axis=CRANK_AXIS,
        )

    moving_datum_ops: dict[str, dict[str, Any]] = {}
    for geometric_id in geometric_ids:
        initial = states_by_angle[0][geometric_id]
        bank_axis = BANK_AXES[initial["bank"]]
        per_member: dict[str, Any] = {
            "rod_big_end_axis": add_datum(
                family="rod_big_end_axis",
                datum_id=f"rod_big_end_axis_{geometric_id}",
                member_id=geometric_id,
                kind="revolute_candidate_axis",
                axis=CRANK_AXIS,
            ),
            "rod_small_end_axis": add_datum(
                family="rod_small_end_axis",
                datum_id=f"rod_small_end_axis_{geometric_id}",
                member_id=geometric_id,
                kind="revolute_candidate_axis",
                axis=CRANK_AXIS,
            ),
            "piston_pin_axis": add_datum(
                family="piston_pin_axis",
                datum_id=f"piston_pin_axis_{geometric_id}",
                member_id=geometric_id,
                kind="revolute_candidate_axis",
                axis=CRANK_AXIS,
            ),
            "piston_crown_datum": add_datum(
                family="piston_crown_datum",
                datum_id=f"piston_crown_datum_{geometric_id}",
                member_id=geometric_id,
                kind="plane_datum",
                axis=bank_axis,
            ),
            "piston_ring_groove_datums": [],
        }
        for ring_index in range(1, len(ring_offsets) + 1):
            per_member["piston_ring_groove_datums"].append(
                add_datum(
                    family="piston_ring_groove_datums",
                    datum_id=f"piston_ring_groove_datum_{geometric_id}_{ring_index:02d}",
                    member_id=f"{geometric_id}_{ring_index:02d}",
                    kind="plane_datum",
                    axis=bank_axis,
                )
            )
        moving_datum_ops[geometric_id] = per_member

    crank_candidate_path = "crankcase_to_crankshaft"
    _, crank_candidate_op = _define_candidate(
        stage,
        candidate_id=crank_candidate_path,
        candidate_type="revolute_candidate",
        body0_path="/World/UnresolvedCrankcaseDatum",
        body1_path=crank_path,
        axis=CRANK_AXIS,
    )
    _set_translation(crank_candidate_op, (0.0, 0.0, 0.0))
    candidate_ops: dict[str, tuple[UsdGeom.XformOp, UsdGeom.XformOp, UsdGeom.XformOp]] = {}
    for geometric_id in geometric_ids:
        rod_path = f"/World/Components/connecting_rod/connecting_rod_{geometric_id}"
        pin_path = f"/World/Components/piston_pin/piston_pin_{geometric_id}"
        piston_path = f"/World/Components/piston/piston_{geometric_id}"
        _, crankpin_op = _define_candidate(
            stage,
            candidate_id=f"crankpin_to_rod_{geometric_id}",
            candidate_type="revolute_candidate",
            body0_path=crank_path,
            body1_path=rod_path,
            axis=CRANK_AXIS,
        )
        _, rod_pin_op = _define_candidate(
            stage,
            candidate_id=f"rod_to_pin_{geometric_id}",
            candidate_type="revolute_candidate",
            body0_path=rod_path,
            body1_path=pin_path,
            axis=CRANK_AXIS,
        )
        _, piston_axis_op = _define_candidate(
            stage,
            candidate_id=f"piston_to_cylinder_{geometric_id}",
            candidate_type="prismatic_candidate",
            body0_path=f"/World/UnresolvedCylinderDatums/{geometric_id}",
            body1_path=piston_path,
            axis=BANK_AXES[states_by_angle[0][geometric_id]["bank"]],
        )
        candidate_ops[geometric_id] = (crankpin_op, rod_pin_op, piston_axis_op)

    maximum_closure_error = 0.0
    crown = parameter(variant, "piston_crown_to_pin_axis_mm")
    for angle, sample, states in zip(angles, samples, states_by_angle, strict=True):
        for crankpin in sample["crankpins"]:
            _set_translation(
                crankpin_datum_ops[str(crankpin["station_id"])],
                crankpin["center_mm"],
                angle,
            )
        for geometric_id in geometric_ids:
            state = states[geometric_id]
            bank = state["bank"]
            bank_sign = 1.0 if bank == "bank_A" else -1.0
            bank_rotation = 0.0 if bank == "bank_A" else 180.0
            axial_offset = paired_rod_axial_offset_mm(bank, rod_width)
            pin_center = [float(value) for value in state["piston_pin_center_mm"]]
            rod = state["connecting_rod"]
            crankpin_center = [float(value) for value in rod["big_end_center_mm"]]
            pin_center[0] += axial_offset
            crankpin_center[0] += axial_offset
            maximum_closure_error = max(maximum_closure_error, abs(float(rod["closure_error_mm"])))

            rod_translate, rod_rotate = rod_ops[geometric_id]
            _set_translation(rod_translate, crankpin_center, angle)
            _set_rotation_x(rod_rotate, bank_rotation + float(rod["signed_tilt_about_x_deg"]), angle)
            _set_translation(piston_ops[geometric_id], pin_center, angle)
            _set_translation(pin_ops[geometric_id], pin_center, angle)
            member_datums = moving_datum_ops[geometric_id]
            _set_translation(member_datums["rod_big_end_axis"], crankpin_center, angle)
            _set_translation(member_datums["rod_small_end_axis"], pin_center, angle)
            _set_translation(member_datums["piston_pin_axis"], pin_center, angle)
            bank_axis = BANK_AXES[bank]
            crown_center = tuple(
                float(pin_center[index]) + crown * bank_axis[index]
                for index in range(3)
            )
            _set_translation(member_datums["piston_crown_datum"], crown_center, angle)
            for ring_index, offset in enumerate(ring_offsets, start=1):
                ring_id = f"{geometric_id}_{ring_index:02d}"
                ring_center = (
                    float(pin_center[0]),
                    float(pin_center[1]) + bank_sign * offset,
                    float(pin_center[2]),
                )
                _set_translation(ring_ops[ring_id], ring_center, angle)
                _set_translation(
                    member_datums["piston_ring_groove_datums"][ring_index - 1],
                    ring_center,
                    angle,
                )

            crankpin_op, rod_pin_op, piston_axis_op = candidate_ops[geometric_id]
            _set_translation(crankpin_op, crankpin_center, angle)
            _set_translation(rod_pin_op, pin_center, angle)
            _set_translation(piston_axis_op, pin_center, angle)

    require(maximum_closure_error <= 1.0e-9, f"analytical_linkage_not_closed:{variant_id}")
    actual_counts = {family: len(paths) for family, paths in occurrence_paths.items()}
    require(actual_counts == COMPONENT_COUNTS, f"occurrence_count_mismatch:{variant_id}:{actual_counts}")
    candidate_prims = [
        prim
        for prim in Usd.PrimRange(stage.GetPrimAtPath("/World/InterfaceCandidates"))
        if prim.GetPath() != Sdf.Path("/World/InterfaceCandidates")
    ]
    require(
        len(candidate_prims) == EXPECTED_CANDIDATE_INTERFACE_COUNT,
        f"candidate_interface_count_mismatch:{variant_id}:{len(candidate_prims)}",
    )
    require(
        all(prim.GetCustomDataByKey("3dprinting993:enabled") is False for prim in candidate_prims),
        f"candidate_interface_enabled:{variant_id}",
    )
    datum_counts = {
        family: sum(
            prim.GetCustomDataByKey("3dprinting993:datumFamily") == family
            for prim in datum_prims
        )
        for family in EXPECTED_DATUM_FRAME_COUNTS
    }
    require(
        datum_counts == EXPECTED_DATUM_FRAME_COUNTS,
        f"datum_frame_count_mismatch:{variant_id}:{datum_counts}",
    )
    require(
        len(datum_prims) == EXPECTED_DATUM_FRAME_TOTAL,
        f"datum_frame_total_mismatch:{variant_id}:{len(datum_prims)}",
    )
    require(
        all(prim.GetCustomDataByKey("3dprinting993:measured") is False for prim in datum_prims),
        f"measured_datum_authored:{variant_id}",
    )

    pre_export_findings = _physics_findings(stage)
    require(not pre_export_findings, f"active_physics_authored:{variant_id}:{pre_export_findings}")
    stage.GetRootLayer().Save()
    del stage
    os.replace(temporary_stage_path, final_stage_path)

    reopened = Usd.Stage.Open(str(final_stage_path))
    require(reopened is not None, f"usd_stage_reopen_failed:{variant_id}")
    require(
        str(UsdGeom.GetStageUpAxis(reopened)).upper() == USD_UP_AXIS,
        f"assembly_up_axis_must_be_Z:{variant_id}",
    )
    require(
        float(UsdGeom.GetStageMetersPerUnit(reopened)) == USD_METERS_PER_UNIT,
        f"assembly_meters_per_unit_must_be_0_001:{variant_id}",
    )
    findings = _physics_findings(reopened)
    require(not findings, f"composed_stage_contains_active_physics:{variant_id}:{findings}")
    world = reopened.GetPrimAtPath("/World")
    require(world.IsValid(), f"world_prim_missing:{variant_id}")
    for key in FALSE_STAGE_METADATA_KEYS:
        require(world.GetCustomDataByKey(key) is False, f"false_stage_metadata_required:{variant_id}:{key}")

    prototype_records = {
        family: _prototype_freshness_record(
            variant_id,
            SOURCE_PROTOTYPE_FAMILIES[family],
            path,
        )
        for family, path in sorted(prototypes.items())
    }
    report = {
        "schema_version": "1.0.0",
        "phase": "F35",
        "status": "animated_display_only_no_active_physics",
        "variant_id": variant_id,
        "contract_path": _repo_relative(contract_path),
        "contract_sha256": sha256(contract_path),
        "kinematics_authority": "twins/reference-917-engine/source/rotating_assembly_f35_math.py",
        "kinematics_authority_sha256": sha256(Path(__file__).with_name("rotating_assembly_f35_math.py")),
        "usd_path": _repo_relative(final_stage_path),
        "usd_sha256": sha256(final_stage_path),
        "stage_metadata": {
            "up_axis": USD_UP_AXIS,
            "meters_per_unit": USD_METERS_PER_UNIT,
        },
        "atomic_stage_commit": True,
        "prototype_count": len(prototype_records),
        "prototypes": prototype_records,
        "component_occurrence_counts": actual_counts,
        "component_occurrence_total": sum(actual_counts.values()),
        "candidate_interfaces": {
            "crankcase_to_crankshaft_revolute": 1,
            "crankpin_to_rod_revolute": 12,
            "rod_to_pin_revolute": 12,
            "piston_to_cylinder_prismatic": 12,
            "total": len(candidate_prims),
            "enabled": 0,
            "physical_joint_authored": 0,
        },
        "datum_frames": {
            "family_counts": datum_counts,
            "total": len(datum_prims),
            "measured": 0,
            "physical_joint_authored": 0,
        },
        "animation": {
            "start_crank_angle_deg": angles[0],
            "end_crank_angle_deg": angles[-1],
            "sample_step_deg": SAMPLE_STEP_DEG,
            "sample_count": len(angles),
            "time_codes_per_second": CRANK_DEGREES_PER_SECOND,
            "duration_seconds": (angles[-1] - angles[0]) / CRANK_DEGREES_PER_SECOND,
            "interpolation": "linear",
        },
        "kinematics": {
            "crank_axis": list(CRANK_AXIS),
            "bank_axes": {key: list(value) for key, value in BANK_AXES.items()},
            "geometric_crankpin_phases_deg": list(DESIGN_CRANKPIN_PHASES_DEG),
            "firing_order_used": False,
            "historical_cylinder_mapping_resolved": False,
            "maximum_analytical_linkage_closure_error_mm": maximum_closure_error,
        },
        "paired_rod_axial_layout": paired_rod_layout,
        "authored_physics": {
            "active_joint_count": 0,
            "rigid_body_count": 0,
            "collider_count": 0,
            "mass_property_count": 0,
            "inertia_property_count": 0,
            "physical_material_count": 0,
            "audit_findings": findings,
        },
        "property_assignment_intent": "display_only_inherited_from_prototypes",
        "historicalCylinderMappingResolved": False,
        "simulationValidated": False,
        "manufacturingReleased": False,
        "powerValidated": False,
        "release_gates": contract["release_gates"],
        "limitations": [
            "geometric_phase_hypothesis_not_historical_firing_order",
            "display_animation_not_dynamic_simulation",
            "no_mass_inertia_contact_clearance_or_load_validation",
            "not_released_for_manufacturing_engine_start_or_1600_hp_claim",
        ],
    }
    report_path = output_dir / REPORT_FILENAME
    _atomic_write_text(report_path, json.dumps(report, indent=2, sort_keys=True) + "\n")
    published_report = load_json(report_path)
    require(
        published_report.get("usd_sha256") == sha256(final_stage_path),
        f"published_usd_report_digest_mismatch:{variant_id}",
    )
    require(
        published_report.get("contract_sha256") == sha256(contract_path),
        f"published_usd_report_contract_stale:{variant_id}",
    )
    return report


def author_all(contract_path: Path = CONTRACT_PATH, work_root: Path = WORK_ROOT) -> list[dict[str, Any]]:
    """Valide tous les inputs puis produit exactement les deux variantes F35."""

    require(work_root.resolve() == WORK_ROOT.resolve(), "work_root_must_be_f35_canonical")
    contract = load_json(contract_path)
    variants = _validate_contract(contract_path, contract)
    prototypes = _preflight_prototypes(variants)
    return [
        _author_variant(
            contract_path=contract_path,
            contract=contract,
            variant=variant,
            prototypes=prototypes[variant["id"]],
        )
        for variant in variants
    ]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Author F35 display-only animated USD stages for both 917 variants."
    )
    parser.add_argument("--contract", type=Path, default=CONTRACT_PATH)
    parser.add_argument("--work-root", type=Path, default=WORK_ROOT)
    args = parser.parse_args()
    reports = author_all(args.contract, args.work_root)
    print(
        json.dumps(
            {
                "status": "passed",
                "phase": "F35",
                "variant_reports": [
                    {
                        "variant_id": report["variant_id"],
                        "usd_path": report["usd_path"],
                        "usd_sha256": report["usd_sha256"],
                    }
                    for report in reports
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
