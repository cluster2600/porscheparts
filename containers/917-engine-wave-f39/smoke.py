#!/usr/bin/env python3
"""Smoke CPU amd64 F39 : dependances et tube a choc Aeolus1D uniquement."""

from __future__ import annotations

import json
from importlib.metadata import version
import os
from pathlib import Path
import platform
import sys

import h5py
import numba
import numpy as np
import scipy

from aeolus1d.bench.sod import run_sod


EXPECTED_VERSIONS = {
    "aeolus1d": "0.3.3",
    "h5py": "3.14.0",
    "llvmlite": "0.49.0",
    "numba": "0.67.0",
    "numpy": "2.2.6",
    "scipy": "1.16.3",
}
RUNTIME_UID = 9139
RUNTIME_GID = 9139
HDF5_PROBE = Path("/tmp/917-engine-wave-f39-smoke.h5")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


@numba.njit(cache=False)
def numba_sum_of_squares(values: np.ndarray) -> float:
    total = 0.0
    for value in values:
        total += value * value
    return total


def dependency_audit() -> dict[str, str]:
    installed = {name: version(name) for name in EXPECTED_VERSIONS}
    require(installed == EXPECTED_VERSIONS, f"unexpected dependency versions: {installed}")
    require(np.__version__ == EXPECTED_VERSIONS["numpy"], "NumPy import mismatch")
    require(numba.__version__ == EXPECTED_VERSIONS["numba"], "Numba import mismatch")
    require(scipy.__version__ == EXPECTED_VERSIONS["scipy"], "SciPy import mismatch")
    require(h5py.__version__ == EXPECTED_VERSIONS["h5py"], "h5py import mismatch")
    return installed


def runtime_audit() -> dict[str, object]:
    require(platform.system() == "Linux", "F39 image must run on Linux")
    require(platform.machine() == "x86_64", "F39 image must run on amd64")
    require(sys.version_info[:2] == (3, 12), "F39 image requires Python 3.12")
    require(os.getuid() == RUNTIME_UID, "smoke must run as the dedicated UID")
    require(os.getgid() == RUNTIME_GID, "smoke must run as the dedicated GID")
    require(os.environ.get("HOME") == "/tmp", "HOME must be /tmp")
    return {
        "system": platform.system(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "uid": os.getuid(),
        "gid": os.getgid(),
        "gpu_required": False,
        "external_api_required": False,
    }


def native_runtime_smoke() -> dict[str, object]:
    values = np.arange(32, dtype=np.float64)
    sum_of_squares = float(numba_sum_of_squares(values))
    require(sum_of_squares == 10416.0, "Numba JIT checksum mismatch")

    HDF5_PROBE.unlink(missing_ok=True)
    try:
        with h5py.File(HDF5_PROBE, "w") as handle:
            handle.create_dataset("values", data=values)
        with h5py.File(HDF5_PROBE, "r") as handle:
            round_trip = np.asarray(handle["values"])
        require(np.array_equal(round_trip, values), "HDF5 round-trip mismatch")
    finally:
        HDF5_PROBE.unlink(missing_ok=True)

    return {
        "numba_jit_executed": True,
        "numba_sum_of_squares": sum_of_squares,
        "hdf5_round_trip_executed": True,
    }


def sod_benchmark_smoke() -> dict[str, float | int | bool]:
    result = run_sod(N=64, cfl=0.4)
    rho = np.asarray(result["rho"])
    pressure = np.asarray(result["p"])
    velocity = np.asarray(result["u"])

    require(rho.size == 64, "unexpected Sod density field size")
    require(pressure.size == 64, "unexpected Sod pressure field size")
    require(velocity.size == 64, "unexpected Sod velocity field size")
    require(np.all(np.isfinite(rho)), "non-finite Sod density")
    require(np.all(np.isfinite(pressure)), "non-finite Sod pressure")
    require(np.all(np.isfinite(velocity)), "non-finite Sod velocity")
    require(float(np.min(rho)) > 0.0, "non-positive Sod density")
    require(float(np.min(pressure)) > 0.0, "non-positive Sod pressure")
    require(abs(float(result["t"]) - 0.2) < 1.0e-12, "unexpected Sod end time")
    require(float(result["L1_rho"]) < 0.25, "Sod density error gate failed")
    require(float(result["L1_p"]) < 0.25, "Sod pressure error gate failed")
    require(float(result["L1_u_abs"]) < 0.25, "Sod velocity error gate failed")

    return {
        "cells": int(rho.size),
        "time_s": float(result["t"]),
        "l1_density_relative": float(result["L1_rho"]),
        "l1_pressure_relative": float(result["L1_p"]),
        "l1_velocity_absolute": float(result["L1_u_abs"]),
        "finite_positive_state_verified": True,
    }


def main() -> int:
    report = {
        "schema_version": "1.0.0",
        "phase": "F39",
        "status": "runtime_smoke_passed_engine_validation_blocked",
        "runtime": runtime_audit(),
        "dependencies": dependency_audit(),
        "native_runtime": native_runtime_smoke(),
        "benchmark": sod_benchmark_smoke(),
        "claim_scope": {
            "generic_sod_benchmark_executed": True,
            "flat_12_model_executed": False,
            "turbo_maps_validated": False,
            "engine_model_physically_correlated": False,
            "target_1600_mechanical_hp_proven": False,
            "engine_start_authorized": False,
            "manufacturing_authorized": False,
        },
    }
    json.dump(report, sys.stdout, indent=2, sort_keys=True, allow_nan=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
