#!/usr/bin/env python3
"""Smoke fail-closed de l'image CPU F34b, sans lancer le DOE canonique."""

from __future__ import annotations

import hashlib
from importlib import metadata
import json
import math
import os
from pathlib import Path
import platform
import pwd
import re
import socket
import subprocess
import sys
from typing import Any

import cantera as ct


APPLICATION_ROOT = Path("/opt/air-oil-cycle-f34b")
REQUIREMENTS = APPLICATION_ROOT / "requirements.txt"
SOLVER = APPLICATION_ROOT / "scripts/run_917_air_oil_cycle_f34b.py"
ARCHITECTURE_CONTRACT = (
    APPLICATION_ROOT
    / "twins/reference-917-engine/air-oil-core-controls-f34a.json"
)
DOE_CONTRACT = (
    APPLICATION_ROOT / "twins/reference-917-engine/doe-surrogate-f34.json"
)
SEED_BUNDLE = (
    APPLICATION_ROOT
    / "twins/reference-917-engine/evidence/f34/air-oil-forward-seeds-f34b.json"
)
DOE_MANIFEST = (
    APPLICATION_ROOT
    / "twins/reference-917-engine/evidence/f34/doe-case-manifest.json"
)
RUNTIME_UID = 9133
RUNTIME_GID = 9133
ALLOWED_SOLVER_MODES = ("preflight",)
EXPECTED_APPLICATION_FILES = {
    "requirements.txt",
    "smoke.py",
    "scripts/run_917_air_oil_cycle_f34b.py",
    "twins/reference-917-engine/air-oil-core-controls-f34a.json",
    "twins/reference-917-engine/doe-surrogate-f34.json",
    "twins/reference-917-engine/evidence/f34/air-oil-forward-seeds-f34b.json",
    "twins/reference-917-engine/evidence/f34/doe-case-manifest.json",
}
EXPECTED_PINS = {
    "cantera": "3.2.0",
    "numpy": "2.5.2",
    "ruamel-yaml": "0.19.1",
    "typing-extensions": "4.16.0",
}
PHYSICAL_RELEASE_GATES = {
    "target_definition_complete": False,
    "target_power_proven": False,
    "mass_and_energy_balance_validated": False,
    "thermodynamic_cycle_validated": False,
    "air_cooling_validated": False,
    "oil_system_validated": False,
    "turbo_match_validated": False,
    "combustion_and_knock_validated": False,
    "controls_and_overspeed_protection_validated": False,
    "structural_and_fatigue_validated": False,
    "doe_execution_complete": False,
    "physical_correlation_complete": False,
    "test_bench_start_authorized": False,
    "porsche_993_packaging_validated": False,
    "porsche_993_vehicle_installation_authorized": False,
    "metal_print_authorized": False,
    "manufacturing_authorized": False,
}
F34A_TECHNICAL_GATE_IDS = {
    "auxiliary_liquid_isolation_verified",
    "boost_failsafe_validated",
    "communications_architecture_validated",
    "control_maps_available",
    "controls_hardware_selected",
    "core_geometry_defined",
    "dry_sump_oil_network_solved",
    "forced_air_network_solved",
    "hardwired_interlocks_verified",
    "knock_control_calibrated",
    "lambda_closed_loop_calibrated",
    "safety_thresholds_validated",
    "sensor_chains_calibrated",
    "vvt_vvl_hardware_selected",
    "vvt_vvl_maps_available",
}
F34A_RELEASE_GATE_IDS = {
    "air_cooling_validated",
    "architecture_physically_validated",
    "auxiliary_liquid_system_validated",
    "boost_control_validated",
    "communications_validated",
    "controls_and_logging_validated",
    "engine_bench_start_authorized",
    "knock_control_validated",
    "lambda_control_validated",
    "manufacturing_authorized",
    "metal_print_authorized",
    "oil_system_validated",
    "porsche_993_fitment_validated",
    "ruf_compatibility_validated",
    "target_power_proven",
    "vehicle_installation_authorized",
    "vvt_vvl_validated",
}
F34_RELEASE_GATE_IDS = {
    "boost_failsafe_validated",
    "can_fd_architecture_validated",
    "cfd_validated",
    "cht_validated",
    "closed_loop_controls_validated",
    "cooling_system_validated",
    "crank_cam_sync_validated",
    "dataset_ready",
    "doe_execution_complete",
    "ecu_hardware_selected",
    "ecu_io_complete",
    "hil_complete",
    "hydraulic_network_validated",
    "ignition_validated",
    "injector_characterization_validated",
    "knock_control_validated",
    "lambda_control_validated",
    "manufacturing_authorized",
    "metal_print_authorized",
    "one_dimensional_model_validated",
    "ood_policy_calibrated",
    "physical_correlation_complete",
    "porsche_993_vehicle_installation_authorized",
    "sil_complete",
    "surrogate_trained",
    "surrogate_validated_against_0d_solver",
    "target_power_proven",
    "test_bench_start_authorized",
    "training_authorized",
    "vvt_vvl_validated",
}
F34B_SEED_PHYSICAL_GATE_IDS = {
    "air_cooling_physically_validated",
    "auxiliary_liquid_isolation_physically_validated",
    "controls_physically_validated",
    "engine_bench_start_authorized",
    "manufacturing_authorized",
    "metal_print_authorized",
    "oil_system_physically_validated",
    "physical_correlation_complete",
    "target_power_proven",
    "vehicle_installation_authorized",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def require_closed_gate_set(value: Any, expected: set[str], label: str) -> None:
    require(isinstance(value, dict), f"{label} must be an object")
    require(set(value) == expected, f"{label} key set mismatch")
    require(all(item is False for item in value.values()), f"{label} gate opened")


def canonical_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    def reject_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON constant rejected: {value}")

    def reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in pairs:
            require(key not in result, f"duplicate JSON key rejected: {key}")
            result[key] = item
        return result

    value = json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=reject_constant,
        object_pairs_hook=reject_duplicate_pairs,
    )
    require(isinstance(value, dict), f"JSON root must be an object: {path}")
    return value


