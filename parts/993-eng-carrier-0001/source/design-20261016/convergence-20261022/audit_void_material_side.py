"""Audit a negative volume with the orientation of its surrounding material."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np


def audit_material_side(vertices, triangles):
    source = Path(__file__).with_name("audit_surface_features.py")
    spec = importlib.util.spec_from_file_location("frozen_surface_feature_auditor", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.audit(vertices, np.asarray(triangles)[:, [0, 2, 1]])
    result.update(
        input_face_orientation_reversed=True,
        reported_orientation="Material side of the void boundary; outward from surrounding material into cavity",
        complete_material_assembly=False,
        feature_auditor_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        scope="Oriented cavity-boundary diagnostic only; not a complete carrier or a mechanical-admission result",
    )
    return result


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    digest = hashlib.sha256(args.input.read_bytes()).hexdigest()
    if digest != args.sha256 or args.output.exists():
        raise ValueError("Frozen input hash and fresh output required")
    with np.load(args.input, allow_pickle=False) as data:
        result = audit_material_side(data["vertices"], data["triangles"])
    result.update(input_sha256=digest,
                  source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  numpy_version=np.__version__, manufacturing_authorized=False)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps({k: v for k, v in result.items() if k != "most_reentrant_edges"}))


if __name__ == "__main__":
    main()
