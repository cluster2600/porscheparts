"""GO-MELT CPU thermal-kernel witness, not a multilevel LPBF validation."""

import argparse
import hashlib
import json
import os
import sys
from importlib.metadata import version
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve() / "go_melt" / "computeFunctions.py"
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != "cf1889dfb41e11591e4245a9199262e66ae972e3a75e2c00baddd30f32851176":
        raise ValueError("Unreviewed GO-MELT kernel revision")
    args.output.mkdir(parents=True, exist_ok=False)
    os.environ["JAX_PLATFORMS"] = "cpu"
    os.environ["JAX_ENABLE_X64"] = "true"
    sys.path.insert(0, str(source.parent))
    import jax
    import jax.numpy as jnp
    import numpy as np
    import computeFunctions as kernel

    coords, connectivity = kernel.createMesh3D((0., 1., 2), (0., 1., 2), (0., 1., 2))
    level = {"node_coords": coords, "connect": connectivity,
             "elements": [1, 1, 1], "nodes": [2, 2, 2]}
    shapes, gradients, weights = kernel.computeQuad3dFemShapeFunctions_jax(kernel.getSampleCoords(level))
    np.testing.assert_allclose(shapes.sum(axis=1), 1., atol=1e-12)
    np.testing.assert_allclose(gradients.sum(axis=1), 0., atol=1e-12)
    np.testing.assert_allclose(weights.sum(), 1., atol=1e-12)
    zero = jnp.zeros(8)
    temperature = jnp.full(8, 300.)
    conductivity = jnp.ones(8)
    heat_capacity = jnp.full(8, 2.)
    equilibrium = kernel.solveMatrixFreeFE(level, 8, 1, conductivity, heat_capacity, 0.01, temperature, zero, zero)
    np.testing.assert_allclose(equilibrium, 300., atol=1e-10, rtol=0.)
    # Uniform volumetric source q=4, unit cube: each nodal load is q*V/8.
    heated = kernel.solveMatrixFreeFE(level, 8, 1, conductivity, heat_capacity, 0.01, temperature, jnp.full(8, 0.5), zero)
    np.testing.assert_allclose(heated, 300.02, atol=1e-10, rtol=0.)
    initial = jnp.array([301., 300., 300., 300., 300., 300., 300., 300.])
    diffused = kernel.solveMatrixFreeFE(level, 8, 1, conductivity, heat_capacity, 0.01, initial, zero, zero)
    np.testing.assert_allclose(diffused.sum(), initial.sum(), atol=1e-10, rtol=0.)
    assert float(diffused.max()) < float(initial.max())
    assert np.isfinite(diffused).all()
    report = {
        "status": "passed_cpu_thermal_kernel_witness",
        "source_commit": "7dafdd8593711cf8ac6ccb18a1f475744610ea3d",
        "kernel_sha256": digest,
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "versions": {name: version(name) for name in ("jax", "jaxlib", "numpy", "scipy", "ml-dtypes", "pyevtk", "dill", "opt-einsum")},
        "backend": jax.default_backend(),
        "mean_heated_temperature": float(heated.mean()),
        "expected_heated_temperature": 300.02,
        "multilevel_scan_validated": False,
        "cuda_validated": False,
        "manufacturing_qualified": False,
    }
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
