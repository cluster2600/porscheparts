#!/usr/bin/env python3
"""Slice the impeller flat and run the unchanged thermal solver for comparison."""
import argparse
import csv
import json
import math
from pathlib import Path
import runpy

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(__file__).parent


def run(output):
    solver = runpy.run_path(str(SOURCE / "simulate_lpbf_thermal.py"))
    card = json.loads(solver["CARD"].read_text())
    original = json.loads((ROOT / card["geometry_report"]).read_text())
    surface = ROOT / card["surface"]
    if solver["sha"](surface) != original["analysis_surface"]["sha256"]:
        raise ValueError("Flat comparison surface differs from the admitted CAD")
    mesh = solver["KERNEL"].orient(trimesh.load_mesh(surface, process=True), "build_z")
    layer = card["process"]["layer_mm"]
    height = float(mesh.extents[2])
    count = math.ceil(height / layer)
    heights = [(i * layer + min((i + 1) * layer, height)) / 2 for i in range(count)]
    paths = mesh.section_multiplane(np.zeros(3), [0., 0., 1.], heights)
    rows = [{"layer_index": i, "z_mm": round(z, 8),
             "part_area_mm2": float(solver["KERNEL"].path_to_polygon(path).area)}
            for i, (z, path) in enumerate(zip(heights, paths))]
    volume = sum(row["part_area_mm2"] * min(layer, height - i * layer) for i, row in enumerate(rows))
    if len(rows) != count or any(not math.isfinite(row["part_area_mm2"]) or row["part_area_mm2"] <= 0 for row in rows):
        raise ValueError("Flat slice schedule is incomplete")
    if abs(volume / mesh.volume - 1) > .001:
        raise ValueError("Flat sliced volume differs from CAD by more than 0.1 percent")
    inputs = output / "inputs"
    inputs.relative_to(ROOT)
    inputs.mkdir(parents=True, exist_ok=False)
    with (inputs / "layers.csv").open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    report = {"classification": "flat_area_slices_for_thermal_comparison_not_support_design",
              "analysis_surface": original["analysis_surface"], "selected_candidate_orientation": "build_z",
              "source_sha256": solver["sha"](Path(__file__)),
              "full_build_slicing": {"layer_thickness_mm": layer, "layer_count": count,
                                     "build_height_mm": height, "sliced_volume_mm3": volume},
              "manufacturing_authorized": False}
    solver["write"](inputs / "geometry.json", report)
    card["geometry_report"] = (inputs / "geometry.json").relative_to(ROOT).as_posix()
    card["layers"] = (inputs / "layers.csv").relative_to(ROOT).as_posix()
    solver["write"](inputs / "study.json", card)
    # Bind only the input card; keep the already executed thermal kernel unchanged.
    solver["run"].__globals__["CARD"] = inputs / "study.json"
    solver["run"](output / "p2-s8", 2., .35, 8)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args().output.resolve())
