"""Compare complete independent source partitions and exercise topology controls."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import numpy as np


def sha(path):
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def equivalent(first, second):
    if first.shape != second.shape:
        raise ValueError("Partition population differs")
    relation = np.unique(np.column_stack((first, second)), axis=0)
    if len(relation) != len(np.unique(first)) or len(relation) != len(np.unique(second)):
        raise ValueError("Partitions are not bijectively equivalent")
    return len(relation)


def inspect(args):
    report = json.loads((args.python / "audit.json").read_text())
    native = json.loads((args.native / "native.json").read_text())
    plan = json.loads(args.plan.read_text())
    if report["plan_sha256"] != sha(args.plan) or sha(args.arrays) != plan["source_arrays_sha256"]:
        raise ValueError("Source/plan hash mismatch")
    with np.load(args.arrays, allow_pickle=False) as d:
        faces = d["triangles"]
        nv = len(d["vertices"])
    binary = args.python / "original-faces.i64le"
    if sha(binary) != report["face_binary_sha256"] or not np.array_equal(np.fromfile(binary, dtype="<i8").reshape(-1, 3), faces):
        raise ValueError("Native source binary differs from original arrays")
    with np.load(args.python / "python-labels.npz", allow_pickle=False) as d:
        edge, vertex, metadata = (d[k] for k in ("edge_face_labels", "vertex_labels", "metadata_face_labels"))
    independent_edge = np.fromfile(args.native / "edge-face-labels.i32le", dtype="<i4")
    independent_vertex = np.fromfile(args.native / "vertex-labels.i32le", dtype="<i4")
    independent_metadata = np.fromfile(args.native / "metadata-labels.i32le", dtype="<i4")
    if len(edge) != len(faces) or len(vertex) != nv or len(metadata) != len(faces):
        raise ValueError("Incomplete source labels")
    counts = {"face_edge_components": equivalent(edge, independent_edge),
              "vertex_components_including_unused": equivalent(vertex, independent_vertex),
              "face_bearing_metadata_states": equivalent(metadata, independent_metadata)}
    for name, value in counts.items():
        expected = report["topology" if name != "face_bearing_metadata_states" else "metadata"][name]
        if native[name] != value or expected != value:
            raise ValueError("Source component census differs")
    for name in ("unique_indexed_edges", "boundary_edges"):
        if native[name] != report["topology"][name]:
            raise ValueError("Source edge incidence census differs")
    for tag, name in (("o", "object_records"), ("g", "group_records"), ("usemtl", "material_records")):
        if native[name] != report["metadata"]["record_counts"].get(tag, 0):
            raise ValueError("Original metadata tag census differs")
    if not native["all_raw_OBJ_face_indices_match"]:
        raise ValueError("Independent raw source parse missing")
    relation = np.unique(np.column_stack((edge, vertex[faces[:, 0]])), axis=0)
    if len(relation) != counts["face_edge_components"]:
        raise ValueError("An edge component crosses vertex components")
    seed_contract = json.loads(args.selections.read_text())
    mappings = []
    for row in seed_contract["files"]:
        path = args.selections.parent / row["path"]
        if sha(path) != row["sha256"]:
            raise ValueError("Fixed chamber selection changed")
        with np.load(path, allow_pickle=False) as d:
            ids = d["original_face_ids"]
        component_counts = sorted(np.unique(edge[ids], return_counts=True)[1].tolist(), reverse=True)
        mappings.append({"region": row["region"], "selected_faces": len(ids),
                         "whole_source_edge_components_touched": len(component_counts),
                         "selection_face_counts_in_components_descending": component_counts})
    return {"source_arrays_sha256": plan["source_arrays_sha256"], "plan_sha256": sha(args.plan),
            "every_face_edge_partition_label_verified": True, "every_vertex_partition_label_verified": True,
            "every_OBJ_metadata_face_assignment_verified": True, "all_original_face_indices_reparsed_independently": True,
            "face_edge_components": counts["face_edge_components"],
            "face_bearing_vertex_components": len(np.unique(vertex[faces[:, 0]])),
            "raw_named_body_partition_accepted": False, "chamber_selection_mappings": mappings,
            "complete_bare_head_selected": False, "physical_acceptance": False, "manufacturing_authorized": False}


def controls(args):
    spec = importlib.util.spec_from_file_location("current_source_audit", args.producer)
    producer = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(producer)
    args.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    vertices = [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [1, 1, 0], [1, 0, 1]]
    fixtures = [
        ("shared_edge", [[0, 1, 2], [1, 0, 3]], (1, 1)),
        ("shared_vertex_only", [[0, 1, 2], [0, 3, 4]], (2, 1)),
        ("disconnected", [[0, 1, 2], [3, 4, 5]], (2, 2)),
        ("nonmanifold", [[0, 1, 2], [1, 0, 3], [0, 1, 4]], None),
    ]
    results = {}
    for name, rows, expected in fixtures:
        directory = args.output / name
        directory.mkdir()
        faces = np.array(rows, dtype="<i8")
        binary = directory / "faces.i64le"
        faces.tofile(binary)
        obj = directory / "fixture.obj"
        text = "# Synthetic topology fixture; no specimen data\no fixture\ng first\n"
        text += "".join("v " + " ".join(map(str, row)) + "\n" for row in vertices)
        for i, face in enumerate(rows):
            if i:
                text += "g second\n"
            # Exercise positive and negative original-OBJ indexing.
            text += "f " + " ".join(str(v + 1 if i == 0 else v - len(vertices)) for v in face) + "\n"
        obj.write_text(text)
        _, _, meta, metadata = producer.metadata(obj, faces, len(vertices))
        python_error = None
        try:
            report, edge, vertex = producer.topology(faces, len(vertices))
        except ValueError as error:
            python_error = str(error)
        native_dir = directory / "native"
        command = [str(args.executable), str(binary), str(obj), str(len(vertices)), str(len(faces)), str(native_dir)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        (directory / "native.log").write_text(result.stdout + result.stderr)
        if expected is None:
            if python_error != "Nonmanifold original source edge" or result.returncode == 0 or "Nonmanifold original source edge" not in result.stderr or (native_dir / "native.json").exists():
                raise ValueError("Nonmanifold source refusal control failed")
            results[name] = {"both_refused": True, "no_success_native_output": True}
        else:
            if python_error or result.returncode != 0:
                raise ValueError("Valid source topology control failed")
            if (report["face_edge_components"], report["face_bearing_vertex_components"]) != expected:
                raise ValueError("Analytic component control differs")
            equivalent(edge, np.fromfile(native_dir / "edge-face-labels.i32le", dtype="<i4"))
            equivalent(vertex, np.fromfile(native_dir / "vertex-labels.i32le", dtype="<i4"))
            equivalent(metadata, np.fromfile(native_dir / "metadata-labels.i32le", dtype="<i4"))
            if meta["face_bearing_metadata_states"] != 2:
                raise ValueError("Two-state OBJ metadata control failed")
            results[name] = {"face_edge_components": expected[0], "face_bearing_vertex_components": expected[1],
                             "all_three_partitions_independently_matched": True, "positive_and_negative_OBJ_indices_checked": True}
    (args.output / "controls.json").write_text(json.dumps(results, indent=2) + "\n")
    return results


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("inspect", "controls"))
    for key in ("arrays", "python", "native", "plan", "selections", "producer", "executable"):
        p.add_argument("--" + key, type=Path)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise ValueError("Existing verification output refused")
    result = inspect(a) if a.mode == "inspect" else controls(a)
    if a.mode == "inspect":
        a.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