def dependency_audit() -> dict[str, Any]:
    source = REQUIREMENTS.read_text(encoding="ascii")
    entries = re.findall(
        r"^([A-Za-z0-9_.-]+)==([^ \\\n]+) \\\n\s+--hash=sha256:([0-9a-f]{64})$",
        source,
        re.MULTILINE,
    )
    pins = {canonical_name(name): version for name, version, _ in entries}
    hashes = [digest for _, _, digest in entries]
    require(pins == EXPECTED_PINS, f"unexpected dependency pins: {pins}")
    require(len(entries) == 4, "the F34b lock must contain exactly four wheels")
    require(len(set(hashes)) == 4, "the F34b wheel hashes must be unique")

    installed = {
        canonical_name(distribution.metadata["Name"]): distribution.version
        for distribution in metadata.distributions()
        if distribution.metadata.get("Name")
    }
    mismatches = {
        name: {"expected": version, "actual": installed.get(name)}
        for name, version in pins.items()
        if installed.get(name) != version
    }
    require(not mismatches, f"installed wheel mismatch: {mismatches}")
    unexpected = sorted(set(installed) - set(pins) - {"pip"})
    require(not unexpected, f"unexpected Python distributions: {unexpected}")
    require(installed.get("pip") == "25.0.1", "unexpected pip in Python base")
    require(ct.__version__ == "3.2.0", "unexpected Cantera version")
    return {
        "policy": "four_exact_hashed_linux_amd64_wheels_plus_pinned_base_pip",
        "requirements_sha256": sha256(REQUIREMENTS),
        "pin_count": len(pins),
        "hash_count": len(hashes),
        "unexpected_distributions": unexpected,
        "versions": {**pins, "pip": installed["pip"]},
    }


