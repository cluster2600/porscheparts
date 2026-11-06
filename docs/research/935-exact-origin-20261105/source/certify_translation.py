"""Prove an exact -10 coordinate-origin change without modifying the source.

The bounded positive binary64 range permits an integer-lattice comparison.
This is a frame-invariance diagnostic, not a conditioning improvement.
"""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import time

import numpy as np


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def exact_translation(source, translated):
    assert source.dtype == translated.dtype == np.dtype(np.float64)
    assert source.shape == translated.shape
    assert np.all(np.isfinite(source)) and np.all(np.isfinite(translated))
    assert np.all(source >= 10.) and np.all(source < 256.)
    assert np.asarray([1.], dtype=np.float64).view(np.uint64)[0] == 0x3ff0000000000000
    bits = source.view(np.uint64)
    exponent = ((bits >> 52) & 0x7ff).astype(np.int64) - 1075
    assert np.all(exponent >= -49) and np.all(exponent <= -45)
    mantissa = (bits & ((1 << 52) - 1)) | (1 << 52)
    offset = np.left_shift(np.uint64(10), (-exponent).astype(np.uint64))
    assert np.all(mantissa >= offset)
    exact_integer = mantissa - offset
    assert np.all(exact_integer < (1 << 53))
    # Scaling by a power of two is exact in this finite normal-data range.
    # Compare floating values, rather than truncating a possibly fractional
    # scaled value to an integer, which could conceal a corrupted coordinate.
    scaled = np.ldexp(translated, (-exponent).astype(np.int32))
    return bool(np.array_equal(scaled, exact_integer.astype(np.float64)))


def controls():
    source = np.array([[10., np.nextafter(10., np.inf), 20.1],
                       [np.nextafter(100., np.inf), 234.16, 255.999]])
    translated = source - 10.
    assert exact_translation(source, translated)
    for old, new in zip(source.flat, translated.flat):
        assert Fraction(float(old)) - 10 == Fraction(float(new))
    corrupt = translated.copy()
    corrupt[0, 2] = np.nextafter(corrupt[0, 2], np.inf)
    assert not exact_translation(source, corrupt)
    # An arbitrary different origin can lose source bits; it is not presumed
    # admissible merely because it is a rigid transform over the real numbers.
    old = np.nextafter(10., np.inf)
    assert Fraction(float(old - 128.)) != Fraction(float(old)) - 128
    return {"independent_fraction_controls_passed": True,
            "single_bit_coordinate_corruption_rejected": True,
            "different_origin_precision_loss_witness": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesh", type=Path, required=True)
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert sha(args.mesh) == "233f7bd83072772fa0b92d0287f20cec3cf44c4988546be42addf5579630299e"
    assert sha(args.parent / "manifest.json") == "91fbc0ecc6dfdeb2b95949676698f0ea9a1a8605d783efdfa61e2fe3722ed64d"
    parent_manifest = {row["path"]: row["sha256"] for row in json.loads((args.parent / "manifest.json").read_text())["files"]}
    witness_path = args.parent / "independent-foam/report.json"
    assert sha(witness_path) == parent_manifest["independent-foam/report.json"]
    witness = json.loads(witness_path.read_text())
    assert witness["reference_sha256"] == sha(args.mesh) and witness["head"]["all_coordinates_exact"]
    original_points = args.parent / "cloud-import-001/recovered/head/constant/polyMesh/points"
    assert sha(original_points) == witness["native_file_sha256"]["points"]
    tested = controls()
    args.output.mkdir(mode=0o700, exist_ok=False)
    started = time.monotonic()
    with np.load(args.mesh, allow_pickle=False) as data:
        nodes = data["nodes"]
    assert nodes.shape == (4181299, 3)
    translated = nodes - 10.
    assert exact_translation(nodes, translated), "Exact geometry-preserving shift refused"
    assert np.array_equal(translated + 10., nodes)
    archive = args.output / "expected-translated-points.npz"
    np.savez_compressed(archive, nodes=translated)
    with np.load(archive, allow_pickle=False) as recovered:
        assert np.array_equal(recovered["nodes"], translated)
    result = {"source_sha256": sha(Path(__file__)), "source_volume_sha256": sha(args.mesh),
        "native_original_points_sha256": sha(original_points),
        "controls": tested, "points": len(nodes), "coordinates_checked": int(nodes.size),
        "source_bounds": [nodes.min(axis=0).tolist(), nodes.max(axis=0).tolist()],
        "translated_bounds": [translated.min(axis=0).tolist(), translated.max(axis=0).tolist()],
        "integer_lattice_comparison_passed_for_every_coordinate": True,
        "inverse_coordinate_roundtrip_bit_exact": True,
        "method": "Decode x=m*2^e; compare (x-10)*2^-e to the exact integer m-10*2^-e, below 2^53",
        "source_to_trial_frame": [[1, 0, 0, -10], [0, 1, 0, -10], [0, 0, 1, -10], [0, 0, 0, 1]],
        "exact_geometry_deviation_after_inverse_transform": 0,
        "intrinsic_edge_matrix_conditioning_unchanged": True,
        "uncoupled_stencil_rank_unchanged": True,
        "source_mesh_modified": False, "printing_master_replaced": False,
        "expected_translated_points_sha256": sha(archive),
        "native_io_and_geometry_trial_executed_by_this_script": False,
        "field_solve_executed": False, "physics_admitted": False,
        "manufacturing_qualified": False, "new_paid_compute_usd": 0,
        "seconds": time.monotonic() - started}
    (args.output / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
