"""Compare native relocation to the exact source before connectivity normalization."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def compare(raw_path, source_path, protected_vertices):
    with np.load(raw_path, allow_pickle=False) as raw, np.load(source_path, allow_pickle=False) as source:
        labels = raw["node_tags"]
        order = np.argsort(labels)
        assert np.array_equal(labels[order], np.arange(1, len(labels) + 1))
        before, after = source["nodes"], raw["coordinates"][order]
        assert before.shape == after.shape
        displacement = np.linalg.norm(after - before, axis=1)
        tets = raw["cell_node_tags"]
        old_tets = source["tets"]
        assert tets.shape == old_tets.shape
        changed_rows = 0
        for start in range(0, len(tets), 50000):
            changed_rows += int(np.count_nonzero(np.any(tets[start:start + 50000] != old_tets[start:start + 50000] + 1, axis=1)))
        return {"native_input_tetrahedral_rows_changed": changed_rows,
                "all_input_connectivity_and_row_order_retained": changed_rows == 0,
                "complete_boundary_connectivity_exact": bool(np.array_equal(raw["face_node_tags"], source["boundary"] + 1)),
                "nodes_moved": int(np.count_nonzero(displacement)),
                "protected_vertices_moved": int(np.count_nonzero(displacement[:protected_vertices])),
                "maximum_displacement_mm": float(displacement.max()),
                "maximum_protected_displacement_mm": float(displacement[:protected_vertices].max()),
                "no_coordinates_or_cells_modified_by_inspector": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("raw", "source", "surface", "raw-audit", "control-raw", "control-source", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(mode=0o700, exist_ok=False)
    with np.load(args.surface, allow_pickle=False) as surface:
        protected = len(surface["vertices"])
    control = compare(args.control_raw, args.control_source, 8)
    assert control["protected_vertices_moved"] == 0 and control["complete_boundary_connectivity_exact"]
    actual = compare(args.raw, args.source, protected)
    audit = json.loads(args.raw_audit.read_text())
    assert audit["raw_native_sha256"] == sha(args.raw) and audit["all_referenced_tags_resolve_exactly"]
    record = {"source_sha256": sha(Path(__file__)), "raw_sha256": sha(args.raw),
              "input_sha256": sha(args.source), "raw_sign_audit_sha256": sha(args.raw_audit),
              "control": control, "head": actual,
              "raw_negative_cells": audit["negative_cells"], "raw_exact_zero_cells": audit["exact_zero_cells"],
              "retained_input_connectivity_proves_orientation_changes_are_not_label_permutations": actual["all_input_connectivity_and_row_order_retained"],
              "independent_face_pairing_passed": False,
              "optimized_head_admitted": False, "physics_admitted": False, "manufacturing_qualified": False}
    (args.output / "report.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record), flush=True)


if __name__ == "__main__":
    main()
