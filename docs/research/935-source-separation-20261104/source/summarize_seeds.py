#!/usr/bin/env python3
"""Map fixed source selections to independently verified whole-source components.

Publish counts only. Component size is not an anatomical classification.
Run after check_source.py inspect; original labels and selections stay private.
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Existing output refused")
    verification = json.loads((args.results / "verification.json").read_text())
    if not verification["every_face_edge_partition_label_verified"]:
        raise ValueError("Whole-source partition verification missing")
    with np.load(args.results / "python-audit/python-labels.npz", allow_pickle=False) as data:
        labels = data["edge_face_labels"]
    native = np.fromfile(args.results / "native-audit/edge-face-labels.i32le", dtype="<i4")
    if len(labels) != len(native):
        raise ValueError("Partition lengths differ")
    _, counts = np.unique(labels, return_counts=True)
    rows = []
    contract = json.loads((args.results / "selection-inputs.json").read_text())
    for item in contract["files"]:
        path = args.results / item["path"]
        if sha(path) != item["sha256"]:
            raise ValueError("Fixed selection hash mismatch")
        with np.load(path, allow_pickle=False) as data:
            ids = data["original_face_ids"]
        if len(np.unique(ids)) != len(ids) or np.any(ids < 0) or np.any(ids >= len(labels)):
            raise ValueError("Invalid or repeated source faces")
        chosen = np.unique(labels[ids])
        if len(chosen) != 1 or len(np.unique(native[ids])) != 1:
            raise ValueError("Selection spans multiple components")
        selected_component = labels == chosen[0]
        independent_component = native == native[ids[0]]
        if not np.array_equal(selected_component, independent_component):
            raise ValueError("Independent whole-component membership differs")
        size = int(selected_component.sum())
        rows.append({"region": item["region"], "selected_faces": len(ids),
                     "whole_component_faces": size,
                     "strictly_larger_components": int((counts > size).sum()),
                     "complete_component_membership_independently_matched": True})
    result = {"source_sha256": sha(Path(__file__)), "regions": rows,
              "component_size_is_anatomical_identity": False,
              "complete_bare_head_selected": False,
              "manufacturing_authorized": False}
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
