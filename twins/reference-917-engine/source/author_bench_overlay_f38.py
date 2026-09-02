#!/usr/bin/env python3
"""Compose un overlay USDA F38 au-dessus du banc sémantique F37.

Le fichier ne contient que des métadonnées de stations et des résultats
numériques fail-closed. Il ne crée ni géométrie, ni schéma physique, ni volume
CFD. Une copie vérifiée du stage F37 est embarquée puis consommée comme sublayer.
"""

from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import json
import math
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONTRACT = REPO_ROOT / "twins/reference-917-engine/gas-path-network-f38.json"
DEFAULT_F37 = REPO_ROOT / "work/917-integrated-bench-f37"
DEFAULT_F38_REPORT = REPO_ROOT / "work/917-gas-path-network-f38/gas-path-network-f38-report.json"
DEFAULT_CANONICAL_F38_REPORT = (
    REPO_ROOT / "twins/reference-917-engine/evidence/f38/gas-path-network-f38-report.json"
)
DEFAULT_OUTPUT = REPO_ROOT / "work/917-gas-path-network-f38/omniverse"
EXPECTED_VARIANT_TO_BENCH = {
    "917_2026_flat12_na_candidate": "type_912_4_5_na",
    "917_2026_flat12_twin_turbo_1600hp_target": "917_30_turbo_5374",
}
EXPECTED_VARIANT_IDS = tuple(EXPECTED_VARIANT_TO_BENCH)
EXPECTED_BENCH_VARIANT_IDS = frozenset(EXPECTED_VARIANT_TO_BENCH.values())
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
EMBEDDED_F37_STAGE_NAME = "integrated-bench-f37.usda"
OVERLAY_NAME = "bench-overlay-f38.usda"