def runtime_identity_and_filesystem_audit() -> dict[str, Any]:
    account = pwd.getpwuid(RUNTIME_UID)
    require(account.pw_name == "air-oil-cycle", "unexpected runtime account")
    require(account.pw_gid == RUNTIME_GID, "unexpected runtime group")
    require(account.pw_dir == "/tmp", "runtime passwd home must be /tmp")
    require(os.getuid() == RUNTIME_UID, "smoke must run as the dedicated user")
    require(os.getgid() == RUNTIME_GID, "smoke must run with the dedicated group")
    require(os.environ.get("HOME") == "/tmp", "HOME must be /tmp")
    require(
        os.environ.get("XDG_CACHE_HOME") == "/tmp/air-oil-cycle-f34b-cache",
        "XDG_CACHE_HOME must be isolated under /tmp",
    )

    application_write_blocked = False
    try:
        (APPLICATION_ROOT / ".write-probe").write_text("forbidden", encoding="ascii")
    except OSError:
        application_write_blocked = True
    require(application_write_blocked, "application payload must not be writable")

    tmp_probe = Path("/tmp/air-oil-cycle-f34b-write-probe")
    tmp_probe.write_text("ok", encoding="ascii")
    require(tmp_probe.read_text(encoding="ascii") == "ok", "/tmp write probe failed")
    tmp_probe.unlink()
    return {
        "account": account.pw_name,
        "uid": os.getuid(),
        "gid": os.getgid(),
        "passwd_home": account.pw_dir,
        "home_environment": os.environ["HOME"],
        "xdg_cache_home": os.environ["XDG_CACHE_HOME"],
        "application_payload_write_blocked": application_write_blocked,
        "tmp_write_probe": True,
    }


def network_isolation_evidence() -> dict[str, Any]:
    routed_interfaces: list[str] = []
    route_path = Path("/proc/net/route")
    if route_path.is_file():
        lines = route_path.read_text(encoding="ascii").splitlines()[1:]
        routed_interfaces = sorted(
            {
                fields[0]
                for line in lines
                if len(fields := line.split()) >= 4 and fields[1] == "00000000"
            }
        )
    require(not routed_interfaces, f"external default route present: {routed_interfaces}")
    return {
        "verified": True,
        "external_routed_interfaces": routed_interfaces,
        "hostname_recorded": False,
        "socket_module_available": socket is not None,
    }


def bundled_content_audit() -> dict[str, Any]:
    files = {
        path.relative_to(APPLICATION_ROOT).as_posix()
        for path in APPLICATION_ROOT.rglob("*")
        if path.is_file()
    }
    require(files == EXPECTED_APPLICATION_FILES, f"unexpected application files: {files}")
    forbidden_suffixes = {
        ".obj",
        ".stl",
        ".3mf",
        ".step",
        ".stp",
        ".usd",
        ".usda",
        ".usdc",
        ".pt",
        ".pth",
        ".onnx",
        ".safetensors",
        ".pem",
        ".key",
    }
    forbidden_assets = sorted(
        relative
        for relative in files
        if Path(relative).suffix.lower() in forbidden_suffixes
    )
    secret_named = sorted(
        relative
        for relative in files
        if any(
            token in Path(relative).name.lower()
            for token in ("secret", "token", "password", "private", "credential")
        )
    )
    require(not forbidden_assets, f"forbidden bundled assets: {forbidden_assets}")
    require(not secret_named, f"secret-named bundled files: {secret_named}")
    solver_source = SOLVER.read_text(encoding="utf-8").lower()
    forbidden_network_tokens = sorted(
        token
        for token in (
            "import requests",
            "from requests",
            "urllib.request",
            "import socket",
            "from socket",
            "http.client",
            "subprocess.",
            "os.system",
        )
        if token in solver_source
    )
    require(
        not forbidden_network_tokens,
        f"forbidden network/process API in solver: {forbidden_network_tokens}",
    )
    return {
        "policy": "seven_exact_allow_listed_inputs_with_name_extension_and_solver_api_audits",
        "file_count": len(files),
        "files_sha256": {
            relative: sha256(APPLICATION_ROOT / relative)
            for relative in sorted(files)
        },
        "forbidden_asset_files": forbidden_assets,
        "secret_named_files": secret_named,
        "contains_scan_or_print_geometry": False,
        "contains_model_weights": False,
        "proprietary_manual_file_in_allow_list": False,
        "semantic_content_license_audit_performed": False,
        "solver_forbidden_network_or_process_api_tokens": forbidden_network_tokens,
    }


