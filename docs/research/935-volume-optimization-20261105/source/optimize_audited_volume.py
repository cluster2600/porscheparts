"""Capture native Netgen tags and coordinates before retained export checks.

This diagnostic changes no optimization setting. A unique, complete node-tag
mapping must be established before the exact-sign audit attributes a zero cell
to the native readback. No audit result grants solver admission.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

import gmsh
import numpy as np


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recipe", type=Path, required=True)
    args, forward = parser.parse_known_args()
    output = Path(forward[forward.index("--output") + 1])
    geometric = module(Path(__file__).with_name("optimize_geometric_volume.py"), "retained_audited_region")
    io = module(args.recipe, "retained_audited_io")
    inspector = Path(forward[forward.index("--interval-inspector") + 1])
    orient = module(inspector, "retained_audited_signs")
    native = gmsh.model.mesh.optimize

    def optimize(method="", force=False, niter=1, dimTags=None):
        native(method, force=force, niter=niter, dimTags=dimTags or [])
        tags, xyz, _ = gmsh.model.mesh.getNodes()
        element_tags, cells = gmsh.model.mesh.getElementsByType(4)
        face_tags, faces = gmsh.model.mesh.getElementsByType(2)
        raw = output / "raw-native-tags.npz"
        np.savez_compressed(raw, node_tags=tags, coordinates=xyz.reshape(-1, 3),
                            element_tags=element_tags, cell_node_tags=cells.reshape(-1, 4),
                            face_tags=face_tags, face_node_tags=faces.reshape(-1, 3))
        order = np.argsort(tags)
        sorted_tags = tags[order]
        unique = bool(np.all(sorted_tags[1:] > sorted_tags[:-1]))
        record = {"wrapper_sha256": io.sha(Path(__file__)), "raw_native_sha256": io.sha(raw),
                  "geometric_adapter_sha256": io.sha(Path(geometric.__file__)),
                  "actual_method": method, "niter_argument": niter,
                  "one_native_api_call": True, "node_count": len(tags),
                  "tetrahedron_count": len(element_tags), "node_tags_unique": unique,
                  "physics_admitted": False, "manufacturing_qualified": False}
        receipt = output / "native-tag-audit.json"
        receipt.write_text(json.dumps(record, indent=2) + "\n")
        assert unique, "Native node tags are not unique"
        tets = np.searchsorted(sorted_tags, cells).reshape(-1, 4)
        boundary = np.searchsorted(sorted_tags, faces).reshape(-1, 3)
        for native_tags, indices in ((cells.reshape(-1, 4), tets), (faces.reshape(-1, 3), boundary)):
            assert np.all(indices < len(tags)) and np.array_equal(sorted_tags[indices], native_tags), "Missing node tag"
        nodes = xyz.reshape(-1, 3)[order]
        assert np.isfinite(nodes).all(), "Non-finite native coordinate"
        repeated = int(np.count_nonzero(np.any(np.diff(np.sort(tets, axis=1), axis=1) == 0, axis=1)))
        positive = negative = ambiguous = 0
        zeros = []
        for start in range(0, len(tets), 50000):
            positions = nodes[tets[start:start + 50000]]
            low, high = orient.determinant_interval(positions)
            positive += int(np.count_nonzero(low > 0))
            negative += int(np.count_nonzero(high < 0))
            uncertain = np.flatnonzero((low <= 0) & (high >= 0))
            ambiguous += len(uncertain)
            for i in uncertain:
                exact = orient.exact_determinant(positions[i])
                positive += exact > 0
                negative += exact < 0
                if exact == 0:
                    zeros.append(start + int(i))
        assert positive + negative + len(zeros) == len(tets)
        np.save(output / "private-zero-cell-indices.npy", np.asarray(zeros, dtype=np.int64))
        record.update({"all_referenced_tags_resolve_exactly": True, "coordinates_finite": True,
                       "cells_with_repeated_node_tags": repeated, "positive_cells": positive,
                       "negative_cells": negative, "exact_zero_cells": len(zeros),
                       "exact_fraction_fallbacks": ambiguous,
                       "sign_scope": "Every native cell, stored binary64 coordinates; outward intervals then exact fractions",
                       "zero_cause_beyond_native_readback_established": False})
        receipt.write_text(json.dumps(record, indent=2) + "\n")

    gmsh.model.mesh.optimize = optimize
    previous = sys.argv
    sys.argv = [str(geometric.__file__), "--recipe", str(args.recipe), *forward]
    try:
        geometric.main()
    finally:
        gmsh.model.mesh.optimize = native
        sys.argv = previous


if __name__ == "__main__":
    main()
