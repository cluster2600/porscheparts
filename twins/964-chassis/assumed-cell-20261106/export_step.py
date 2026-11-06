"""Export the authored assumed plate-box union directly to STEP, independently of PicoGK."""
from pathlib import Path
import argparse
import hashlib
import itertools
import json
import math
import time

import build123d as cad


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def valid(shape):
    return shape.is_valid() if callable(shape.is_valid) else shape.is_valid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Use a fresh output directory")
    started = time.monotonic()
    source_hash = sha(args.model)
    model = json.loads(args.model.read_text())
    thickness = model["thickness_mm"]
    if (model["units"] != "mm" or model["status"] != "assumed"
            or not math.isfinite(thickness) or not 0 < thickness <= 10):
        raise ValueError("Expected assumed millimetre model with positive thickness <=10 mm")
    boxes = model["plate_boxes"]
    panels = {row["name"]: row for row in model["panels"]}
    if not 0 < len(boxes) <= 100 or len(panels) != len(boxes):
        raise ValueError("Expected 1..100 uniquely named panel/box pairs")
    for box in boxes:
        panel = panels[box["name"]]
        normal, u, v = (panel[k] for k in ("normal_axis", "u_axis", "v_axis"))
        if normal not in (0, 1, 2) or u != (normal + 1) % 3 or v != (normal + 2) % 3:
            raise ValueError("Invalid panel-axis convention")
        lo, hi = [None] * 3, [None] * 3
        lo[normal], hi[normal] = panel["at_mm"] - thickness / 2, panel["at_mm"] + thickness / 2
        lo[u], hi[u] = panel["u_mm"]
        lo[v], hi[v] = panel["v_mm"]
        if (lo != box["min_mm"] or hi != box["max_mm"]
                or any(not math.isfinite(x) or abs(x) > 10000 for x in lo + hi)
                or any(a >= b for a, b in zip(lo, hi))):
            raise ValueError("Plate boxes must be literal +/-t/2 extrusions of the midplanes")
    cuts = [sorted({box[k][a] for box in boxes for k in ("min_mm", "max_mm")})
            for a in range(3)]
    intervals = [list(zip(axis, axis[1:])) for axis in cuts]
    reference_volume = 0.0
    for cell in itertools.product(*intervals):
        middle = [(a + b) / 2 for a, b in cell]
        if any(all(lo < x < hi for x, lo, hi in
                   zip(middle, box["min_mm"], box["max_mm"])) for box in boxes):
            reference_volume += math.prod(b - a for a, b in cell)
    primitives = [cad.Box(*(hi - lo for lo, hi in zip(box["min_mm"], box["max_mm"])),
                          align=(cad.Align.MIN,) * 3).located(cad.Location(box["min_mm"]))
                  for box in boxes]
    union = primitives[0].fuse(*primitives[1:])
    args.output.mkdir(parents=True, mode=0o700)
    step = args.output / "assumed-cell.step"
    cad.export_step(union, str(step))
    restored = cad.import_step(str(step))
    if (not valid(union) or not valid(restored)
            or len(union.solids()) != 1 or len(restored.solids()) != 1
            or abs(union.volume - reference_volume) > 0.01
            or abs(restored.volume - union.volume) > 0.01):
        raise ValueError("STEP union or roundtrip failed validity/solid/volume checks")
    bbox = union.bounding_box()
    expected_min, expected_max = [a[0] for a in cuts], [a[-1] for a in cuts]
    if any(abs(a - b) > 1e-6 for a, b in
           zip(list(bbox.min) + list(bbox.max), expected_min + expected_max)):
        raise ValueError("Union bounds differ from the literal plate boxes")
    if sha(args.model) != source_hash:
        raise ValueError("Source model changed during export")
    report = {
        "classification": "exact_authored_assumed_plate_union_STEP_not_vehicle_fitment",
        "source_model_sha256": source_hash, "exporter_sha256": sha(__file__),
        "physical_thickness_mm": thickness, "literal_plate_boxes": len(boxes),
        "exact_box_union_reference_mm3": reference_volume,
        "occt_union_volume_mm3": union.volume, "roundtrip_volume_mm3": restored.volume,
        "valid_before_and_after": True, "solid_count_before_and_after": 1,
        "bounds_min_mm": list(bbox.min), "bounds_max_mm": list(bbox.max),
        "step_sha256": sha(step), "step_bytes": step.stat().st_size,
        "build123d_version": cad.__version__, "elapsed_seconds": time.monotonic() - started,
        "PicoGK_mesh_or_voxel_conversion_used": False,
        "donor_fitment_verified": False, "strength_verified": False,
        "manufacturing_authorized": False,
    }
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
