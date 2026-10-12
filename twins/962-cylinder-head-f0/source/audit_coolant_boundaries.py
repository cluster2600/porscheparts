"""Inspect the retained F0 meshes; diagnose sampled interfaces without CFD claims."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

FAMILY = Path(__file__).resolve().parents[1]
OFFSETS = (.25, .5, .75, 1.5)


def section(poly, x):
    import numpy as np
    import vtk
    plane = vtk.vtkPlane(); plane.SetOrigin(x, 0, 0); plane.SetNormal(1, 0, 0)
    cut = vtk.vtkCutter(); cut.SetInputData(poly); cut.SetCutFunction(plane); cut.Update()
    clean = vtk.vtkCleanPolyData(); clean.SetInputConnection(cut.GetOutputPort()); clean.Update()
    lines = clean.GetOutput()
    degrees, neighbours, perimeter = Counter(), {}, 0.
    for i in range(lines.GetNumberOfCells()):
        cell = lines.GetCell(i)
        if cell.GetNumberOfPoints() != 2:
            raise ValueError("Expected section line segments")
        a, b = cell.GetPointId(0), cell.GetPointId(1)
        if a == b:
            raise ValueError("Degenerate section edge")
        degrees.update((a, b)); neighbours.setdefault(a, set()).add(b); neighbours.setdefault(b, set()).add(a)
        perimeter += np.linalg.norm(np.array(lines.GetPoint(a)) - lines.GetPoint(b))
    if not degrees or any(v != 2 for v in degrees.values()):
        raise ValueError("Section is empty or not a closed loop")
    seen, pending = set(), [next(iter(degrees))]
    while pending:
        node = pending.pop()
        if node not in seen:
            seen.add(node); pending.extend(neighbours[node] - seen)
    if len(seen) != len(degrees):
        raise ValueError("Expected one port loop")
    fill = vtk.vtkContourTriangulator(); fill.SetInputData(lines); fill.Update()
    cap = fill.GetOutput()
    if fill.GetTriangulationError() or not cap.GetNumberOfCells():
        raise ValueError("Port triangulation failed")
    area = sum(cap.GetCell(i).ComputeArea() for i in range(cap.GetNumberOfCells()))
    if not np.isfinite(area) or area <= 0 or not np.isfinite(perimeter) or perimeter <= 0:
        raise ValueError("Invalid section metrics")
    return cap, dict(plane_x_mm=x, closed_loops=1, area_mm2=float(area),
                     perimeter_mm=float(perimeter), hydraulic_diameter_mm=float(4 * area / perimeter))


def probes(centers, normals, metal_distance, water_distance, x_limits, guard=1.5):
    # shortcut: face-centre probes miss unsampled gaps; use a conforming interface audit before CHT.
    import numpy as np
    centers, normals = np.asarray(centers, dtype=float), np.asarray(normals, dtype=float)
    if centers.ndim != 2 or centers.shape[1:] != (3,) or centers.shape != normals.shape or not len(centers):
        raise ValueError("Expected matching, nonempty point and normal arrays")
    if not np.isfinite(centers).all() or not np.isfinite(normals).all() or not np.allclose(np.linalg.norm(normals, axis=1), 1):
        raise ValueError("Invalid points or unit normals")
    if not np.isfinite(x_limits).all() or len(x_limits) != 2 or not x_limits[0] < x_limits[1] or not np.isfinite(guard) or guard <= 0:
        raise ValueError("Invalid clipping guard")
    mask = (centers[:, 0] > x_limits[0] + guard) & (centers[:, 0] < x_limits[1] - guard)
    if not mask.any():
        raise ValueError("No interior samples")
    rows, gaps = [], []
    for offset in OFFSETS:
        points = centers[mask] + offset * normals[mask]
        metal = np.array([metal_distance(tuple(p)) for p in points])
        water = np.array([water_distance(tuple(p)) for p in points])
        if not np.isfinite(metal).all() or not np.isfinite(water).all():
            raise ValueError("Nonfinite distance result")
        gap = (metal >= 0) & (water >= 0)
        rows.append(dict(offset_mm=offset, samples=len(points),
                         metal_only=int(((metal < 0) & (water >= 0)).sum()),
                         water_only=int(((water < 0) & (metal >= 0)).sum()),
                         overlap=int(((water < 0) & (metal < 0)).sum()),
                         unassigned=int(gap.sum())))
        gaps.append(points[gap])
    return rows, gaps, int((~mask).sum())


def audit(mesh_dir, output):
    import numpy as np
    import trimesh
    import vtk
    receipt = FAMILY / "derived/study-report.json"
    original = json.loads(receipt.read_text())
    for relative, digest in original["source_hashes"].items():
        if hashlib.sha256((FAMILY.parent.parent / relative).read_bytes()).hexdigest() != digest:
            raise ValueError("Retained F0 source changed: " + relative)
    paths = {n: mesh_dir / (n + ".stl") for n in ("solid", "coolant")}
    for name, path in paths.items():
        if hashlib.sha256(path.read_bytes()).hexdigest() != original["mesh_metrics"][name]["sha256"]:
            raise ValueError("Input differs from retained F0: " + name)
    if output.exists():
        raise ValueError("Output directory must be new")
    readers, distances = {}, {}
    for name, path in paths.items():
        reader = vtk.vtkSTLReader(); reader.SetFileName(str(path)); reader.Update()
        readers[name] = reader
        distance = vtk.vtkImplicitPolyDataDistance(); distance.SetInput(reader.GetOutput())
        distances[name] = distance
    water = trimesh.load_mesh(paths["coolant"], process=True)
    bounds = original["mesh_metrics"]["solid"]["bounds_mm"]
    rows, gaps, excluded = probes(water.triangles_center, water.face_normals,
        distances["solid"].EvaluateFunction, distances["coolant"].EvaluateFunction,
        [bounds[0][0], bounds[1][0]])
    caps, ports = {}, {}
    for name, x in (("inlet", bounds[0][0]), ("outlet", bounds[1][0])):
        caps[name], ports[name] = section(readers["coolant"].GetOutput(), x)
    # Only the two X terminations are expected; this is a bound check, not a leak test.
    if np.any(water.vertices[:, 1:] < np.array(bounds[0][1:])) or np.any(water.vertices[:, 1:] > np.array(bounds[1][1:])):
        raise ValueError("Unexpected coolant extension through Y/Z envelope")
    output.mkdir(parents=True)
    for name, cap in caps.items():
        writer = vtk.vtkXMLPolyDataWriter(); writer.SetFileName(str(output / (name + ".vtp")))
        writer.SetInputData(cap)
        if writer.Write() != 1:
            raise OSError("Port export failed")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 2, figsize=(10, 8), constrained_layout=True)
    for ax, row, points in zip(axes.flat, rows, gaps):
        ax.scatter(water.triangles_center[::30, 0], water.triangles_center[::30, 1], s=1, color="lightgray")
        if len(points): ax.scatter(points[:, 0], points[:, 1], s=20, color="magenta")
        ax.set(title=f"Offset {row['offset_mm']} mm: {row['unassigned']} unassigned", xlabel="X (mm)", ylabel="Y (mm)")
        ax.set_aspect("equal")
    fig.suptitle("F0 geometric probes / XY projection / NOT a CFD or leak result")
    fig.savefig(output / "boundary-probes.png", dpi=150); plt.close(fig)
    report = dict(status="sampled_interface_diagnostic_not_cfd_ready", manufacturing_authorized=False,
                  is_fitment_validated=False, hydraulic_performance_validated=False,
                  wall_thickness_qualified=False, interface_conformity_validated=False,
                  ports=ports, probes=rows, excluded_terminal_face_samples=excluded,
                  terminal_guard_mm=1.5, original_mesh_hashes={n: original["mesh_metrics"][n]["sha256"] for n in paths},
                  source_hashes={"source/audit_coolant_boundaries.py": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                                 "derived/study-report.json": hashlib.sha256(receipt.read_bytes()).hexdigest()},
                  output_hashes={n: hashlib.sha256((output / n).read_bytes()).hexdigest()
                                 for n in ("inlet.vtp", "outlet.vtp", "boundary-probes.png")},
                  runtime=dict(vtk=vtk.vtkVersion.GetVTKVersion(), trimesh=trimesh.__version__, numpy=np.__version__))
    (output / "boundary-audit.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mesh_dir", type=Path); parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.mesh_dir.resolve(), args.output_dir.resolve()), indent=2))
