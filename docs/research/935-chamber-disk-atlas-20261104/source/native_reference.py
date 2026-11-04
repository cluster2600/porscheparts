"""Build or independently inspect exact disk-grouped acquired-facet STEP references."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np


BUILDER_SHA = "fca5259ef3b3412a72e441fea39816e14fea4e375095e1c83def2e4117f6ae8e"
INSPECTOR_SHA = "3a2ddf947a1083399890dc167ec631fec0bce4d5a7a564613a765fcd95158658"


def sha(path):
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def module(path, expected):
    if sha(path) != expected:
        raise ValueError("Frozen native helper changed")
    spec = importlib.util.spec_from_file_location("frozen_native_helper", path)
    result = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(result)
    return result


def inspect(step, vertices, faces, ids, labels, helper, output):
    from OCP.BRep import BRep_Tool
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_SHELL, TopAbs_SOLID, TopAbs_VERTEX
    from OCP.TopExp import TopExp
    from OCP.TopoDS import TopoDS
    from scipy.spatial import cKDTree

    before = sha(step)
    if step.suffix == ".brep":
        from OCP.BRep import BRep_Builder
        from OCP.BRepTools import BRepTools
        from OCP.BRepCheck import BRepCheck_Analyzer
        from OCP.TopoDS import TopoDS_Shape
        units = json.loads(step.with_suffix(".units.json").read_text())
        if units != {"native_sha256": before, "units": "mm", "authority": "owner-confirmed OBJ scale; not independent metrology"}:
            raise ValueError("Native BREP units sidecar mismatch")
        shape = TopoDS_Shape()
        if not BRepTools.Read_s(shape, str(step), BRep_Builder()) or not BRepCheck_Analyzer(shape).IsValid():
            raise ValueError("Actual native BREP load failed")
    else:
        shape = helper.load(step)
    vm, em, fm, sm = [helper.indexed(shape, t) for t in (TopAbs_VERTEX, TopAbs_EDGE, TopAbs_FACE, TopAbs_SHELL)]
    if helper.indexed(shape, TopAbs_SOLID).Extent():
        raise ValueError("Unexpected solid in acquired reference")
    vi = np.unique(faces)
    if len(np.unique(vertices[vi], axis=0)) != len(vi):
        raise ValueError("Ambiguous original coordinates")
    positions = []
    for i in range(1, vm.Extent() + 1):
        p = BRep_Tool.Pnt_s(TopoDS.Vertex_s(vm.FindKey(i)))
        positions.append([p.X(), p.Y(), p.Z()])
    distance, nearest = cKDTree(vertices[vi]).query(np.array(positions))
    mapped = vi[nearest]
    if distance.max() > 1e-6 or len(mapped) != len(vi) or len(np.unique(mapped)) != len(vi):
        raise ValueError("Global original vertex sharing was changed")
    original_edges = set()
    for f in faces:
        for i in range(3):
            original_edges.add(tuple(sorted((int(f[i]), int(f[(i + 1) % 3])))))
    actual_edges = []
    for i in range(1, em.Extent() + 1):
        e = TopoDS.Edge_s(em.FindKey(i))
        first = vm.FindIndex(TopExp.FirstVertex_s(e))
        last = vm.FindIndex(TopExp.LastVertex_s(e))
        actual_edges.append(tuple(sorted((int(mapped[first - 1]), int(mapped[last - 1])))))
    if len(actual_edges) != len(original_edges) or set(actual_edges) != original_edges:
        raise ValueError("Global original edge sharing was changed")
    if fm.Extent() != len(ids) or sm.Extent() != len(np.unique(labels)):
        raise ValueError("Native face or disk-shell coverage changed")
    by_vertices = {tuple(sorted(map(int, face))): int(label) for face, label in zip(faces, labels)}
    if len(by_vertices) != len(faces):
        raise ValueError("Duplicate original indexed face")
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    seen, per_shell = [], []
    max_plane = 0.
    for i in range(1, sm.Extent() + 1):
        shell = sm.FindKey(i)
        first_face = helper.indexed(shell, TopAbs_FACE).FindKey(1)
        corners = helper.indexed(first_face, TopAbs_VERTEX)
        key = tuple(sorted(int(mapped[vm.FindIndex(corners.FindKey(j)) - 1]) for j in range(1, corners.Extent() + 1)))
        if key not in by_vertices:
            raise ValueError("Actual shell introduced an unacquired triangle")
        label = by_vertices[key]
        if label in seen:
            raise ValueError("Duplicate native disk shell")
        seen.append(label)
        path = output / f"shell-{i:04d}.step"
        writer = STEPControl_Writer()
        if writer.Transfer(shell, STEPControl_AsIs) != IFSelect_RetDone or writer.Write(str(path)) != IFSelect_RetDone:
            raise ValueError("Actual shell re-export failed")
        selection = labels == label
        checked = helper.inspect_source(path, vertices, faces[selection], ids[selection])
        per_shell.append(checked)
    for i in range(1, fm.Extent() + 1):
        face = TopoDS.Face_s(fm.FindKey(i))
        plane = BRepAdaptor_Surface(face, True).Plane()
        corners = helper.indexed(face, TopAbs_VERTEX)
        for j in range(1, corners.Extent() + 1):
            max_plane = max(max_plane, plane.Distance(BRep_Tool.Pnt_s(TopoDS.Vertex_s(corners.FindKey(j)))))
    if sorted(seen) != sorted(np.unique(labels).tolist()) or max_plane > 1e-6 or sha(step) != before:
        raise ValueError("Disk coverage, plane consistency or STEP preservation failed")
    if step.suffix != ".brep" and "SI_UNIT(.MILLI.,.METRE.)" not in step.read_text():
        raise ValueError("Explicit STEP millimetre declaration missing")
    return {"step_sha256": before, "source_faces": len(ids), "native_faces": fm.Extent(),
            "native_vertices": vm.Extent(), "source_edges": len(original_edges), "native_edges": em.Extent(),
            "native_disk_shells": sm.Extent(), "native_solids": 0,
            "vertex_roundtrip_maximum_mm": float(distance.max()),
            "normal_roundtrip_maximum_error": max(r["normal_roundtrip_maximum_error"] for r in per_shell),
            "native_plane_corner_maximum_mm": max_plane,
            "every_original_face_once": True, "global_original_vertex_and_edge_sharing_preserved": True,
            "every_actual_shell_independently_checked": True, "units_mm_checked": True,
            "format": "native BREP with hash-bound units sidecar" if step.suffix == ".brep" else "STEP"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("build", "verify"))
    for key in ("arrays", "plan", "atlas", "verification", "helper", "output"):
        p.add_argument("--" + key, type=Path, required=True)
    p.add_argument("--steps", type=Path)
    p.add_argument("--format", choices=("step", "brep"), default="step")
    a = p.parse_args()
    if a.output.exists():
        raise ValueError("Existing native output refused")
    plan = json.loads(a.plan.read_text())
    verification = json.loads(a.verification.read_text())
    if (sha(a.arrays) != plan["source_arrays_sha256"] or verification["plan_sha256"] != sha(a.plan) or
            verification["atlas_report_sha256"] != sha(a.atlas / "atlas.json") or
            verification["eligible_for_exact_native_reference_export"] is not True or len(verification["regions"]) != 8):
        raise ValueError("Independent atlas admission missing")
    helper = module(a.helper, BUILDER_SHA if a.mode == "build" else INSPECTOR_SHA)
    with np.load(a.arrays, allow_pickle=False) as data:
        vertices, original_faces = data["vertices"], data["triangles"]
    a.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    def export(shape, path):
        if a.format == "brep":
            from OCP.BRepTools import BRepTools
            if not BRepTools.Write_s(shape, str(path)):
                raise ValueError("Native BREP write failed")
            path.with_suffix(".units.json").write_text(json.dumps({"native_sha256": sha(path), "units": "mm", "authority": "owner-confirmed OBJ scale; not independent metrology"}, indent=2) + "\n")
        else:
            helper.export(shape, path)

    if a.mode == "build":
        v = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.], [1., 1., 0.]])
        f = np.array([[0, 1, 2], [1, 3, 2]])
        export(helper.native_shape(v, f, np.array([0, 1])), a.output / ("shared-edge-fixture." + a.format))
    else:
        if a.steps is None:
            raise ValueError("Actual STEP directory required")
        # Independent fixed unit-square contract, two shells sharing an original edge.
        v = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.], [1., 1., 0.]])
        f = np.array([[0, 1, 2], [1, 3, 2]])
        fixture = inspect(a.steps / ("shared-edge-fixture." + a.format), v, f, np.array([0, 1]),
                          np.array([0, 1]), helper, a.output / "fixture-inspection")
        if (fixture["native_vertices"], fixture["native_edges"], fixture["native_faces"], fixture["native_disk_shells"]) != (4, 5, 2, 2):
            raise ValueError("Shared-edge native fixture failed")
    results = []
    for i, certificate in enumerate(verification["regions"]):
        path = a.atlas / f"region-{i}-atlas.npz"
        if sha(path) != certificate["atlas_sha256"] or certificate["region"] != i:
            raise ValueError("Independently checked atlas changed")
        with np.load(path, allow_pickle=False) as data:
            ids, vi, triangles, labels = (data[k] for k in ("original_face_ids", "original_vertex_ids", "original_local_triangles", "labels"))
        if not np.array_equal(vi[triangles], original_faces[ids]):
            raise ValueError("Original source geometry changed")
        step_name = f"observed-chamber-region-{i}.{a.format}"
        if a.mode == "build":
            export(helper.native_shape(vertices[vi], triangles, labels), a.output / step_name)
            result = {"region": i, "source_faces": len(ids), "disk_shells": len(np.unique(labels)),
                      "step_sha256": sha(a.output / step_name), "coordinates_changed": False}
        else:
            result = inspect(a.steps / step_name, vertices, original_faces[ids], ids, labels,
                             helper, a.output / f"region-{i}-shell-inspections")
            result["region"] = i
        results.append(result)
    result = {"mode": a.mode, "source_sha256": sha(__file__), "helper_sha256": sha(a.helper),
              "atlas_verification_sha256": sha(a.verification), "regions": results,
              "synthetic_shared_edge_fixture_verified": a.mode == "verify",
              "smooth_surface_created": False, "full_head_created": False,
              "physical_acceptance": False, "manufacturing_authorized": False}
    (a.output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
