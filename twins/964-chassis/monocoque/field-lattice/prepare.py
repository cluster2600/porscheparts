"""Map retained F0 integration-point demand to sparse, explicitly located samples."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "source"))
from strength_audit import read_dat  # noqa: E402

PITCH_MM = 0.5


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def von_mises(stress):
    s = np.asarray(stress, dtype=float)
    if s.ndim != 2 or s.shape[1] != 6 or not np.isfinite(s).all():
        raise ValueError("Expected finite global Sxx,Syy,Szz,Sxy,Sxz,Syz")
    a, b, c, d, e, f = s.T
    return np.sqrt(((a-b)**2 + (b-c)**2 + (c-a)**2)/2 + 3*(d*d+e*e+f*f))


def aggregate(coords, values):
    coords, values = np.asarray(coords, float), np.asarray(values, float)
    if (coords.ndim != 2 or coords.shape[1] != 3 or not len(coords)
            or values.shape != (len(coords), 2) or not np.isfinite(coords).all()
            or not np.isfinite(values).all() or (values < 0).any()
            or np.abs(coords).max() > 5000):
        raise ValueError("Invalid mm / MPa samples")
    # shortcut: point-bin maxima, not interpolation; retain tensors for ply analysis.
    snapped = np.floor(coords / PITCH_MM + 0.5).astype(np.int64)
    cells, inverse, counts = np.unique(snapped, axis=0, return_inverse=True, return_counts=True)
    maxima = np.zeros((len(cells), 2))
    np.maximum.at(maxima, inverse, values)
    rows = np.column_stack((cells * PITCH_MM, maxima.astype(np.float32), counts))
    error = np.linalg.norm(coords - snapped * PITCH_MM, axis=1)
    return rows, float(error.max())


def prepare(run_dir, output):
    receipt_path = HERE.parent / "derived/strength-audit-20261012.json"
    receipt = json.loads(receipt_path.read_text())
    if not receipt["numerical_checks_passed"] or receipt["runtime"]["threads"] != 1:
        raise ValueError("Only the accepted serial audit is admitted")
    for name, expected in receipt["source_sha256"].items():
        if digest(HERE.parent / name) != expected:
            raise ValueError(f"Source changed: {name}")
    fields, hashes, coords, ids = [], {}, None, None
    for name in ("torsion_+1", "bending_+1"):
        path = Path(run_dir) / name / "shell.dat"
        hashes[name] = digest(path)
        if hashes[name] != receipt["runs"][name]["files_sha256"]["shell.dat"]:
            raise ValueError(f"Unverified solver output: {name}")
        data = read_dat(path)
        keys = sorted(data["coord"])
        xyz = np.array([data["coord"][key] for key in keys])
        if coords is not None and (keys != ids or not np.array_equal(coords, xyz)):
            raise ValueError("Load cases have different integration-point locations")
        coords, ids = xyz, keys
        fields.append(von_mises([data["stress"][key] for key in keys]))
    rows, error = aggregate(coords, np.array(fields).T)
    payload = {"schema_version": 1, "voxel_mm": PITCH_MM,
               "frame": "F0_GLOBAL_X_forward_Y_left_Z_up", "value_unit": "MPa",
               "rows": rows.tolist()}
    Path(output).mkdir(parents=True, exist_ok=False)
    samples = Path(output) / "samples.json"
    samples.write_text(json.dumps(payload, separators=(",", ":"), allow_nan=False) + "\n")
    report = {"source_receipt_sha256": digest(receipt_path), "input_dat_sha256": hashes,
              "integration_points_per_case": len(coords), "active_sample_bins": len(rows),
              "voxel_mm": PITCH_MM, "position_error_max_mm": error,
              "position_error_bound_mm": float(np.sqrt(3)*PITCH_MM/2),
              "peak_float32_error_max_MPa": float(np.max(np.abs(rows[:, 3:5].max(axis=0)
                                                                         - np.max(fields, axis=1)))),
              "source_peak_MPa": [float(np.max(v)) for v in fields],
              "mapped_peak_MPa": rows[:, 3:5].max(axis=0).tolist(),
              "samples_sha256": digest(samples), "aggregation": "maximum per occupied bin per load case",
              "interpolation": "none; inactive is unknown, not zero stress",
              "failure_criterion": None, "product_strength_validated": False}
    (Path(output) / "mapping.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.run_dir, args.output), indent=2))
