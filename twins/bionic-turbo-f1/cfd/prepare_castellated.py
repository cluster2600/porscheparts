#!/usr/bin/env python3
"""Prepare a diagnostic staircase mesh without altering the frozen F1 recipe."""
import argparse
import json
from pathlib import Path

import prepare_case


def prepare(surface, output):
    manifest = prepare_case.prepare(surface, output, "medium", 100000, 1, 1.2, 800)
    name = "system/snappyHexMeshDict"
    path = output / name
    content = path.read_text()
    if content.count("snap true;") != 1:
        raise ValueError("Expected exactly one snapping switch")
    path.write_text(content.replace("snap true;", "snap false;"))
    manifest["file_sha256"][name] = prepare_case.sha(path)
    manifest["diagnostic_recipe"] = {
        "name": "castellated-medium-gap-v1",
        "source_sha256": prepare_case.sha(Path(__file__)),
        "snapping": False,
        "surface_distance_error_quantified": False,
        "performance_ranking_authorized": False,
    }
    manifest["limitations"].append(
        "Staircase boundary: diagnostic only; surface displacement, roughness and gap errors are unquantified."
    )
    (output / "case-manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("surface", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    prepare(args.surface, args.output)
    print(json.dumps({"status": "prepared_diagnostic_only", "output": str(args.output)}))
