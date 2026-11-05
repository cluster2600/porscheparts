"""Inspect retained native label references without inventing missing coordinates."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def inspect(path):
    with np.load(path, allow_pickle=False) as data:
        tags = np.sort(data["node_tags"])
        assert np.all(tags[1:] > tags[:-1]), "Duplicate native node tags"
        summary = {"nodes": len(tags), "native_node_tags_unique": True,
                   "minimum_node_tag": int(tags[0]), "maximum_node_tag": int(tags[-1])}
        for name, key in (("tetrahedra", "cell_node_tags"), ("boundary", "face_node_tags")):
            refs = data[key]
            position = np.searchsorted(tags, refs)
            valid = position < len(tags)
            valid[valid] &= tags[position[valid]] == refs[valid]
            missing = np.unique(refs[~valid])
            summary[name] = {"elements": len(refs), "missing_references": int((~valid).sum()),
                             "elements_with_missing_references": int((~valid).any(axis=1).sum()),
                             "distinct_missing_tags": len(missing),
                             "minimum_missing_tag": int(missing.min()) if len(missing) else None,
                             "maximum_missing_tag": int(missing.max()) if len(missing) else None}
        summary["all_references_resolve"] = all(summary[key]["missing_references"] == 0 for key in ("tetrahedra", "boundary"))
        return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(mode=0o700, exist_ok=False)
    control = inspect(args.control)
    assert control["all_references_resolve"]
    with np.load(args.control, allow_pickle=False) as data:
        forged = {key: data[key] for key in data.files}
    forged["cell_node_tags"] = forged["cell_node_tags"].copy()
    forged["cell_node_tags"][0, 0] = forged["node_tags"].max() + 1
    forged_path = args.output / "private-forged-missing-tag.npz"
    np.savez_compressed(forged_path, **forged)
    rejected = inspect(forged_path)
    assert not rejected["all_references_resolve"] and rejected["tetrahedra"]["missing_references"] == 1
    actual = inspect(args.raw)
    record = {"source_sha256": sha(Path(__file__)), "raw_sha256": sha(args.raw),
              "control_sha256": sha(args.control), "controls": {"valid_cube": True, "missing_tag_detected": True},
              "actual": actual, "coordinates_inferred_or_modified": False,
              "orientation_claimed_for_unresolved_cells": False,
              "physics_admitted": False, "manufacturing_qualified": False}
    (args.output / "report.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record), flush=True)


if __name__ == "__main__":
    main()
