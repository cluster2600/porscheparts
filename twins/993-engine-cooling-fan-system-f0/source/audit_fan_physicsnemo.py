#!/usr/bin/env python3
"""Audit the actual PicoGK mesh with PhysicsNeMo; this does not predict flow."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path

import numpy as np
import torch
import trimesh
from physicsnemo.mesh import Mesh


def audit(source: Path, out: Path, device="cpu"):
    if device != "cpu" and not (device.startswith("cuda") and torch.cuda.is_available()):
        raise ValueError("Requested audit device unavailable")
    if not source.name.endswith("-mm.stl"):
        raise ValueError("Expected a PicoGK -mm.stl export")
    metre_source = source.with_name(source.name.removesuffix("-mm.stl") + "-metres.stl")
    # PicoGK exports binary STL in identical triangle order in both units.
    triangle = np.dtype([("normal", "<f4", 3), ("vertices", "<f4", (3, 3)), ("attr", "<u2")])
    mm_triangles = np.memmap(source, dtype=triangle, mode="r", offset=84)
    m_triangles = np.memmap(metre_source, dtype=triangle, mode="r", offset=84)
    units_match = (len(mm_triangles) == len(m_triangles) and np.allclose(
        mm_triangles["vertices"] * .001, m_triangles["vertices"], rtol=1e-6, atol=1e-9))
    surface = trimesh.load_mesh(source, process=True)
    if not isinstance(surface, trimesh.Trimesh) or len(surface.faces) == 0:
        raise ValueError("Expected nonempty triangular surface")
    points = torch.as_tensor(np.array(surface.vertices), dtype=torch.float64, device=device)
    cells = torch.as_tensor(np.array(surface.faces), dtype=torch.int64, device=device)
    mesh = Mesh(points=points, cells=cells)
    areas = mesh.cell_areas.detach().cpu().numpy()
    normals = mesh.cell_normals.detach().cpu().numpy()
    area_agreement = np.allclose(areas, surface.area_faces, rtol=1e-6, atol=1e-12)
    passed = (surface.is_watertight and surface.is_winding_consistent
              and surface.body_count == 1 and surface.volume > 0
              and np.isfinite(normals).all() and np.isfinite(areas).all()
              and (areas > 0).all() and area_agreement and units_match)
    report = {
        "status": "surface_audit_passed" if passed else "surface_audit_failed",
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "metres_surface_sha256": hashlib.sha256(
            metre_source.read_bytes()).hexdigest(),
        "metres_export_matches_mm": bool(units_match),
        "picogk_report_sha256": hashlib.sha256(
            source.with_name("picogk-report.json").read_bytes()).hexdigest(),
        "physicsnemo_version": importlib.metadata.version("nvidia-physicsnemo"),
        "torch_version": torch.__version__, "device": str(points.device),
        "vertices": len(points), "triangles": len(cells),
        "watertight": bool(surface.is_watertight),
        "winding_consistent": bool(surface.is_winding_consistent),
        "connected_bodies": int(surface.body_count),
        "volume_mm3": float(surface.volume), "bounds_mm": surface.bounds.tolist(),
        "physicsnemo_surface_area_mm2": float(areas.sum()),
        "area_matches_independent_trimesh": bool(area_agreement),
        "airflow_m3_s": None, "aerodynamic_optimization_completed": False,
        "manufacturing_authorized": False,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if not passed:
        raise RuntimeError("Surface audit failed; CFD handoff prohibited")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("surface", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("--device", default="cpu")
    a = p.parse_args()
    audit(a.surface, a.out, a.device)
