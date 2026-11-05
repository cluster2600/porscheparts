"""Export the checked volume through native Gmsh, with full exact readback.

Native metric admission is independent of the preceding exact stored-coordinate
cell proof. No optimizer, boundary classification or physical load is applied.
"""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import signal
import time

import gmsh
import numpy as np


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def metric_controls():
    results = []
    for inverted in (False, True):
        gmsh.clear()
        gmsh.model.add("native_jacobian_control")
        gmsh.model.addDiscreteEntity(3, 1)
        gmsh.model.mesh.addNodes(3, 1, [1, 2, 3, 4], [0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1])
        gmsh.model.mesh.addElementsByType(1, 4, [1], [1, 3, 2, 4] if inverted else [1, 2, 3, 4])
        value = {name: float(gmsh.model.mesh.getElementQualities([1], name)[0]) for name in ("minDetJac", "minSICN", "volume")}
        assert abs(value["minDetJac"] - (-1 if inverted else 1)) < 1e-14
        assert (value["minSICN"] < 0) if inverted else (value["minSICN"] > 0)
        if not inverted:
            assert abs(value["volume"] - 1 / 6) < 1e-14
        results.append({"inverted": inverted, **value})
    gmsh.clear()
    return results


def arrays():
    tags, xyz, _ = gmsh.model.mesh.getNodes()
    order = np.argsort(tags)
    tags = tags[order]
    assert np.all(tags[1:] > tags[:-1]), "Duplicate native node label"
    nodes = xyz.reshape(-1, 3)[order]
    tetra_tags, native_tets = gmsh.model.mesh.getElementsByType(4)
    _, native_faces = gmsh.model.mesh.getElementsByType(2)
    result = []
    for values, width in ((native_tets, 4), (native_faces, 3)):
        indices = np.searchsorted(tags, values)
        assert np.all(indices < len(tags)) and np.array_equal(tags[indices], values), "Unresolved native label"
        result.append(indices.reshape(-1, width))
    return nodes, result[0], result[1], tetra_tags


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("mesh", "input-report", "surface", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(mode=0o700, exist_ok=False)
    signal.signal(signal.SIGALRM, signal.SIG_DFL)
    signal.alarm(600)
    started = time.monotonic()
    assert gmsh.__version__ == importlib.metadata.version("gmsh") == "4.12.1"
    assert sha(Path(gmsh.__file__)) == "fa69936fc45646eca8b29ab0fd9e32ebaf45216414cbc75c380b4c0db7b6f485"
    binary = Path(gmsh.lib._name)
    assert binary.is_file()
    source_report = json.loads(args.input_report.read_text())
    assert source_report["source_sha256"] == "b0810ac21b35654556dce18ef022f6d4ca8f30a847223c5d566188eab82f4e71"
    assert source_report["mesh_sha256"] == sha(args.mesh) and source_report["surface_sha256"] == sha(args.surface)
    assert source_report["all_cells_positive_for_stored_binary_coordinates"]
    assert source_report["actual_complete_boundary_and_orientation_exact"] and source_report["all_internal_faces_oppositely_oriented"]
    with np.load(args.mesh, allow_pickle=False) as data:
        nodes, tets, boundary = data["nodes"], data["tets"], data["boundary"]
    with np.load(args.surface, allow_pickle=False) as data:
        assert np.array_equal(nodes[:len(data["vertices"])], data["vertices"])
    plan = {"source_sha256": sha(Path(__file__)), "input_sha256": sha(args.mesh), "input_report_sha256": sha(args.input_report),
            "gmsh_api": gmsh.__version__, "gmsh_module_sha256": sha(Path(gmsh.__file__)), "gmsh_binary_sha256": sha(binary),
            "format": "MSH 4.1 binary", "optimization_requested": False, "unit_scope": "Coordinates inherited unchanged from hypothetical parent; no specimen calibration",
            "boundary_classification": "One unclassified source boundary, no physical port or attachment assignment",
            "kernel_alarm_seconds": 600, "physics_admitted": False, "manufacturing_qualified": False, "new_paid_compute_usd": 0}
    (args.output / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    gmsh.initialize()
    gmsh.option.setNumber("General.NumThreads", 8)
    controls = metric_controls()
    gmsh.model.add("conditioned_hypothesis_volume")
    gmsh.model.addDiscreteEntity(2, 1)
    outer = np.unique(boundary)
    inner = np.setdiff1d(np.arange(len(nodes)), outer)
    gmsh.model.mesh.addNodes(2, 1, outer + 1, nodes[outer].ravel())
    gmsh.model.mesh.addElementsByType(1, 2, np.arange(1, len(boundary) + 1), (boundary + 1).ravel())
    loop = gmsh.model.geo.addSurfaceLoop([1])
    volume = gmsh.model.geo.addVolume([loop])
    gmsh.model.geo.synchronize()
    if len(inner):
        gmsh.model.mesh.addNodes(3, volume, inner + 1, nodes[inner].ravel())
    gmsh.model.mesh.addElementsByType(volume, 4, np.arange(len(boundary) + 1, len(boundary) + len(tets) + 1), (tets + 1).ravel())
    gmsh.model.addPhysicalGroup(2, [1], 2, "source_boundary_unclassified")
    gmsh.model.addPhysicalGroup(3, [volume], 1, "hypothetical_solid")
    imported = arrays()
    for expected, actual in zip((nodes, tets, boundary), imported[:3]):
        assert np.array_equal(expected, actual), "Native import changed stored arrays"
    del imported, outer, inner
    gmsh.option.setNumber("Mesh.MshFileVersion", 4.1)
    gmsh.option.setNumber("Mesh.Binary", 1)
    gmsh.option.setNumber("Mesh.SaveAll", 0)
    mesh = args.output / "solid.msh"
    gmsh.write(str(mesh))
    gmsh.clear()
    gmsh.open(str(mesh))
    recovered = arrays()
    for expected, actual in zip((nodes, tets, boundary), recovered[:3]):
        assert np.array_equal(expected, actual), "Native MSH roundtrip changed stored arrays"
    tags = recovered[3]
    del recovered, nodes, tets, boundary
    metrics = {}
    for name in ("minDetJac", "minSICN", "volume"):
        minimum, maximum, nonfinite = float("inf"), -float("inf"), 0
        rejected_ids = []
        rejected_values = []
        for start in range(0, len(tags), 50000):
            value = np.asarray(gmsh.model.mesh.getElementQualities(tags[start:start + 50000], name))
            assert len(value) == len(tags[start:start + 50000])
            nonfinite += int((~np.isfinite(value)).sum())
            minimum = min(minimum, float(value.min()))
            maximum = max(maximum, float(value.max()))
            bad = np.flatnonzero((value <= 0) | ~np.isfinite(value))
            rejected_ids.extend((start + bad).tolist())
            rejected_values.extend(value[bad].tolist())
        path = args.output / ("private-nonpositive-" + name + ".npz")
        np.savez_compressed(path, cell_ids=np.asarray(rejected_ids, dtype=np.int64), values=np.asarray(rejected_values))
        metrics[name] = {"minimum": minimum, "maximum": maximum, "nonpositive_or_nonfinite_cells": len(rejected_ids),
                         "nonfinite_cells": nonfinite, "private_indices_sha256": sha(path)}
    gmsh.finalize()
    result = {**plan, "controls": controls, "native_import_all_arrays_exact": True, "native_readback_all_arrays_exact": True,
              "complete_node_label_mapping_verified": True, "tetrahedra": len(tags), "native_metrics": metrics,
              "native_positive_metric_witness_passed": all(value["nonpositive_or_nonfinite_cells"] == 0 for value in metrics.values()),
              "msh_sha256": sha(mesh), "msh_bytes": mesh.stat().st_size, "field_solve_executed": False,
              "openfoam_or_calculix_import_not_yet_tested": True, "seconds": time.monotonic() - started}
    (args.output / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result), flush=True)
    signal.alarm(0)


if __name__ == "__main__":
    main()
