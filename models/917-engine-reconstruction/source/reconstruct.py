#!/usr/bin/env python3
"""Reconstruct observed 917 surfaces with PicoGK; independently audit the meshes."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import subprocess

ROOT = Path(__file__).resolve().parents[3]
EXPECTED_SHA256 = "428c4143d073f8330022f2fecbd1ac1ee7784d4f1565f1160020448dbdffa0ae"


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_output(output):
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT / "work") or output == ROOT / "work":
        raise ValueError("Output must be a new directory under ignored work/")
    if output.exists():
        raise ValueError("Output already exists; previous experiments must be preserved")
    return output


def check_voxels(values):
    if len(values) < 2 or len(set(values)) != len(values) or any(not math.isfinite(v) or v <= 0 for v in values):
        raise ValueError("At least two distinct positive finite voxel sizes are required")
    return sorted(values, reverse=True)


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def audit(reference, candidate, samples=2000):
    import numpy as np
    import trimesh

    def distance(left, right):
        points, _ = trimesh.sample.sample_surface(left, samples, seed=917)
        # Bound temporary proximity-query memory for the multi-million-face scan.
        distances = np.concatenate([trimesh.proximity.closest_point(right, chunk)[1]
                                    for chunk in np.array_split(points, 20)])
        if not np.isfinite(distances).all():
            raise ValueError("Non-finite surface distances")
        return {"samples": samples, "median": float(np.median(distances)),
                "p95": float(np.percentile(distances, 95)), "max_sampled": float(distances.max())}

    finite = bool(np.isfinite(candidate.vertices).all())
    watertight = bool(candidate.is_watertight)
    winding = bool(candidate.is_winding_consistent)
    if not finite or not watertight or not winding or candidate.volume <= 0:
        raise ValueError(f"Invalid shell geometry: finite={finite}, watertight={watertight}, "
                         f"winding_consistent={winding}, volume={candidate.volume}")
    return {"finite": finite, "watertight": watertight, "winding_consistent": winding,
            "vertices": len(candidate.vertices), "triangles": len(candidate.faces),
            "connected_surface_components": len(candidate.split(only_watertight=False)),
            "bounds_source_units": candidate.bounds.tolist(),
            "shell_mesh_volume_source_units_cubed": float(candidate.volume),
            "source_to_shell_distance_source_units": distance(reference, candidate),
            "shell_to_source_distance_source_units": distance(candidate, reference),
            "dimensional_acceptance": "not_established_no_calibrated_scan_or_engineering_tolerance"}


def run(source, output, dotnet, voxels):
    import numpy as np
    import trimesh

    output = check_output(output)
    voxels = check_voxels(voxels)
    source = Path(source).resolve()
    if sha256(source) != EXPECTED_SHA256:
        raise ValueError("Canonical source scan hash mismatch")
    os.umask(0o077)
    output.mkdir(parents=True)
    save(output / "status.json", {"status": "running", "manufacturing_authorized": False})
    try:
        scan = trimesh.load_mesh(source, process=False, maintain_order=True)
        if not isinstance(scan, trimesh.Trimesh) or not np.isfinite(scan.vertices).all():
            raise ValueError("Expected a finite triangular scan mesh")
        # STL repeats float32 vertices; quantify transport error without welding or repair.
        float_error = float(np.linalg.norm(scan.vertices.astype(np.float32).astype(float) - scan.vertices, axis=1).max())
        transport = output / "observed-source.stl"
        scan.export(transport)
        transport_hash = sha256(transport)
        app = output / "app"
        command = [dotnet, "build", str(Path(__file__).with_name("ScanShell.csproj")),
                   "-c", "Release", "-o", str(app),
                   "-p:BaseIntermediateOutputPath=" + str(output / "obj") + os.sep]
        with (output / "build.log").open("x") as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
        results = []
        for voxel in voxels:
            target = output / f"voxel-{voxel:g}"
            print(f"PicoGK observed surface shell: {voxel:g} source units", flush=True)
            with (output / f"voxel-{voxel:g}.log").open("x") as log:
                subprocess.run([dotnet, str(app / "ScanShell.dll"), str(transport), transport_hash,
                                str(voxel), str(target)], stdout=log, stderr=subprocess.STDOUT, check=True)
            receipt = json.loads((target / "receipt.json").read_text())
            for suffix in ("stl", "vdb"):
                if sha256(target / f"observed-surface-shell.{suffix}") != receipt[f"{suffix}_sha256"]:
                    raise ValueError("PicoGK output hash mismatch")
            if receipt["input_sha256"] != transport_hash or receipt["voxel_size_source_units"] != voxel:
                raise ValueError("PicoGK receipt input mismatch")
            mesh = trimesh.load_mesh(target / "observed-surface-shell.stl", process=True)
            validation = audit(scan, mesh)
            save(target / "independent-mesh-audit.json", validation)
            results.append({"voxel_size_source_units": voxel, "receipt": receipt, "audit": validation})
        if sha256(source) != EXPECTED_SHA256 or sha256(transport) != transport_hash:
            raise ValueError("Source changed during execution")
        report = {"status": "observed_surface_reconstruction_executed_not_functional",
                  "toolchain": {"python": platform.python_version(), "platform": platform.platform(),
                                "numpy": np.__version__, "trimesh": trimesh.__version__,
                                "dotnet": subprocess.check_output([dotnet, "--version"], text=True).strip(),
                                "executable_sha256": sha256(app / "ScanShell.dll"),
                                "source_sha256": {name: sha256(Path(__file__).with_name(name))
                                                   for name in ("Program.cs", "ScanShell.csproj", "reconstruct.py")}},
                  "source_sha256": EXPECTED_SHA256, "source_units": None,
                  "source_bounds": scan.bounds.tolist(), "source_triangles": len(scan.faces),
                  "source_watertight": bool(scan.is_watertight),
                  "maximum_stl_float32_transport_error_source_units": float_error,
                  "transport_sha256": transport_hash, "results": results,
                  "resolution_comparison": "shell thickness changes with voxel size; not fixed-geometry convergence",
                  "release_gates": {key: False for key in (
                      "scan_scale_verified", "variant_identified", "functional_interfaces_verified",
                      "internal_geometry_verified", "material_qualified", "solver_validated",
                      "manufacturing_authorized", "engine_start_authorized")}}
        save(output / "report.json", report)
        save(output / "status.json", {"status": "completed_surface_audit_only", "manufacturing_authorized": False})
        return report
    except Exception as error:
        save(output / "status.json", {"status": "failed_not_released", "error_type": type(error).__name__,
                                      "error": str(error),
                                      "manufacturing_authorized": False})
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--dotnet", required=True)
    parser.add_argument("--voxels", nargs="+", type=float, default=[3, 2])
    args = parser.parse_args()
    run(args.source, args.output, args.dotnet, args.voxels)
