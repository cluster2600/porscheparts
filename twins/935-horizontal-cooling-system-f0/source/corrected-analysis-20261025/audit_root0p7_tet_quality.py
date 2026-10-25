"""Measure the shape of every audited exploratory fluid tetrahedron."""

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

EXPECTED = "bcad2182f1e78e2cc6fe2ca90ddc5c277b0e93ca35dce4ddca9082b4a60e0420"
EDGES = ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))


def mean_ratio(tetrahedra):
    a, b, c, d = np.moveaxis(tetrahedra, 1, 0)
    six_volume = np.einsum("ij,ij->i", b - a, np.cross(c - a, d - a))
    edge_sum = sum(np.einsum("ij,ij->i", tetrahedra[:, i] - tetrahedra[:, j], tetrahedra[:, i] - tetrahedra[:, j]) for i, j in EDGES)
    if np.any(six_volume <= 0) or np.any(edge_sum <= 0):
        raise ValueError("Inverted or degenerate tetrahedron")
    return 12 * (six_volume / 2) ** (2 / 3) / edge_sum


def main(volume_path, output_path):
    regular = np.array([[[0., 0., 0.], [1., 0., 0.], [.5, np.sqrt(3) / 2, 0.], [.5, np.sqrt(3) / 6, np.sqrt(2 / 3)]]])
    assert abs(mean_ratio(regular)[0] - 1) < 1e-12
    digest = hashlib.sha256(Path(volume_path).read_bytes()).hexdigest()
    if digest != EXPECTED:
        raise ValueError("Unexpected audited volume")
    with np.load(volume_path) as data:
        vertices = data["vertices"]
        cells = data["tetrahedra"]
        boundary = data["boundary"]
        markers = data["markers"]
    if len(vertices) != 817600 or len(cells) != 3727134:
        raise ValueError("Unexpected cell count")
    ratios = np.empty(len(cells), dtype=np.float64)
    for start in range(0, len(cells), 100000):
        end = min(start + 100000, len(cells))
        ratios[start:end] = mean_ratio(vertices[cells[start:end]])
    if not np.isfinite(ratios).all() or np.any(ratios > 1 + 1e-10):
        raise ValueError("Invalid mean ratio")
    weak = cells[ratios < .01]
    touches_rotor = np.isin(weak, np.unique(boundary[markers == 4])).any(axis=1)
    touches_outer = np.isin(weak, np.unique(boundary[markers != 4])).any(axis=1)
    report = {
        "status": "complete_exploratory_tetra_shape_audit",
        "volume_npz_sha256": digest,
        "tetrahedra": len(cells),
        "mean_ratio_definition": "12*(3*volume)**(2/3)/sum(six_squared_edge_lengths)",
        "mean_ratio_min": float(ratios.min()),
        "mean_ratio_p01": float(np.quantile(ratios, .01)),
        "mean_ratio_median": float(np.median(ratios)),
        "mean_ratio_p99": float(np.quantile(ratios, .99)),
        "mean_ratio_lt_0p01": int(np.count_nonzero(ratios < .01)),
        "mean_ratio_lt_0p05": int(np.count_nonzero(ratios < .05)),
        "mean_ratio_lt_0p1": int(np.count_nonzero(ratios < .1)),
        "weak_lt_0p01_touch_rotor": int(touches_rotor.sum()),
        "weak_lt_0p01_touch_outer": int(touches_outer.sum()),
        "weak_lt_0p01_touch_both": int((touches_rotor & touches_outer).sum()),
        "weak_lt_0p01_touch_no_boundary": int((~(touches_rotor | touches_outer)).sum()),
        "CFD_quality_admitted": False,
        "CFD_accepted": False,
    }
    Path(output_path).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: audit_root0p7_tet_quality.py AUDITED_VOLUME_NPZ NEW_REPORT_JSON")
    main(sys.argv[1], sys.argv[2])
