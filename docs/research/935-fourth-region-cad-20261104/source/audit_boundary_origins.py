#!/usr/bin/env python3
"""Distinguish acquired gaps from search-selection cuts without changing source edges."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def classify(original, selected, vertex_count):
    def codes(faces):
        edges = np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1)
        return edges[:, 0] * vertex_count + edges[:, 1]
    original_codes, incidence = np.unique(codes(original), return_counts=True)
    selected_codes, uses = np.unique(codes(selected), return_counts=True)
    boundary = selected_codes[uses == 1]
    positions = np.searchsorted(original_codes, boundary)
    if np.any(positions == len(original_codes)) or not np.array_equal(original_codes[positions], boundary):
        raise ValueError("Boundary edge absent from original acquired source")
    full_uses = incidence[positions]
    if np.any((full_uses != 1) & (full_uses != 2)):
        raise ValueError("Unresolved original edge incidence")
    return boundary, full_uses


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ["arrays", "selection", "output"]:
        p.add_argument("--" + name, type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise ValueError("Existing boundary audit refused")
    if (sha(a.arrays) != "dd94c37117a1f1277a4f2b7f0bf0023e0d1858991b943f766cf447db319a101a" or
            sha(a.selection / "selected-source.npz") != "fdaf0c99285a2ab5d9f5d1928e4e4f1d5283ac25cb60264bfcc5a6f7981a9f31"):
        raise ValueError("Registered original/selection changed")
    fixture = np.array([[0, 1, 2], [1, 3, 2]], dtype=np.int64)
    _, control = classify(fixture, fixture[:1], 4)
    assert sorted(control.tolist()) == [1, 1, 2]
    with np.load(a.arrays, allow_pickle=False) as s:
        faces, vertex_count = s["triangles"], len(s["vertices"])
    with np.load(a.selection / "selected-source.npz", allow_pickle=False) as s:
        selected = faces[s["source_face_ids"]]
    boundary, incidence = classify(faces, selected, vertex_count)
    a.output.mkdir(parents=True)
    np.savez_compressed(a.output / "source-boundary-origins.npz",
                        original_vertex_edges=np.column_stack([boundary // vertex_count, boundary % vertex_count]),
                        full_original_incidence=incidence)
    result = {"boundary_edges": len(boundary), "original_scan_boundary_edges": int((incidence == 1).sum()),
              "selection_cut_edges": int((incidence == 2).sum()),
              "shared_square_control_passed": True, "source_sha256": sha(__file__),
              "no_boundaries_closed": True, "physical_acceptance": False}
    (a.output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
