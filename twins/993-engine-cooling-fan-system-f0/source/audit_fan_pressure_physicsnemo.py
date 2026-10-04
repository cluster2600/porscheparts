#!/usr/bin/env python3
"""Independently integrate OpenFOAM rotor pressure with PhysicsNeMo Mesh."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path

import numpy as np
import torch
from physicsnemo.mesh import Mesh


def read_patch(path):
    text = path.read_text()
    if "ASCII" not in text.splitlines()[:4] or "DATASET POLYDATA" not in text:
        raise ValueError("Expected legacy ASCII VTK POLYDATA from foamToVTK")
    tokens = text.split()
    i = tokens.index("POINTS")
    count = int(tokens[i+1])
    points = np.asarray(tokens[i+3:i+3+3*count], dtype=float).reshape(count, 3)
    i = tokens.index("POLYGONS")
    faces, size = int(tokens[i+1]), int(tokens[i+2])
    end = i + 3 + size
    i += 3
    polygons = []
    for _ in range(faces):
        n = int(tokens[i])
        face = list(map(int, tokens[i+1:i+1+n]))
        if n < 3 or min(face) < 0 or max(face) >= count:
            raise ValueError("Invalid polygon")
        polygons.append(face)
        i += 1+n
    if i != end:
        raise ValueError("Polygon count mismatch")
    i = tokens.index("CELL_DATA")
    if int(tokens[i+1]) != faces:
        raise ValueError("Pressure must be cell data on the rotor patch")
    i = tokens.index("p", i)
    if int(tokens[i+1]) != 1 or int(tokens[i+2]) != faces:
        raise ValueError("Expected scalar pressure for every face")
    pressure = np.asarray(tokens[i+4:i+4+faces], dtype=float)
    if not np.isfinite(points).all() or not np.isfinite(pressure).all():
        raise ValueError("Nonfinite geometry or pressure")
    return points, polygons, pressure


def integrate(points, polygons, pressure, rho=1.2, device="cpu"):
    if device != "cpu" and not (device.startswith("cuda") and torch.cuda.is_available()):
        raise ValueError("Requested audit device unavailable")
    vertices = list(points)
    triangles, values = [], []
    for face, p in zip(polygons, pressure, strict=True):
        center = len(vertices)
        vertices.append(np.mean(points[face], axis=0))
        for a, b in zip(face, face[1:]+face[:1]):
            triangles.append([center, a, b])
            values.append(p * rho)
    xyz = torch.as_tensor(np.asarray(vertices), dtype=torch.float64, device=device)
    cells = torch.as_tensor(np.asarray(triangles), dtype=torch.int64, device=device)
    mesh = Mesh(points=xyz, cells=cells)
    forces = mesh.cell_normals * mesh.cell_areas[:, None] * torch.tensor(values, dtype=torch.float64, device=device)[:, None]
    centers = xyz[cells].mean(dim=1)
    moments = torch.linalg.cross(centers, forces)
    force, moment = forces.sum(dim=0).cpu().numpy(), moments.sum(dim=0).cpu().numpy()
    if not np.isfinite(force).all() or not np.isfinite(moment).all():
        raise ValueError("Invalid pressure integral")
    return force, moment


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vtk", type=Path, nargs="?")
    parser.add_argument("--forces", type=Path)
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()
    if args.vtk is None:
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            patch = Path(tmp) / "rotor_1.vtk"
            patch.write_text("# vtk DataFile Version 2.0\ntriangle\nASCII\nDATASET POLYDATA\n"
                "POINTS 3 float\n0 0 0 1 0 0 0 1 0\nPOLYGONS 1 4\n3 0 1 2\n"
                "CELL_DATA 1\nFIELD attributes 1\np 1 1 float\n2\n")
            f, m = integrate(*read_patch(patch), device=args.device)
            patch.write_text(patch.read_text().replace("CELL_DATA 1", "CELL_DATA 2"))
            try:
                read_patch(patch)
            except ValueError:
                pass
            else:
                raise AssertionError("Invalid pressure cell count accepted")
        assert np.allclose(f, [0,0,1.2]) and np.allclose(m, [.4,-.4,0])
        print("PhysicsNeMo pressure integral self-check passed")
    else:
        if args.forces is None:
            parser.error("--forces is required with a VTK patch")
        f, m = integrate(*read_patch(args.vtk), device=args.device)
        row = [line for line in args.forces.read_text().splitlines() if line.strip() and not line.startswith("#")][-1]
        values = np.asarray(list(map(float, row.replace("(", " ").replace(")", " ").split())))
        if len(values) != 13 or not np.isfinite(values).all():
            raise ValueError("Invalid OpenFOAM force record")
        if float(args.vtk.stem.rsplit("_", 1)[-1]) != values[0]:
            raise ValueError("VTK export time and force record do not match")
        force_error = np.linalg.norm(f-values[1:4]) / max(np.linalg.norm(values[1:4]), 1e-12)
        moment_error = np.linalg.norm(m-values[7:10]) / max(np.linalg.norm(values[7:10]), 1e-12)
        result = {"status":"pressure_integral_only_not_flow_validation", "rho_kg_m3":1.2,
            "device":str(torch.device(args.device)), "torch_version":torch.__version__,
            "physicsnemo_version":importlib.metadata.version("nvidia-physicsnemo"),
            "pressure_force_N":f.tolist(), "pressure_moment_Nm":m.tolist(),
            "relative_force_error":float(force_error), "relative_moment_error":float(moment_error),
            "matches_openfoam_within_half_percent":bool(max(force_error,moment_error)<.005),
            "vtk_sha256":hashlib.sha256(args.vtk.read_bytes()).hexdigest(),
            "forces_sha256":hashlib.sha256(args.forces.read_bytes()).hexdigest()}
        args.vtk.with_suffix(".physicsnemo.json").write_text(json.dumps(result,indent=2)+"\n")
        print(json.dumps(result,indent=2))
        if not result["matches_openfoam_within_half_percent"]:
            raise RuntimeError("Independent pressure-force integration does not agree")