def embedded_authority_audit() -> dict[str, Any]:
    architecture = read_json(ARCHITECTURE_CONTRACT)
    doe = read_json(DOE_CONTRACT)
    seed_bundle = read_json(SEED_BUNDLE)
    manifest = read_json(DOE_MANIFEST)

    decision = architecture.get("decision", {})
    require(
        decision.get("id") == "F34A-AIR-OIL-CORE-2026-CONTROLS",
        "unexpected F34a architecture decision",
    )
    require(
        decision.get("selected_core_thermal_architecture")
        == "strict_forced_air_and_dry_sump_oil_only",
        "F34a is not the strict air/oil architecture",
    )
    core = architecture.get("engine_core_boundary", {})
    require(core.get("core_liquid_coolant_loop_present") is False, "core liquid loop present")
    require(
        core.get("core_to_auxiliary_liquid_cross_connection_allowed") is False,
        "core-to-auxiliary liquid cross-connection allowed",
    )
    require_closed_gate_set(
        architecture.get("technical_gates"),
        F34A_TECHNICAL_GATE_IDS,
        "F34a technical gates",
    )
    require_closed_gate_set(
        architecture.get("release_gates"),
        F34A_RELEASE_GATE_IDS,
        "F34a release gates",
    )

    require(
        doe.get("status") == "doe_contract_and_case_plan_only_no_solver_cases_executed",
        "unexpected F34 DOE contract status",
    )
    require(doe.get("authority_boundary", {}).get("doe_executed") is False, "DOE marked executed")
    require(
        doe.get("runtime", {}).get("future_solver", {}).get("execution_authorized") is False,
        "F34 DOE execution unexpectedly authorized",
    )
    require_closed_gate_set(
        doe.get("release_gates"), F34_RELEASE_GATE_IDS, "F34 DOE release gates"
    )

    parents = {parent.get("path"): parent for parent in doe.get("parents", [])}
    architecture_relative = "twins/reference-917-engine/air-oil-core-controls-f34a.json"
    require(
        parents.get(architecture_relative, {}).get("sha256") == sha256(ARCHITECTURE_CONTRACT),
        "F34a parent hash mismatch",
    )

    counts = manifest.get("case_counts", {})
    ledger = manifest.get("execution_ledger", {})
    cases = manifest.get("cases", [])
    require(
        manifest.get("contract_file_sha256") == sha256(DOE_CONTRACT),
        "DOE contract hash mismatch",
    )
    require(
        manifest.get("status")
        == "deterministic_case_manifest_generated_zero_solver_cases_executed",
        "unexpected DOE manifest status",
    )
    require(counts.get("planned") == 2570, "unexpected canonical DOE plan size")
    require(
        counts.get("executed")
        == counts.get("accepted")
        == counts.get("rejected")
        == 0,
        "canonical DOE result count is non-zero",
    )
    require(ledger.get("planned_not_executed") == 2570, "unexpected unexecuted ledger count")
    require(
        ledger.get("executed")
        == ledger.get("accepted")
        == ledger.get("rejected")
        == 0,
        "canonical DOE ledger contains results",
    )
    require(len(cases) == 2570, "canonical DOE case list length mismatch")
    require(
        all(
            case.get("execution_status") == "planned_not_executed"
            and case.get("training_eligible") is False
            for case in cases
        ),
        "canonical DOE case was executed or made training-eligible",
    )
    require_closed_gate_set(
        manifest.get("release_gates"),
        F34_RELEASE_GATE_IDS,
        "F34 DOE manifest release gates",
    )
    require(
        seed_bundle.get("authority_boundary", {}).get(
            "engine_core_liquid_coolant_present"
        )
        is False,
        "seed bundle is not air/oil-only",
    )
    require(
        seed_bundle.get("canonical_doe_cases_executed") == 0,
        "seed bundle records canonical DOE execution",
    )
    require(
        seed_bundle.get("execution_ledger", {}).get("seed_count") == 2
        and seed_bundle.get("execution_ledger", {}).get("solver_case_count") == 0,
        "seed bundle execution ledger is not the two-seed zero-solver boundary",
    )
    require_closed_gate_set(
        seed_bundle.get("physical_gates"),
        F34B_SEED_PHYSICAL_GATE_IDS,
        "seed bundle physical gates",
    )
    require_closed_gate_set(
        seed_bundle.get("release_gates"),
        F34_RELEASE_GATE_IDS,
        "seed bundle release gates",
    )

    seed_parents = {
        parent.get("path"): parent for parent in seed_bundle.get("parents", [])
    }
    require(
        seed_parents.get(architecture_relative, {}).get("sha256")
        == sha256(ARCHITECTURE_CONTRACT),
        "seed bundle F34a parent hash mismatch",
    )
    require(
        seed_parents.get("twins/reference-917-engine/doe-surrogate-f34.json", {}).get(
            "sha256"
        )
        == sha256(DOE_CONTRACT),
        "seed bundle DOE parent hash mismatch",
    )
    require(
        seed_parents.get(
            "twins/reference-917-engine/evidence/f34/doe-case-manifest.json", {}
        ).get("sha256")
        == sha256(DOE_MANIFEST),
        "seed bundle manifest parent hash mismatch",
    )
    return {
        "architecture_decision_id": decision["id"],
        "engine_core": "forced_air_and_dry_sump_oil",
        "engine_core_liquid_coolant_present": False,
        "canonical_doe_planned_cases": counts["planned"],
        "canonical_doe_executed_cases": counts["executed"],
        "canonical_doe_training_eligible_cases": 0,
        "manifest_contract_file_sha256_verified": True,
        "architecture_parent_sha256_verified": True,
        "seed_bundle_embedded_parent_sha256s_verified": True,
        "air_oil_seed_bundle_sha256": sha256(SEED_BUNDLE),
        "all_embedded_release_gates_closed": True,
    }


