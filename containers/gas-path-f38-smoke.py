#!/usr/bin/env python3
"""Smoke reproductible de l'image CPU F38, sans API ni réseau."""

from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import platform
import pwd
import shutil
import socket
import subprocess
import sys
from typing import Any


APPLICATION_ROOT = Path("/opt/gas-path-f38")
CONTRACT = APPLICATION_ROOT / "twins/reference-917-engine/gas-path-network-f38.json"
RUNNER = (
    APPLICATION_ROOT
    / "twins/reference-917-engine/source/run_gas_path_network_f38.py"
)
CANONICAL_REPORT = (
    APPLICATION_ROOT
    / "twins/reference-917-engine/evidence/f38/gas-path-network-f38-report.json"
)
OUTPUT_ROOT = Path("/tmp/f38-smoke-output")
OUTPUT_REPORT = OUTPUT_ROOT / "gas-path-network-f38-report.json"
RUNTIME_UID = 9138
RUNTIME_GID = 9138
EXPECTED_REPORT_SHA256 = (
    "f433c3a7e0dbfee9139bcd72b244dedfa28bf781101c0bd38ccb47bb9b565e10"
)
EXPECTED_APPLICATION_FILES = {
    "smoke.py",
    "twins/reference-917-engine/source/run_gas_path_network_f38.py",
    "twins/reference-917-engine/gas-path-network-f38.json",
    "twins/reference-917-engine/clean-sheet-cycle-thermal-f33.json",
    "twins/reference-917-engine/doe-surrogate-f34.json",
    "twins/reference-917-engine/air-oil-core-controls-f34a.json",
    "twins/reference-917-engine/integrated-bench-assembly-f37.json",
    "twins/reference-917-engine/evidence/f33/cycle-thermal-report.json",
    "twins/reference-917-engine/evidence/f34/air-oil-forward-seeds-f34b.json",
    "twins/reference-917-engine/evidence/f34/report.json",
    "twins/reference-917-engine/evidence/f38/gas-path-network-f38-report.json",
}
EXPECTED_TECHNICAL_GATES = {
    "charge_cooler_required_duty_computed_from_prescribed_states",
    "f33_turbo_algebra_subset_recomputed_from_same_inputs",
    "nonnegative_energy_complements_constructed",
    "source_hashes_verified",
    "steady_turbo_shaft_identity_closed",
    "two_variant_topology_executed",
    "upstream_mass_identities_rechecked",
}
EXPECTED_RELEASE_GATES = {
    "combustion_and_knock_validated",
    "compressor_map_containment_validated",
    "engine_start_authorized",
    "full_engine_energy_balance_validated",
    "manufacturing_authorized",
    "physical_engine_dyno_correlated",
    "target_power_proven",
    "turbine_map_containment_validated",
    "turbo_rotor_transient_validated",
    "unsteady_one_dimensional_gas_dynamics_validated",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    def reject_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON constant rejected: {value}")

    value = json.loads(path.read_text(encoding="utf-8"), parse_constant=reject_constant)
    require(isinstance(value, dict), f"JSON root must be an object: {path}")
    return value


def runtime_identity_and_filesystem_audit() -> dict[str, Any]:
    account = pwd.getpwuid(RUNTIME_UID)
    require(account.pw_name == "gas-path-f38", "unexpected runtime account")
    require(account.pw_gid == RUNTIME_GID, "unexpected runtime group")
    require(account.pw_dir == "/tmp", "runtime home must be /tmp")
    require(os.getuid() == RUNTIME_UID, "smoke must run as dedicated UID")
    require(os.getgid() == RUNTIME_GID, "smoke must run as dedicated GID")
    require(os.environ.get("HOME") == "/tmp", "HOME must be /tmp")

    write_blocked = False
    try:
        (APPLICATION_ROOT / ".write-probe").write_text("forbidden", encoding="ascii")
    except OSError:
        write_blocked = True
    require(write_blocked, "application payload must not be writable")

    files = {
        str(path.relative_to(APPLICATION_ROOT))
        for path in APPLICATION_ROOT.rglob("*")
        if path.is_file() or path.is_symlink()
    }
    require(files == EXPECTED_APPLICATION_FILES, f"unexpected payload inventory: {files}")
    forbidden = [
        path
        for path in sorted(files)
        if any(token in path.lower() for token in ("raw-scan", "password", "api_key", "id_vastai"))
        or Path(path).suffix.lower() in {".obj", ".stl", ".step", ".usd", ".usdc", ".pem", ".key"}
    ]
    require(not forbidden, f"forbidden payload files: {forbidden}")
    return {
        "uid": os.getuid(),
        "gid": os.getgid(),
        "application_payload_write_blocked": write_blocked,
        "file_count": len(files),
        "forbidden_payload_files": forbidden,
    }


def standard_library_audit() -> dict[str, Any]:
    tree = ast.parse(RUNNER.read_text(encoding="utf-8"), filename=str(RUNNER))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
    unexpected = sorted(roots - set(sys.stdlib_module_names) - {"__future__"})
    require(not unexpected, f"non-standard-library solver imports: {unexpected}")
    return {
        "policy": "python_standard_library_only",
        "import_roots": sorted(roots),
        "unexpected_import_roots": unexpected,
        "external_api_required": False,
        "gpu_required": False,
    }


def source_hash_audit(contract: dict[str, Any]) -> dict[str, Any]:
    declarations = contract.get("source_evidence")
    require(isinstance(declarations, dict), "source_evidence object required")
    require(len(declarations) == 7, "exactly seven source documents required")
    verified: dict[str, str] = {}
    for source_id, declaration in declarations.items():
        require(isinstance(declaration, dict), f"invalid source declaration: {source_id}")
        relative = declaration.get("path")
        expected = declaration.get("expected_sha256")
        require(isinstance(relative, str), f"source path missing: {source_id}")
        require(isinstance(expected, str) and len(expected) == 64, f"source hash missing: {source_id}")
        path = APPLICATION_ROOT / relative
        require(path.is_file(), f"source missing: {relative}")
        actual = sha256(path)
        require(actual == expected, f"source hash mismatch: {source_id}")
        verified[source_id] = actual
    return {"count": len(verified), "verified_sha256": verified}


def network_isolation_audit() -> dict[str, Any]:
    interfaces = sorted(path.name for path in Path("/sys/class/net").iterdir())
    ipv4_routes: list[dict[str, str]] = []
    route_file = Path("/proc/net/route")
    if route_file.is_file():
        for line in route_file.read_text(encoding="ascii").splitlines()[1:]:
            fields = line.split()
            if len(fields) >= 4 and fields[0] != "lo" and int(fields[3], 16) & 0x1:
                ipv4_routes.append(
                    {
                        "interface": fields[0],
                        "destination_hex": fields[1],
                        "gateway_hex": fields[2],
                    }
                )
    ipv6_routed_interfaces: list[str] = []
    ipv6_route_file = Path("/proc/net/ipv6_route")
    if ipv6_route_file.is_file():
        for line in ipv6_route_file.read_text(encoding="ascii").splitlines():
            fields = line.split()
            if len(fields) >= 10 and fields[-1] != "lo":
                ipv6_routed_interfaces.append(fields[-1])
    require(not ipv4_routes, f"unexpected active IPv4 routes: {ipv4_routes}")
    require(
        not ipv6_routed_interfaces,
        f"unexpected active IPv6 routes: {ipv6_routed_interfaces}",
    )
    connection_blocked = False
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.settimeout(0.1)
    try:
        probe.connect(("192.0.2.1", 9))
    except OSError:
        connection_blocked = True
    finally:
        probe.close()
    require(connection_blocked, "network connection unexpectedly succeeded")
    return {
        "verified": True,
        "interfaces": interfaces,
        "external_ipv4_routes": ipv4_routes,
        "external_ipv6_routed_interfaces": ipv6_routed_interfaces,
        "test_net_connection_blocked": connection_blocked,
    }


def execute_and_compare() -> dict[str, Any]:
    shutil.rmtree(OUTPUT_ROOT, ignore_errors=True)
    result = subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--project-root",
            str(APPLICATION_ROOT),
            "--contract",
            str(CONTRACT),
            "--output",
            str(OUTPUT_ROOT),
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd="/tmp",
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    require(result.returncode == 0, f"F38 runner failed: {result.stderr or result.stdout}")
    require(not result.stderr, f"F38 runner wrote stderr: {result.stderr}")
    require(OUTPUT_REPORT.is_file(), "fresh F38 report missing")
    canonical_hash = sha256(CANONICAL_REPORT)
    fresh_hash = sha256(OUTPUT_REPORT)
    require(canonical_hash == EXPECTED_REPORT_SHA256, "embedded canonical report hash mismatch")
    require(fresh_hash == EXPECTED_REPORT_SHA256, "fresh report hash mismatch")
    require(OUTPUT_REPORT.read_bytes() == CANONICAL_REPORT.read_bytes(), "fresh report differs byte-for-byte")
    return {
        "fresh_report_sha256": fresh_hash,
        "canonical_report_sha256": canonical_hash,
        "byte_identical": True,
    }


def report_boundary_audit(contract: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    require(report.get("phase") == "F38", "unexpected report phase")
    require(
        report.get("status")
        == "steady_gas_path_accounting_executed_prescribed_duties_and_shaft_identity_closed_physical_validation_blocked",
        "unexpected report status",
    )
    require(report.get("contract_sha256") == sha256(CONTRACT), "report contract hash mismatch")
    technical = report.get("technical_gates")
    release = report.get("release_gates")
    require(isinstance(technical, dict) and set(technical) == EXPECTED_TECHNICAL_GATES, "technical gate set mismatch")
    require(all(value is True for value in technical.values()), "technical gate failed")
    require(isinstance(release, dict) and set(release) == EXPECTED_RELEASE_GATES, "release gate set mismatch")
    require(all(value is False for value in release.values()), "physical release gate opened")
    require(all(value is False for value in contract["release_gates"].values()), "contract release gate opened")

    runtime = report["runtime"]
    scope = report["model_scope"]
    require(runtime == {
        "deterministic": True,
        "external_api_used": False,
        "gpu_used": False,
        "implementation": "python_standard_library",
        "network_access_used": False,
    }, "runtime boundary mismatch")
    require(scope["steady_station_network_executed"] is True, "stationary network missing")
    for key in (
        "unsteady_one_dimensional_gas_dynamics_executed",
        "duct_geometry_or_wave_action_solved",
        "moving_valve_or_piston_cfd_executed",
        "physical_correlation_complete",
        "independent_model_cross_check",
    ):
        require(scope[key] is False, f"scope gate opened: {key}")

    target_authority = report["target_independence"]
    require(
        target_authority
        == {
            "requested_power_target_used_as_direct_f38_solver_input": False,
            "requested_power_target_has_indirect_sampling_ancestry": True,
            "inverse_sizing_seed_ancestry_present": True,
            "full_target_independence_proven": False,
            "scope": "absence_of_direct_target_input_in_f38_only",
        },
        "target ancestry boundary mismatch",
    )

    turbo = next(item for item in report["variants"] if item["configuration"] == "twin_turbo")
    turbo_system = turbo["turbo_system"]
    for key in (
        "compressor_map_digitized",
        "turbine_map_digitized",
        "map_interpolation_executed",
        "compressor_map_containment_validated",
        "turbine_map_containment_validated",
        "rotor_speed_calculated",
        "transient_rotor_dynamics_executed",
        "turbo_match_validated",
    ):
        require(turbo_system[key] is False, f"turbo proof gate opened: {key}")
    require(turbo_system["independent_model_cross_check"] is False, "independent model gate opened")
    require(turbo_system["chra_thermal_model_executed"] is False, "CHRA thermal model gate opened")
    require(
        turbo_system["turbo_mechanical_loss_destination_known"] is False,
        "turbo mechanical loss destination promoted",
    )
    require(turbo["target_comparison"]["target_power_proven"] is False, "target power gate opened")
    require(
        turbo["target_comparison"][
            "requested_power_target_used_as_direct_f38_solver_input"
        ]
        is False,
        "target became a direct F38 input",
    )
    require(
        turbo["target_comparison"]["full_target_independence_proven"] is False,
        "full target independence promoted",
    )
    require(
        turbo["target_comparison"]["target_unit"]
        == "mechanical_hp_not_metric_PS_or_ch",
        "target unit ambiguity",
    )
    return {
        "technical_gate_count": len(technical),
        "closed_release_gate_count": len(release),
        "steady_station_network_executed": True,
        "unsteady_1d_executed": False,
        "maps_digitized": False,
        "target_power_proven": False,
        "physical_correlation_complete": False,
        "independent_model_cross_check": False,
        "requested_power_target_has_indirect_sampling_ancestry": True,
        "full_target_independence_proven": False,
        "target_unit": "mechanical_hp_not_metric_PS_or_ch",
    }


def main() -> int:
    architecture = platform.machine().lower()
    require(platform.system() == "Linux", "Linux runtime required")
    require(architecture in {"x86_64", "amd64"}, f"linux/amd64 required, got {architecture}")
    identity = runtime_identity_and_filesystem_audit()
    dependency = standard_library_audit()
    contract = load_json(CONTRACT)
    source_hashes = source_hash_audit(contract)
    network = network_isolation_audit()
    comparison = execute_and_compare()
    report = load_json(CANONICAL_REPORT)
    boundary = report_boundary_audit(contract, report)
    shutil.rmtree(OUTPUT_ROOT, ignore_errors=True)
    print(
        json.dumps(
            {
                "status": "passed_embedded_f38_stationary_network_only",
                "platform": "linux/amd64-cpu",
                "offline": True,
                "non_root": True,
                "runtime_identity_and_filesystem_audit": identity,
                "standard_library_audit": dependency,
                "source_hash_audit": source_hashes,
                "network_isolation_evidence": network,
                "reproducibility": comparison,
                "proof_boundary": boundary,
            },
            allow_nan=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyError, OSError, RuntimeError, TypeError, ValueError) as error:
        print(f"F38 image smoke error: {error}", file=sys.stderr)
        raise SystemExit(2) from error
