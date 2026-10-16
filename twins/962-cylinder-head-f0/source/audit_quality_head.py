"""Read actual original/proposed arrays; quality improvement is not mesh admission."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import time

import numpy as np

from audit_quality_patch import assess_native_report, require_quality_objective

ROOT = Path(__file__).resolve().parents[3]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    with path.open("rb") as stream:
        header = stream.read(24)
    if len(header) != 24 or header[:8] != b"962SURF1":
        raise ValueError("Complete binary indexed surface required")
    nv, nf = struct.unpack_from("<QQ", header, 8)
    if not nv or not nf or path.stat().st_size != 24+24*(nv+nf):
        raise ValueError("Complete surface payload and counts required")
    p = np.memmap(path, mode="r", dtype="<f8", offset=24, shape=(nv, 3))
    f = np.memmap(path, mode="r", dtype="<u8", offset=24+24*nv, shape=(nf, 3))
    if not np.isfinite(p).all() or f.max() >= nv:
        raise ValueError("Finite valid coordinate/index arrays required")
    return p, f


def qualities(p, f):
    values = np.empty(len(f))
    for start in range(0, len(f), 65536):
        xyz = p[f[start:start+65536]]; u = xyz[:, 1]-xyz[:, 0]; v = xyz[:, 2]-xyz[:, 0]
        cross = np.cross(u, v)
        sq = lambda x: np.einsum("ij,ij->i", x, x)
        values[start:start+len(xyz)] = 2*np.sqrt(3)*np.sqrt(sq(cross))/(sq(u)+sq(v)+sq(v-u))
    if not np.isfinite(values).all() or np.any(values <= 0):
        raise ValueError("All proposed triangles must remain finite and nondegenerate")
    return values


def canonical_faces(f):
    rows = np.asarray(f).copy()
    shifts = np.argmin(rows, axis=1)
    return np.take_along_axis(rows, (np.arange(3)[None, :]+shifts[:, None]) % 3, axis=1)


def audit(directory):
    contract = json.loads((directory/"frozen-execution-contract.json").read_text())
    pins = contract["input_hashes"]
    if not all(digest(ROOT/p) == h for p, h in pins.items()):
        raise ValueError("Frozen head-pass dependencies changed")
    original = ROOT/contract["original_indexed_input"]
    proposed = directory/"native/proposed-surface.bin"
    native = json.loads((directory/"native/report.json").read_text())
    execution = json.loads((directory/"execution-receipt.json").read_text())
    if execution["deadline_exceeded"] or execution["container_state"].get("Running") or execution["container_state"].get("OOMKilled"):
        raise ValueError("A stopped, complete, non-OOM native proposal is required")
    for name, expected in execution["output_sha256"].items():
        if digest(directory/name) != expected:
            raise ValueError("Native proposal/output receipt drift")
    before_hash, after_hash = digest(original), digest(proposed)
    p, f = read(original); q, g = read(proposed)
    if p.shape != q.shape or f.shape != g.shape:
        raise ValueError("No vertex/face-count change permitted")
    before_q, after_q = qualities(p, f), qualities(q, g)
    metrics = lambda a: dict(triangles=len(a), below_necessary_bound=int((a < 2/29).sum()),
                            minimum_triangle_SICN=float(a.min()))
    before, after = metrics(before_q), metrics(after_q)
    seeds = np.unique(f[before_q < 2/29])
    patch = np.any(np.isin(f, seeds), axis=1)
    exterior_nodes = np.unique(f[~patch])
    fixed = np.zeros(len(p), dtype=bool); fixed[exterior_nodes] = True
    fixed |= (p[:, 0] == -76) | (p[:, 0] == 76)
    fixed_equal = bool(np.array_equal(p[fixed], q[fixed]))
    outside_equal = True
    for start in range(0, len(f), 65536):
        stop = min(start+65536, len(f)); mask = ~patch[start:stop]
        if not np.array_equal(canonical_faces(f[start:stop][mask]), canonical_faces(g[start:stop][mask])):
            outside_equal = False
    independent_improvement = require_quality_objective(before, after)
    native_guard = assess_native_report(native)
    agrees = native_guard["quality_objective_passed"] == independent_improvement
    passed = independent_improvement and fixed_equal and outside_equal and agrees
    result = dict(status="full_array_quality_improvement_only_all_geometric_gates_pending" if passed else "full_array_quality_pass_rejected_original_preserved",
                  original_sha256=before_hash, proposed_sha256=after_hash,
                  full_surface_before=before, full_surface_after=after,
                  full_arrays_inspected=True, all_fixed_source_coordinates_exact=fixed_equal,
                  all_exterior_oriented_source_faces_exact=outside_equal,
                  independent_bad_seed_faces=before["below_necessary_bound"],
                  independent_seed_vertices=len(seeds), independent_patch_faces=int(patch.sum()),
                  independent_fixed_vertices=int(fixed.sum()),
                  native_and_independent_objective_agree=agrees, quality_objective_passed=passed,
                  source_and_proposal_unchanged=digest(original) == before_hash and digest(proposed) == after_hash,
                  runtime=dict(numpy=np.__version__), assessor_sha256=digest(Path(__file__)),
                  independent_distance_completed=False, independent_intersections_completed=False,
                  feature_channel_BCC_review_completed=False, solver_admission_established=False,
                  engineering_accepted=False, manufacturing_authorized=False)
    if not result["source_and_proposal_unchanged"]:
        raise ValueError("A bound array changed during assessment")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path); parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(); start = time.monotonic()
    if args.report.exists() or args.report.is_symlink():
        raise ValueError("Existing assessment preserved")
    result = audit(args.directory); result["wall_seconds"] = time.monotonic()-start
    with args.report.open("x") as stream:
        json.dump(result, stream, indent=2); stream.write("\n")
    print(json.dumps(result, indent=2))