def execute_solver_mode(mode: str) -> dict[str, Any]:
    require(mode in ALLOWED_SOLVER_MODES, f"solver mode not allowed by smoke: {mode}")
    output = Path(f"/tmp/air-oil-cycle-f34b-{mode}.json")
    command = [
        sys.executable,
        str(SOLVER),
        mode,
        "--doe-contract",
        str(DOE_CONTRACT),
        "--architecture-contract",
        str(ARCHITECTURE_CONTRACT),
        "--seed-bundle",
        str(SEED_BUNDLE),
        "--output",
        str(output),
    ]
    completed = subprocess.run(
        command,
        cwd=APPLICATION_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=90,
    )
    require(completed.returncode == 0, f"{mode} failed: {completed.stderr.strip()}")
    require(not completed.stderr, f"{mode} wrote stderr: {completed.stderr.strip()}")
    require(not completed.stdout, f"{mode} wrote stdout while --output was set")
    require(output.is_file(), f"{mode} did not write its JSON report")
    report = read_json(output)
    output.unlink()
    require(report.get("canonical_doe_cases_executed") == 0, f"{mode} executed a canonical DOE case")
    require(report.get("predicted_engine_power") is False, f"{mode} claimed engine power")
    require(report.get("validated_1600_hp") is False, f"{mode} claimed 1600 hp validation")
    require(report.get("physical_correlation") is False, f"{mode} claimed physical correlation")
    return report