class F38OverlayError(ValueError):
    """Entrée incompatible avec l'overlay fail-closed."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise F38OverlayError(message)


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        require(key not in value, f"duplicate JSON key: {key}")
        value[key] = item
    return value


def reject_nonfinite_constant(value: str) -> None:
    raise F38OverlayError(f"non-finite JSON number forbidden: {value}")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_keys,
        parse_constant=reject_nonfinite_constant,
    )
    require(isinstance(value, dict), f"JSON object required: {path}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def usd_string(value: Any) -> str:
    return json.dumps(str(value), ensure_ascii=True)


def usd_bool(value: bool) -> str:
    return "true" if value else "false"


def usd_number(value: Any, label: str) -> str:
    require(not isinstance(value, bool) and isinstance(value, (int, float)), f"{label} must be numeric")
    number = float(value)
    require(math.isfinite(number), f"{label} must be finite")
    if isinstance(value, int):
        require(int(number) == value, f"{label} cannot be represented exactly as a USD double")
    serialized = repr(number)
    require(float(serialized) == number, f"{label} USD double serialization is not round-trip safe")
    return serialized


def usd_identifier(value: str) -> str:
    identifier = re.sub(r"[^A-Za-z0-9_]", "_", value)
    if not identifier or identifier[0].isdigit():
        identifier = f"station_{identifier}"
    return identifier


def exact_index(
    values: Any,
    key: str,
    expected: set[str] | frozenset[str],
    label: str,
) -> dict[str, dict[str, Any]]:
    require(isinstance(values, list), f"{label} must be a list")
    result: dict[str, dict[str, Any]] = {}
    for item in values:
        require(isinstance(item, dict), f"{label} entries must be objects")
        identifier = item.get(key)
        require(isinstance(identifier, str) and identifier, f"{label}.{key} required")
        require(identifier not in result, f"duplicate {label} {key}: {identifier}")
        result[identifier] = item
    require(set(result) == set(expected), f"unexpected {label} set")
    return result


def require_sha256(value: Any, label: str) -> str:
    require(isinstance(value, str) and SHA256_PATTERN.fullmatch(value) is not None, f"{label} must be SHA-256")
    return value


def resolve_confined_file(root: Path, relative_value: Any, label: str) -> Path:
    require(isinstance(relative_value, str) and relative_value, f"{label} path required")
    relative = Path(relative_value)
    require(not relative.is_absolute(), f"{label} path must be relative")
    try:
        resolved = (root / relative).resolve(strict=True)
    except FileNotFoundError as error:
        raise F38OverlayError(f"{label} missing: {relative_value}") from error
    require(resolved.is_relative_to(root), f"{label} path must remain within F37 root")
    require(resolved.is_file(), f"{label} must be a file")
    return resolved


def validate_contract(contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    require(contract.get("phase") == "F38", "contract.phase must be F38")
    variants = exact_index(
        contract.get("variants"),
        "variant_id",
        frozenset(EXPECTED_VARIANT_IDS),
        "contract variants",
    )
    observed_bench_ids: set[str] = set()
    for variant_id in EXPECTED_VARIANT_IDS:
        expected_bench = EXPECTED_VARIANT_TO_BENCH[variant_id]
        bench_variant = variants[variant_id].get("bench_variant_id")
        require(bench_variant == expected_bench, f"contract bench variant mismatch: {variant_id}")
        require(bench_variant not in observed_bench_ids, f"duplicate contract bench variant: {bench_variant}")
        observed_bench_ids.add(bench_variant)
    require(observed_bench_ids == EXPECTED_BENCH_VARIANT_IDS, "unexpected contract bench variant set")
    policy = contract.get("bench_overlay_policy")
    require(isinstance(policy, dict), "bench_overlay_policy required")
    require(policy.get("f37_runtime_required") is True, "F37 runtime must be required")
    require(policy.get("f37_stage_hash_verification_required") is True, "F37 hash check must be required")
    for key in (
        "geometry_authored",
        "physics_schema_authored",
        "rigid_body_authored",
        "collider_authored",
        "physical_joint_authored",
        "mass_or_inertia_authored",
        "material_binding_authored",
        "cfd_volume_authored",
    ):
        require(policy.get(key) is False, f"overlay policy {key} must be false")
    return variants


def validate_f38(
    report: dict[str, Any],
    contract: dict[str, Any],
    contract_sha: str,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    require(report.get("phase") == "F38", "F38 report phase mismatch")
    require(report.get("contract_sha256") == contract_sha, "F38 report contract hash mismatch")
    require(report.get("variant_count") == 2, "F38 report must contain two variants")
    variants = exact_index(
        report.get("variants"),
        "variant_id",
        frozenset(EXPECTED_VARIANT_IDS),
        "F38 variants",
    )
    observed_bench_ids: set[str] = set()
    for variant_id in EXPECTED_VARIANT_IDS:
        expected_bench = EXPECTED_VARIANT_TO_BENCH[variant_id]
        bench_variant = variants[variant_id].get("bench_variant_id")
        require(bench_variant == expected_bench, f"F38 bench variant mismatch: {variant_id}")
        require(bench_variant not in observed_bench_ids, f"duplicate F38 bench variant: {bench_variant}")
        observed_bench_ids.add(bench_variant)
    require(observed_bench_ids == EXPECTED_BENCH_VARIANT_IDS, "unexpected F38 bench variant set")

    declarations = contract.get("source_evidence")
    evidence = report.get("source_evidence")
    require(isinstance(declarations, dict) and declarations, "contract source_evidence missing")
    require(isinstance(evidence, dict), "F38 source_evidence missing")
    require(set(evidence) == set(declarations), "F38 source evidence set mismatch")
    for source_id, declaration in declarations.items():
        require(isinstance(declaration, dict), f"contract source evidence invalid: {source_id}")
        record = evidence.get(source_id)
        require(isinstance(record, dict), f"F38 source evidence invalid: {source_id}")
        expected_sha = require_sha256(declaration.get("expected_sha256"), f"contract source {source_id}")
        require(record.get("path") == declaration.get("path"), f"F38 source path mismatch: {source_id}")
        require(record.get("expected_sha256") == expected_sha, f"F38 expected source hash mismatch: {source_id}")
        require(record.get("actual_sha256") == expected_sha, f"F38 actual source hash mismatch: {source_id}")
        require(record.get("hash_verified") is True, f"F38 source hash not verified: {source_id}")

    f37_contract_evidence = evidence.get("integrated_bench_contract_f37")
    require(isinstance(f37_contract_evidence, dict), "F37 contract evidence missing from F38 report")
    technical = report.get("technical_gates")
    release = report.get("release_gates")
    require(isinstance(technical, dict) and technical, "F38 technical gates missing")
    require(all(value is True for value in technical.values()), "F38 technical gates must be true")
    require(isinstance(release, dict) and release, "F38 release gates missing")
    require(all(value is False for value in release.values()), "F38 release gates must stay false")
    require(report.get("model_scope", {}).get("unsteady_one_dimensional_gas_dynamics_executed") is False, "F38 unsteady 1D claim must be false")
    return variants, f37_contract_evidence


def validate_f37(
    report: dict[str, Any],
    f37_contract_evidence: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    require(report.get("phase") == "F37", "F37 report phase mismatch")
    require(
        report.get("status") == "semantic_integrated_bench_built_all_physical_gates_blocked",
        "F37 report status mismatch",
    )
    require(report.get("source_integrity_checked") is True, "F37 source integrity must be checked")
    require(report.get("physical_joint_count") == 0, "F37 physical joint count must be zero")
    require(report.get("closed_cfd_volume_count") == 0, "F37 closed CFD volume count must be zero")
    release = report.get("release_gates")
    require(
        isinstance(release, dict) and release and all(value is False for value in release.values()),
        "F37 release gates must stay false",
    )
    config = report.get("config")
    require(isinstance(config, dict), "F37 report config evidence missing")
    require(
        config.get("path") == f37_contract_evidence.get("path"),
        "F37 report config path does not match F38 contract evidence",
    )
    require(
        config.get("sha256") == f37_contract_evidence.get("actual_sha256"),
        "F37 report config hash does not match F38 contract evidence",
    )
    return exact_index(
        report.get("variants"),
        "variant_id",
        EXPECTED_BENCH_VARIANT_IDS,
        "F37 variants",
    )


def validate_station_nodes(
    variant: dict[str, Any],
    expected_nodes: Any,
) -> None:
    variant_id = variant.get("variant_id")
    nodes = variant.get("nodes")
    require(isinstance(nodes, list), f"F38 nodes missing: {variant_id}")
    expected_node_ids = list(expected_nodes) if isinstance(expected_nodes, list) else None
    require(expected_node_ids is not None, f"contract station topology missing: {variant_id}")
    raw_ids: set[str] = set()
    authored_ids: set[str] = set()
    observed_order: list[str] = []
    for node in nodes:
        require(isinstance(node, dict), f"F38 station must be an object: {variant_id}")
        station_id = node.get("id")
        require(isinstance(station_id, str) and station_id, f"F38 station id required: {variant_id}")
        require(station_id not in raw_ids, f"duplicate F38 station id: {variant_id}:{station_id}")
        raw_ids.add(station_id)
        authored_id = usd_identifier(station_id)
        require(
            authored_id not in authored_ids,
            f"colliding USDA station identifier: {variant_id}:{authored_id}",
        )
        authored_ids.add(authored_id)
        observed_order.append(station_id)
    require(observed_order == expected_node_ids, f"F38 station topology mismatch: {variant_id}")


def station_block(node: dict[str, Any], indent: str = "            ") -> list[str]:
    station_id = node.get("id")
    require(isinstance(station_id, str), "station id required")
    lines = [f'{indent}def Scope "{usd_identifier(station_id)}"', f"{indent}{{"]
    lines.append(f"{indent}    custom string stationId = {usd_string(station_id)}")
    lines.append(f'{indent}    custom token modelState = "numerical_station_only"')
    for key, attribute in (
        ("pressure_pa_abs", "pressurePaAbs"),
        ("temperature_k", "temperatureK"),
        ("mass_flow_kg_s", "massFlowKgS"),
        ("air_mass_flow_kg_s", "airMassFlowKgS"),
        ("fuel_mass_flow_kg_s", "fuelMassFlowKgS"),
        ("exhaust_mass_flow_kg_s", "exhaustMassFlowKgS"),
    ):
        if node.get(key) is not None:
            lines.append(f"{indent}    custom double {attribute} = {usd_number(node[key], station_id + '.' + key)}")
    if node.get("classification") is not None:
        lines.append(f"{indent}    custom string classification = {usd_string(node['classification'])}")
    lines.append(f"{indent}}}")
    return lines


def author_usda(
    stage_relative_path: str,
    f37_stage_sha: str,
    f37_contract_sha: str,
    canonical_f38_report_sha: str,
    variant: dict[str, Any],
) -> str:
    bench_variant = variant["bench_variant_id"]
    target = variant["target_comparison"]
    mass = variant["mass_balance"]
    lines = [
        "#usda 1.0",
        "(",
        '    defaultPrim = "World"',
        "    subLayers = [",
        f"        @{stage_relative_path}@",
        "    ]",
        ")",
        "",
        'over "World"',
        "{",
        '    custom string f38Phase = "F38"',
        f"    custom string f38VariantId = {usd_string(variant['variant_id'])}",
        f"    custom string benchVariantId = {usd_string(bench_variant)}",
        '    custom string f38Status = "canonical_f38_report_verified_embedded_f37_stage_digest_checked_all_physical_gates_blocked"',
        f"    custom string f37ContractSha256 = {usd_string(f37_contract_sha)}",
        f"    custom string embeddedF37StageSha256 = {usd_string(f37_stage_sha)}",
        f"    custom string canonicalF38ReportSha256 = {usd_string(canonical_f38_report_sha)}",
        "    custom bool geometryAuthoredByF38 = false",
        "    custom bool physicsSchemaAuthoredByF38 = false",
        "    custom bool physicalJointAuthoredByF38 = false",
        "    custom bool colliderAuthoredByF38 = false",
        "    custom bool massOrInertiaAuthoredByF38 = false",
        "    custom bool unsteadyOneDimensionalGasDynamicsValidated = false",
        "    custom bool compressorMapContainmentValidated = false",
        "    custom bool turbineMapContainmentValidated = false",
        "    custom bool targetPowerProven = false",
        "    custom bool engineStartAuthorized = false",
        "    custom bool manufacturingAuthorized = false",
        "",
        '    over "IntegratedRegistry"',
        "    {",
        '        def Scope "F38GasPath"',
        "        {",
        f"            custom string configuration = {usd_string(variant['configuration'])}",
        f"            custom double engineSpeedRpm = {usd_number(variant['operating_point']['speed_rpm'], 'speed')}",
        f"            custom double airMassFlowKgS = {usd_number(mass['air_mass_flow_kg_s'], 'air flow')}",
        f"            custom double fuelMassFlowKgS = {usd_number(mass['fuel_mass_flow_kg_s'], 'fuel flow')}",
        f"            custom double exhaustMassFlowKgS = {usd_number(mass['exhaust_mass_flow_kg_s'], 'exhaust flow')}",
        f"            custom double massRelativeResidual = {usd_number(mass['relative_residual'], 'mass residual')}",
        f"            custom double forwardPredictedMechanicalHp = {usd_number(target['forward_predicted_mechanical_hp'], 'power')}",
        "            custom bool physicalMassBalanceValidated = false",
        "            custom bool physicalEngineDynoCorrelated = false",
    ]
    if target.get("target_power_mechanical_hp") is not None:
        lines.append(
            f"            custom double targetRequirementMechanicalHp = {usd_number(target['target_power_mechanical_hp'], 'target')}"
        )
    turbo = variant.get("turbo_system")
    if turbo is not None:
        shaft = turbo["steady_shaft_balance"]
        lines.extend(
            [
                f"            custom double compressorPressureRatio = {usd_number(turbo['compressor_pressure_ratio'], 'compressor PR')}",
                f"            custom double correctedAirMassFlowPerTurboKgS = {usd_number(turbo['corrected_air_mass_flow_per_turbo_kg_s'], 'corrected flow')}",
                f"            custom double turbineFlowFraction = {usd_number(shaft['turbine_flow_fraction'], 'turbine fraction')}",
                f"            custom double wastegateBypassFraction = {usd_number(shaft['wastegate_bypass_fraction'], 'wastegate fraction')}",
                f"            custom double shaftRelativeResidual = {usd_number(shaft['relative_shaft_power_residual'], 'shaft residual')}",
                "            custom bool compressorMapDigitized = false",
                "            custom bool turbineMapDigitized = false",
                "            custom bool turboMatchValidated = false",
            ]
        )
    lines.extend(['            def Scope "Stations"', "            {"])
    for node in variant["nodes"]:
        lines.extend(station_block(node, indent="                "))
    lines.extend(["            }", "        }", "    }", "}", ""])
    return "\n".join(lines)


def atomic_publish_directory(temporary: Path, output: Path) -> None:
    require(temporary.parent == output.parent, "atomic publication requires one parent directory")
    require(
        all("/" not in name and name not in {"", ".", ".."} for name in (temporary.name, output.name)),
        "invalid publication directory name",
    )
    parent_flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        parent_flags |= os.O_DIRECTORY
    parent_fd = os.open(output.parent, parent_flags)
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        source = os.fsencode(temporary.name)
        destination = os.fsencode(output.name)
        if hasattr(libc, "renameat2"):
            rename = libc.renameat2
            rename.argtypes = [
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_uint,
            ]
            rename.restype = ctypes.c_int
            result = rename(parent_fd, source, parent_fd, destination, 1)
        elif hasattr(libc, "renameatx_np"):
            rename = libc.renameatx_np
            rename.argtypes = [
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_uint,
            ]
            rename.restype = ctypes.c_int
            result = rename(parent_fd, source, parent_fd, destination, 0x00000004)
        else:
            raise OSError(errno.ENOSYS, "atomic no-replace directory rename unavailable")
        if result != 0:
            observed_errno = ctypes.get_errno()
            raise OSError(observed_errno, os.strerror(observed_errno), output.name)
    finally:
        os.close(parent_fd)


def build_overlays(
    contract_path: Path,
    f37_root: Path,
    f38_report_path: Path,
    canonical_f38_report_path: Path,
    output: Path,
) -> dict[str, Any]:
    contract_path = contract_path.resolve(strict=True)
    f37_root = f37_root.resolve(strict=True)
    f38_report_path = f38_report_path.resolve(strict=True)
    canonical_f38_report_path = canonical_f38_report_path.resolve(strict=True)
    output_parent = output.parent.resolve(strict=True)
    output = output_parent / output.name
    require(f37_root.is_dir(), "F37 work root must be a directory")
    require(f38_report_path.is_file(), "F38 runtime report must be a file")
    require(canonical_f38_report_path.is_file(), "canonical F38 report must be a file")
    require(
        f38_report_path != canonical_f38_report_path,
        "runtime and canonical F38 reports must be distinct files",
    )
    require(not os.path.lexists(output), "output already exists; atomic no-overwrite publication required")
    require(
        not output.is_relative_to(f37_root) and not f37_root.is_relative_to(output),
        "output and F37 work root must not overlap",
    )

    contract = load_json(contract_path)
    contract_variants = validate_contract(contract)
    contract_sha = sha256(contract_path)
    runtime_f38_bytes = f38_report_path.read_bytes()
    canonical_f38_bytes = canonical_f38_report_path.read_bytes()
    runtime_f38_sha = sha256_bytes(runtime_f38_bytes)
    canonical_f38_sha = sha256_bytes(canonical_f38_bytes)
    require(runtime_f38_sha == canonical_f38_sha, "F38 report canonical hash mismatch")
    require(runtime_f38_bytes == canonical_f38_bytes, "F38 report differs from canonical evidence bytes")
    f38 = load_json(f38_report_path)
    f38_variants, f37_contract_evidence = validate_f38(f38, contract, contract_sha)
    f37_report_path = resolve_confined_file(
        f37_root,
        "integrated-bench-f37-report.json",
        "F37 runtime report",
    )
    f37 = load_json(f37_report_path)
    f37_variants = validate_f37(f37, f37_contract_evidence)

    topology = contract.get("station_topology")
    require(isinstance(topology, dict), "contract station_topology required")
    source_stages: dict[str, dict[str, Any]] = {}
    stage_paths: set[Path] = set()
    overlay_payloads: dict[str, str] = {}
    for variant_id in EXPECTED_VARIANT_IDS:
        variant = f38_variants[variant_id]
        contract_variant = contract_variants[variant_id]
        configuration = variant.get("configuration")
        require(configuration == contract_variant.get("configuration"), f"F38 configuration mismatch: {variant_id}")
        topology_record = topology.get(configuration)
        require(isinstance(topology_record, dict), f"contract topology missing: {configuration}")
        validate_station_nodes(variant, topology_record.get("nodes"))

        bench_variant = EXPECTED_VARIANT_TO_BENCH[variant_id]
        f37_variant = f37_variants[bench_variant]
        stage_relative_in_f37 = f37_variant.get("usda_path")
        stage_expected_sha = require_sha256(
            f37_variant.get("usda_sha256"),
            f"F37 stage {bench_variant}",
        )
        stage_path = resolve_confined_file(
            f37_root,
            stage_relative_in_f37,
            f"F37 stage {bench_variant}",
        )
        require(stage_path != f37_report_path, f"F37 stage/report path collision: {bench_variant}")
        require(stage_path not in stage_paths, f"F37 stage path collision: {bench_variant}")
        stage_paths.add(stage_path)
        stage_bytes = stage_path.read_bytes()
        stage_actual_sha = sha256_bytes(stage_bytes)
        require(stage_actual_sha == stage_expected_sha, f"F37 stage hash mismatch: {bench_variant}")
        source_stages[bench_variant] = {
            "source_path": stage_path,
            "source_relative_path": stage_relative_in_f37,
            "declared_sha256": stage_expected_sha,
            "observed_sha256": stage_actual_sha,
            "bytes": stage_bytes,
        }
        overlay_payloads[bench_variant] = author_usda(
            EMBEDDED_F37_STAGE_NAME,
            stage_actual_sha,
            f37_contract_evidence["actual_sha256"],
            canonical_f38_sha,
            variant,
        )

    require(set(source_stages) == EXPECTED_BENCH_VARIANT_IDS, "exactly two distinct F37 stages required")
    require(set(overlay_payloads) == EXPECTED_BENCH_VARIANT_IDS, "exactly two distinct overlays required")

    temporary = Path(tempfile.mkdtemp(prefix=f".{output.name}.f38-overlay-", dir=output.parent))
    try:
        results: list[dict[str, Any]] = []
        for variant_id in EXPECTED_VARIANT_IDS:
            variant = f38_variants[variant_id]
            bench_variant = EXPECTED_VARIANT_TO_BENCH[variant_id]
            source_stage = source_stages[bench_variant]
            variant_output = temporary / bench_variant
            embedded_stage_path = variant_output / EMBEDDED_F37_STAGE_NAME
            overlay_path = variant_output / OVERLAY_NAME
            variant_output.mkdir(parents=True, exist_ok=False)
            embedded_stage_path.write_bytes(source_stage["bytes"])
            require(
                sha256(embedded_stage_path) == source_stage["observed_sha256"],
                f"embedded F37 stage hash mismatch: {bench_variant}",
            )
            overlay_path.write_text(overlay_payloads[bench_variant], encoding="utf-8")
            results.append(
                {
                    "variant_id": variant_id,
                    "bench_variant_id": bench_variant,
                    "f37_source_stage_path": str(source_stage["source_path"]),
                    "f37_source_stage_report_declared_sha256": source_stage["declared_sha256"],
                    "f37_source_stage_observed_sha256": source_stage["observed_sha256"],
                    "embedded_f37_stage_path": f"{bench_variant}/{EMBEDDED_F37_STAGE_NAME}",
                    "embedded_f37_stage_sha256": sha256(embedded_stage_path),
                    "overlay_path": f"{bench_variant}/{OVERLAY_NAME}",
                    "overlay_sha256": sha256(overlay_path),
                    "station_count": len(variant["nodes"]),
                    "geometry_authored": False,
                    "physics_schema_authored": False,
                    "target_power_proven": False,
                }
            )
        report = {
            "schema_version": "1.0.0",
            "phase": "F38",
            "status": "two_canonical_f38_verified_f37_contract_authenticated_embedded_stage_digest_checked_overlays_authored_all_physical_gates_blocked",
            "contract_sha256": contract_sha,
            "f38_report_path": str(f38_report_path),
            "f38_report_sha256": runtime_f38_sha,
            "canonical_f38_report_path": str(canonical_f38_report_path),
            "canonical_f38_report_sha256": canonical_f38_sha,
            "f38_report_matches_canonical_bytes": True,
            "f37_report_path": str(f37_report_path),
            "f37_report_observed_sha256": sha256(f37_report_path),
            "f37_contract_path": f37_contract_evidence["path"],
            "f37_contract_sha256": f37_contract_evidence["actual_sha256"],
            "variant_count": len(results),
            "variants": results,
            "f37_stages_embedded": True,
            "atomic_output_commit": True,
            "existing_output_overwritten": False,
            "openusd_runtime_used": False,
            "geometry_authored": False,
            "physics_schema_authored": False,
            "rigid_body_authored": False,
            "collider_authored": False,
            "physical_joint_authored": False,
            "mass_or_inertia_authored": False,
            "target_power_proven": False,
            "engine_start_authorized": False,
            "manufacturing_authorized": False,
        }
        require(report["variant_count"] == 2, "exactly two overlays required")
        write_json(temporary / "bench-overlay-f38-report.json", report)
        atomic_publish_directory(temporary, output)
        return report
    except Exception:
        if temporary.exists():
            shutil.rmtree(temporary, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="Author fail-closed F38 USDA overlays on F37 stages.")
    parser.add_argument("--contract", default=str(DEFAULT_CONTRACT))
    parser.add_argument("--f37-work-root", default=str(DEFAULT_F37))
    parser.add_argument("--f38-report", default=str(DEFAULT_F38_REPORT))
    parser.add_argument("--canonical-f38-report", default=str(DEFAULT_CANONICAL_F38_REPORT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    arguments = parser.parse_args()
    try:
        report = build_overlays(
            Path(arguments.contract).resolve(),
            Path(arguments.f37_work_root).resolve(),
            Path(arguments.f38_report).resolve(),
            Path(arguments.canonical_f38_report).resolve(),
            Path(arguments.output).resolve(),
        )
    except (F38OverlayError, OSError, json.JSONDecodeError, KeyError, TypeError) as error:
        print(f"F38 overlay error: {error}", file=os.sys.stderr)
        return 2
    print(json.dumps({"phase": "F38", "status": report["status"], "variant_count": report["variant_count"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
