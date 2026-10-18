"""Exact shared-face cancellation and one directed continuous CUB query.

Shared source faces may be omitted only because an identical target face
remains in the COMPLETE opposite target. This is not a symmetric fragment
comparison, a point sample, or an engineering/mesh-admission certificate.
"""
import argparse
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import platform
import sys
import time

import numpy as np

from audit_quality_head import digest, read

ROOT = Path(__file__).resolve().parents[3]
WHOLEBODY = ROOT/"twins/m64-cylinder-head/source/wholebody"


def save(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write("\n")


def coordinate_faces(points, faces):
    """Exact finite binary64 coordinates, cyclic orientation, signed-zero neutral."""
    xyz = np.asarray(points[faces], dtype="<f8").copy()
    if (not np.isfinite(xyz).all() or
            not (np.linalg.norm(np.cross(xyz[:, 1]-xyz[:, 0],
                                        xyz[:, 2]-xyz[:, 0]), axis=1) > 0).all()):
        raise ValueError("Finite nondegenerate triangles required")
    xyz[xyz == 0] = 0.0
    first = np.lexsort((xyz[:, :, 2], xyz[:, :, 1], xyz[:, :, 0]), axis=1)[:, 0]
    order = (first[:, None]+np.arange(3)[None, :]) % 3
    return np.take_along_axis(xyz, order[:, :, None], axis=1)


def shared_faces(p, f, q, g):
    """Pairwise cancellation is conservative; no approximate/global matching."""
    if f.shape != g.shape:
        raise ValueError("Corresponding face counts required for this reduction")
    shared = np.zeros(len(f), dtype=bool)
    covered = hashlib.sha256()
    for start in range(0, len(f), 65536):
        stop = min(start+65536, len(f))
        a, b = coordinate_faces(p, f[start:stop]), coordinate_faces(q, g[start:stop])
        same = np.all(a == b, axis=(1, 2))
        shared[start:stop] = same
        covered.update(a[same].tobytes())
    return shared, covered.hexdigest()


def partition(original, candidate, output):
    if output.exists() or output.is_symlink():
        raise ValueError("Existing partition evidence preserved")
    before = {str(path): digest(path) for path in (original, candidate)}
    p, f = read(original); q, g = read(candidate)
    shared, covered_sha = shared_faces(p, f, q, g)
    changed = np.flatnonzero(~shared).astype("<u8")
    output.mkdir(parents=True, exist_ok=False)
    with (output/"facet-partition.npz").open("xb") as stream:
        np.savez(stream, shared_face_mask=shared, changed_face_indices=changed)
    unchanged = all(digest(Path(path)) == sha for path, sha in before.items())
    report = dict(schema="962-exact-shared-face-partition/v1", input_sha256=before,
        original_vertices=len(p), candidate_vertices=len(q),
        original_faces=len(f), candidate_faces=len(g), shared_faces=int(shared.sum()),
        changed_original_faces=len(changed), changed_candidate_faces=len(changed),
        shared_oriented_coordinate_triangles_sha256=covered_sha,
        partition_sha256=digest(output/"facet-partition.npz"),
        cancelled_faces_covered_exactly_in_opposite_full_target=True,
        complete_opposite_targets_required=True, coordinate_rounding_or_tolerance_used=False,
        orientation_preserved=True, signed_zero_geometric_equivalence=True,
        proof="A=S union A_changed; B=S union B_changed; h(A,B)=max(0,h(A_changed,B)); reverse analogously. Every cancelled corresponding coordinate triangle is identical, including orientation. Unmatched shared faces can remain in the query without affecting exactness.",
        source_and_candidate_unchanged=unchanged, source_sha256=digest(Path(__file__)),
        solver_admission_established=False, engineering_accepted=False,
        manufacturing_authorized=False)
    save(output/"reduction-proof.json", report)
    if not unchanged:
        raise ValueError("Partition input changed")
    return report


def directed(p, f, q, g, tolerance=1e-4, query=None):
    """A -> COMPLETE B only. Empty A is exactly zero without a native call."""
    if isinstance(tolerance, bool) or not math.isfinite(tolerance) or tolerance <= 0:
        raise ValueError("Positive finite absolute tolerance required")
    sys.path.insert(0, str(WHOLEBODY))
    from run_bounded_chamfer import interval_ok, surface_arrays
    b, fb = surface_arrays(q, g)
    if not len(f):
        return dict(lower=0., upper=0., interval_closed=True, native_called=False,
                    source_faces=0, target_faces=len(fb), target_is_complete=True)
    a, fa = surface_arrays(p, f)
    if query is None:
        from cascading_upper_bounds import pompeiu_hausdorff
        query = pompeiu_hausdorff
    factor = max(1., min(1e6, 2000000/max(len(a), len(fa))))
    snapshots = [hashlib.sha256(x.tobytes()).hexdigest() for x in (a, fa, b, fb)]
    lower, upper, diagonal, bvh_ms, bounds_ms = map(float,
        query(a, fa, b, fb, tolerance, factor, False))
    unchanged = snapshots == [hashlib.sha256(x.tobytes()).hexdigest() for x in (a, fa, b, fb)]
    if not unchanged or not all(math.isfinite(x) for x in (diagonal, bvh_ms, bounds_ms)):
        raise ValueError("Native query arrays/timing changed or nonfinite")
    return dict(lower=lower, upper=upper, interval_closed=interval_ok(lower, upper, tolerance),
        native_called=True, source_vertices=len(a), source_faces=len(fa),
        target_vertices=len(b), target_faces=len(fb), target_is_complete=True,
        allocation_factor=factor, normalize=False, diagonal=diagonal,
        bvh_ms=bvh_ms, bounds_ms=bounds_ms, query_arrays_unchanged=unchanged)


def worker(contract_path, config_path, output):
    contract = json.loads(contract_path.read_text())
    config = json.loads(config_path.read_text())
    pins = contract["input_hashes"]
    verify = lambda: all(digest(ROOT/path) == sha for path, sha in pins.items())
    if not verify() or digest(config_path) != contract["query_config_hashes"][str(config_path.relative_to(ROOT))]:
        raise ValueError("Frozen query/source/runtime inputs required")
    import cascading_upper_bounds as cub
    import cascading_upper_bounds.cascading_upper_bounds_ext as ext
    runtime = dict(python=sys.version, executable_sha256=digest(Path(sys.executable)),
        machine=platform.machine(), numpy=np.__version__,
        cub_version=importlib.metadata.version("cascading-upper-bounds"),
        cub_module_sha256=digest(Path(cub.__file__)), cub_binary_sha256=digest(Path(ext.__file__)))
    expected = contract["runtime"]
    if any(runtime[key] != value for key, value in expected.items()):
        raise ValueError("Exact pinned native CUB runtime required")
    started = time.monotonic()
    report = dict(schema="962-directed-cub-query/v1", status="failed", runtime=runtime,
        config_sha256=digest(config_path), contract_sha256=digest(contract_path),
        assessor_sha256=digest(Path(__file__)), native_CAD_deviation_certified=False,
        rounding_error_certificate=False, solver_admission_established=False,
        engineering_accepted=False, manufacturing_authorized=False)
    try:
        p, f = read(ROOT/config["source"]); q, g = read(ROOT/config["target"])
        full_count = len(f)
        if config["partition"]:
            with np.load(ROOT/config["partition"], allow_pickle=False) as rows:
                ids = rows["changed_face_indices"]
                mask = rows["shared_face_mask"]
                if (mask.dtype != np.bool_ or mask.shape != (len(f),) or
                        not np.array_equal(ids, np.flatnonzero(~mask))):
                    raise ValueError("Complete frozen facet partition required")
                f = f[ids]
        report["distance"] = directed(p, f, q, g, contract["absolute_gap_tolerance_mm"])
        report.update(status="completed" if report["distance"]["interval_closed"] else "open_interval_rejected",
                      full_source_faces=full_count, complete_target_faces=len(g))
    except Exception as exc:
        report["error"] = type(exc).__name__+": "+str(exc)
    report.update(wall_seconds=time.monotonic()-started, all_bound_inputs_unchanged=verify())
    save(output, report)
    print(json.dumps(dict(status=report["status"], distance=report.get("distance"),
                          error=report.get("error")), allow_nan=False), flush=True)
    return 0 if report["status"] == "completed" and report["all_bound_inputs_unchanged"] else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--partition", nargs=3, type=Path, metavar=("ORIGINAL", "CANDIDATE", "OUTPUT"))
    group.add_argument("--worker", nargs=3, type=Path, metavar=("CONTRACT", "CONFIG", "REPORT"))
    args = parser.parse_args()
    if args.partition:
        print(json.dumps(partition(*args.partition), indent=2))
    else:
        raise SystemExit(worker(*args.worker))