def generic_cantera_fixture() -> dict[str, Any]:
    """Exercise pinned Cantera without any engine seed, geometry or calibration."""

    require(ct.__version__ == "3.2.0", "generic fixture requires Cantera 3.2.0")
    equilibrium_gas = ct.Solution("gri30.yaml")
    equilibrium_gas.TP = 300.0, ct.one_atm
    equilibrium_gas.set_equivalence_ratio(1.0, "CH4:1", "O2:1,N2:3.76")
    initial_enthalpy = equilibrium_gas.enthalpy_mass
    equilibrium_gas.equilibrate("HP")
    equilibrium_temperature = equilibrium_gas.T
    require(
        2100.0 < equilibrium_temperature < 2400.0,
        "unexpected generic methane equilibrium temperature",
    )
    require(
        math.isclose(equilibrium_gas.P, ct.one_atm, rel_tol=1.0e-9),
        "generic HP equilibrium changed pressure",
    )
    require(
        math.isclose(
            equilibrium_gas.enthalpy_mass,
            initial_enthalpy,
            rel_tol=1.0e-9,
        ),
        "generic HP equilibrium changed enthalpy",
    )

    reactor_gas = ct.Solution("gri30.yaml")
    reactor_gas.TPX = 1000.0, ct.one_atm, "H2:2,O2:1,N2:3.76"
    reactor = ct.IdealGasReactor(reactor_gas, energy="on", clone=True)
    network = ct.ReactorNet([reactor])
    initial_temperature = reactor.T
    final_time_s = 0.001
    network.advance(final_time_s)
    require(network.time == final_time_s, "generic reactor did not reach final time")
    require(
        reactor.T > initial_temperature + 100.0,
        "generic hydrogen reactor did not ignite",
    )
    require(network.solver_stats["steps"] > 0, "generic reactor took no step")
    return {
        "fixture": "generic_methane_equilibrium_and_hydrogen_constant_volume_reactor",
        "uses_engine_forward_input": False,
        "uses_engine_geometry": False,
        "uses_engine_calibration": False,
        "uses_porsche_data": False,
        "canonical_doe_case": False,
        "equilibrium_temperature_k": round(equilibrium_temperature, 9),
        "reactor_initial_temperature_k": initial_temperature,
        "reactor_final_temperature_k": round(reactor.T, 9),
        "reactor_final_time_s": network.time,
        "reactor_steps": network.solver_stats["steps"],
    }


def main() -> int:
    authority = embedded_authority_audit()
    preflight = execute_solver_mode("preflight")
    cantera_fixture = generic_cantera_fixture()
    report = {
        "schema_version": "1.0.0",
        "status": "passed_embedded_f34b_preflight_and_generic_cantera_fixture_only",
        "platform": "linux/amd64-cpu",
        "offline": True,
        "non_root": os.getuid() != 0,
        "gpu_required": False,
        "python": platform.python_version(),
        "cantera": ct.__version__,
        "dependency_audit": dependency_audit(),
        "runtime_identity_and_filesystem_audit": runtime_identity_and_filesystem_audit(),
        "network_isolation_evidence": network_isolation_evidence(),
        "bundled_content_audit": bundled_content_audit(),
        "embedded_authority_audit": authority,
        "solver_preflight": {
            "allowed_modes": list(ALLOWED_SOLVER_MODES),
            "preflight": preflight,
        },
        "generic_cantera_fixture": cantera_fixture,
        "proof_boundary": {
            "embedded_model_and_contracts_audited": True,
            "preflight_executed": True,
            "generic_thermochemistry_fixture_executed": True,
            "engine_forward_solver_executed": False,
            "solver_synthetic_smoke_executed": False,
            "canonical_doe_cases_executed": 0,
            "canonical_doe_solver_campaign_executed": False,
            "dataset_generated": False,
            "surrogate_trained": False,
            "predicted_engine_power": False,
            "validated_1600_hp": False,
            "physical_correlation": False,
            "physicsnemo_executed": False,
            "omniverse_executed": False,
            "remote_compute_used": False,
        },
        "physical_release_gates": PHYSICAL_RELEASE_GATES,
    }
    require(report["non_root"], "container must not run as root")
    require(
        all(value is False for value in PHYSICAL_RELEASE_GATES.values()),
        "physical release gate opened",
    )
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
