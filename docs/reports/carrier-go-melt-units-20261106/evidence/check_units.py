#!/usr/bin/env python3
"""Check GO-MELT units on synthetic one-element domains; no carrier model."""
import argparse
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists(), "Preserve earlier receipts; choose a fresh output"
    source = args.source.resolve() / "go_melt" / "computeFunctions.py"
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    assert digest == "cf1889dfb41e11591e4245a9199262e66ae972e3a75e2c00baddd30f32851176"
    revision = subprocess.check_output(["git", "-C", str(args.source), "rev-parse", "HEAD"], text=True).strip()
    assert revision == "7dafdd8593711cf8ac6ccb18a1f475744610ea3d"
    os.environ["JAX_PLATFORMS"] = "cpu"
    os.environ["JAX_ENABLE_X64"] = "true"
    sys.path.insert(0, str(source.parent))
    import jax
    import jax.numpy as jnp
    import numpy as np
    import computeFunctions as kernel

    rows = []
    for width, height in [(1., 1.), (2., 3.)]:
        coords, connect = kernel.createMesh3D((0., width, 2), (0., height, 2), (0., 5., 2))
        level = {"node_coords": coords, "connect": connect, "elements": [1, 1, 1], "nodes": [2, 2, 2]}
        for kind, h_conv, emissivity in [("convection_only", 14.73e-6, 0.), ("radiation_only", 0., 0.6)]:
            properties = kernel.SetupProperties({"h_conv": h_conv, "T_amb": 300., "emissivity": emissivity, "evaporation_coefficient": 0.})
            flux = kernel.computeConvRadBC(level, jnp.full(8, 400.), 1, 8, properties, jnp.zeros(8))
            expected = (h_conv * (300. - 400.) + 5.67e-8 * emissivity * (300.**4 - 400.**4) * 1e-6) * width * height
            observed = float(flux.sum())
            np.testing.assert_allclose(observed, expected, rtol=1e-12, atol=1e-15)
            rows.append({"kind": kind, "area_mm2": width * height, "actual_W": observed, "expected_W": expected})
    properties = kernel.SetupProperties({"density": 4.42e-6, "heat_capacity_solid_a0": 500., "heat_capacity_solid_a1": 0., "thermal_conductivity_bulk_a0": 10., "thermal_conductivity_bulk_a1": 0.})
    _, _, conductivity, capacity = kernel.computeStateProperties(jnp.full(8, 300.), jnp.ones(8), properties, 8)
    np.testing.assert_allclose(conductivity, 0.010, rtol=1e-12, atol=0.)
    np.testing.assert_allclose(capacity, 0.00221, rtol=1e-12, atol=0.)
    report = {
        "status": "passed_actual_upstream_boundary_and_material_unit_controls",
        "source_commit": revision, "kernel_sha256": digest,
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "versions": {name: version(name) for name in ("jax", "jaxlib", "numpy", "scipy", "ml-dtypes", "pyevtk", "dill", "opt-einsum")},
        "backend": jax.default_backend(), "boundary_controls": rows,
        "material_control": {"synthetic_constant_cp_J_kg_K": 500., "synthetic_constant_k_W_m_K": 10., "density_kg_mm3": 4.42e-6, "actual_k_W_mm_K": float(conductivity[0]), "actual_rhocp_J_mm3_K": float(capacity[0])},
        "carrier_thermal_laws_qualified": False, "multilevel_scan_executed": False, "cuda_executed": False,
    }
    with args.output.open("x") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
