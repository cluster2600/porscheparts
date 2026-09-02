#!/usr/bin/env python3
"""Smoke hors ligne de l'image F33, sans geometrie ni donnees Porsche."""

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
from typing import Any

import cantera as ct


APPLICATION_ROOT = Path("/opt/engine-cycle-f33")
REQUIREMENTS = APPLICATION_ROOT / "requirements.txt"
RUNTIME_UID = 9133
RUNTIME_GID = 9133
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
    "turbo_match_validated": False,
    "combustion_and_knock_validated": False,
    "cooling_system_validated": False,
    "oil_system_validated": False,
    "structural_and_fatigue_validated": False,
    "controls_and_overspeed_protection_validated": False,
    "test_bench_start_authorized": False,
    "porsche_993_packaging_validated": False,
    "porsche_993_vehicle_installation_authorized": False,
    "held_out_physical_correlation_complete": False,
    "metal_print_authorized": False,
    "manufacturing_authorized": False,
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def canonical_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
    require(len(entries) == 4, "the F33 lock must contain exactly four wheels")
    require(len(set(hashes)) == 4, "the F33 wheel hashes must be unique")

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
    return {
        "policy": "four_exact_hashed_linux_amd64_wheels_plus_pinned_base_pip",
        "requirements_sha256": sha256(REQUIREMENTS),
        "pin_count": len(pins),
        "hash_count": len(hashes),
        "unexpected_distributions": unexpected,
        "versions": {**pins, "pip": installed["pip"]},
    }


def runtime_identity_audit() -> dict[str, Any]:
    account = pwd.getpwuid(RUNTIME_UID)
    require(account.pw_name == "engine-cycle", "unexpected runtime account")
    require(account.pw_gid == RUNTIME_GID, "unexpected runtime group")
    require(account.pw_dir == "/tmp", "runtime passwd home must be /tmp")
    require(os.getuid() == RUNTIME_UID, "smoke must run as the dedicated user")
    require(os.getgid() == RUNTIME_GID, "smoke must run with the dedicated group")
    require(os.environ.get("HOME") == "/tmp", "HOME must be /tmp")
    require(
        os.environ.get("XDG_CACHE_HOME") == "/tmp/engine-cycle-f33-cache",
        "XDG_CACHE_HOME must be isolated under /tmp",
    )
    return {
        "account": account.pw_name,
        "uid": os.getuid(),
        "gid": os.getgid(),
        "passwd_home": account.pw_dir,
        "home_environment": os.environ["HOME"],
        "xdg_cache_home": os.environ["XDG_CACHE_HOME"],
    }


def network_isolation_evidence() -> dict[str, Any]:
    routed_interfaces: list[str] = []
    route_path = Path("/proc/net/route")
    if route_path.is_file():
        lines = route_path.read_text(encoding="ascii").splitlines()[1:]
        routed_interfaces = sorted(
            {fields[0] for line in lines if len(fields := line.split()) >= 4 and fields[1] == "00000000"}
        )
    require(not routed_interfaces, f"external default route present: {routed_interfaces}")
    return {
        "verified": True,
        "external_routed_interfaces": routed_interfaces,
        "hostname_recorded": False,
        "socket_module_available": socket is not None,
    }


def synthetic_thermochemistry_fixture() -> dict[str, Any]:
    if ct.__version__ != "3.2.0":
        raise RuntimeError(f"unexpected Cantera version: {ct.__version__}")
    gas = ct.Solution("gri30.yaml")
    gas.TP = 300.0, ct.one_atm
    gas.set_equivalence_ratio(1.0, "CH4:1", "O2:1,N2:3.76")
    initial_enthalpy = gas.enthalpy_mass
    gas.equilibrate("HP")
    equilibrium_temperature = gas.T
    require(math.isfinite(equilibrium_temperature), "non-finite equilibrium temperature")
    require(2100.0 < equilibrium_temperature < 2400.0, "unexpected equilibrium temperature")
    require(math.isclose(gas.P, ct.one_atm, rel_tol=1e-9), "HP equilibrium changed pressure")
    require(math.isclose(gas.enthalpy_mass, initial_enthalpy, rel_tol=1e-9), "HP equilibrium changed enthalpy")
    require(math.isclose(float(gas.Y.sum()), 1.0, rel_tol=0.0, abs_tol=1e-12), "mass fractions do not close")

    ignition_gas = ct.Solution("gri30.yaml")
    ignition_gas.TPX = 1000.0, ct.one_atm, "H2:2,O2:1,N2:3.76"
    reactor = ct.IdealGasReactor(ignition_gas, energy="on", clone=True)
    network = ct.ReactorNet([reactor])
    initial_temperature = reactor.T
    final_time_s = 0.001
    network.advance(final_time_s)
    require(math.isfinite(reactor.T), "non-finite reactor temperature")
    require(network.time == final_time_s, "reactor network did not reach requested time")
    require(reactor.T > initial_temperature + 100.0, "synthetic H2 reactor did not ignite")
    require(network.solver_stats["steps"] > 0, "reactor network executed no integration step")

    return {
        "fixture": "generic_methane_equilibrium_and_hydrogen_constant_volume_reactor",
        "uses_engine_geometry": False,
        "uses_engine_calibration": False,
        "uses_porsche_data": False,
        "equilibrium_temperature_k": round(equilibrium_temperature, 9),
        "reactor_initial_temperature_k": initial_temperature,
        "reactor_final_temperature_k": round(reactor.T, 9),
        "reactor_final_time_s": network.time,
        "reactor_steps": network.solver_stats["steps"],
    }


def main() -> int:
    report = {
        "schema_version": "1.0.0",
        "status": "passed_synthetic_thermochemistry_fixture_only",
        "platform": "linux/amd64-cpu",
        "offline": True,
        "non_root": os.getuid() != 0,
        "gpu_required": False,
        "python": platform.python_version(),
        "cantera": ct.__version__,
        "dependency_audit": dependency_audit(),
        "runtime_identity": runtime_identity_audit(),
        "network_isolation_evidence": network_isolation_evidence(),
        "synthetic_fixture": synthetic_thermochemistry_fixture(),
        "proof_boundary": {
            "synthetic_fixture": True,
            "engine_cycle_solver_executed": False,
            "engine_cycle_model": False,
            "one_dimensional_gas_dynamics": False,
            "predicted_engine_power": False,
            "validated_1600_hp": False,
            "physical_correlation": False,
            "physicsnemo_executed": False,
            "omniverse_executed": False,
        },
        "physical_release_gates": PHYSICAL_RELEASE_GATES,
    }
    require(report["non_root"], "container must not run as root")
    require(all(value is False for value in PHYSICAL_RELEASE_GATES.values()), "physical gate opened")
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
