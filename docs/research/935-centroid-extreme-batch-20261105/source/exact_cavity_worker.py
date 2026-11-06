#!/usr/bin/env python3
"""Dependency-free, bounded parallel exact cavity proposals; no field solver.

Only compact, pre-audited private cavity inputs are read. Every source, source
case and binary64 coordinate digest is checked. A literal analytic control and
an independently verified head benchmark precede the queue. No network client,
credential, shell command, model service or acquired full scan is needed.
"""
import argparse
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import math
import multiprocessing as mp
import os
from pathlib import Path
import resource
import re
import shutil
import signal
import struct
import sys
import time

THRESHOLDS = (1000, 10**6, 10**9, 10**12, 10**15, 2**52, 10**16, 3*2**52)
LABELS = ("1e3", "1e6", "1e9", "1e12", "1e15", "eps_inverse", "1e16", "3_eps_inverse")
GEOMETRY_SHA = "c06c37065561813a27791a4096d41c9e221f83ba48e775b2de6489f1f5a84a07"
CONTRACT_SHA = "0983f355f6983a3d5611144362871f404e969bd5f11e6ad7889a0fce35b054bb"
SOURCE_MESH_SHA = "1bc2e8dddaf07c43ca36d35608f4fdb508f22e0694e922108a96466887f6182d"


def sha(path):
    with open(path, "rb") as stream:
        digest = hashlib.sha256()
        for block in iter(lambda: stream.read(1024*1024), b""):
            digest.update(block)
        return digest.hexdigest()


def save(path, value):
    with open(path, "x", encoding="utf-8") as stream:
        json.dump(value, stream, separators=(",", ":"), allow_nan=False)
        stream.write("\n")


def load(path, name, expected):
    assert sha(path) == expected
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def coordinate_digest(nodes):
    return hashlib.sha256(b"".join(struct.pack("<3d", *row) for row in nodes)).hexdigest()


def cell_digest(cells):
    return hashlib.sha256(b"".join(struct.pack("<4I", *row) for row in cells)).hexdigest()


def reciprocal_condition(tet, points, geometry):
    p = [points[int(i)] for i in tet]
    a, b, c = (geometry.sub(p[i], p[0]) for i in (1, 2, 3))
    d = geometry.dot(a, geometry.cross(b, c)); assert d > 0
    norm = sum(geometry.dot(v, v) for v in (a, b, c))
    adj = [geometry.cross(b, c), geometry.cross(c, a), geometry.cross(a, b)]
    product = norm*sum(geometry.dot(v, v) for v in adj)
    assert product >= 9*d*d
    return Q(d*d, product)


def condition_counts(nodes, cells, geometry):
    points, _ = geometry.exact_points(nodes, sorted({i for tet in cells for i in tet}))
    reciprocal = [reciprocal_condition(tet, points, geometry) for tet in cells]
    return [sum(r*t*t <= 1 for r in reciprocal) for t in THRESHOLDS]


def compute_case(arguments):
    root_string, relative = arguments
    root = Path(root_string); started = time.monotonic()
    case_path = root/relative
    case = json.loads(case_path.read_text())
    result = {"case_id": case["case_id"], "input_sha256": sha(case_path), "admitted": False,
        "source_mesh_sha256": case["source_mesh_sha256"], "physics_admitted": False, "manufacturing_qualified": False}
    try:
        assert case["schema"] == "935-exact-cavity-input-1"
        assert re.fullmatch(r"(?:case-[0-9]{4}|control)", case["case_id"])
        assert case["source_mesh_sha256"] in (SOURCE_MESH_SHA, "synthetic-control")
        nodes, old = case["nodes"], case["old_cells"]
        assert 1 <= len(old) <= 96 and 4 <= len(nodes) <= 196
        assert coordinate_digest(nodes) == case["coordinates_f64_sha256"]
        assert cell_digest(old) == case["cells_u32_sha256"]
        assert all(len(row) == 3 and all(math.isfinite(x) for x in row) for row in nodes)
        assert all(len(tet) == 4 and all(type(i) is int and 0 <= i < len(nodes) for i in tet) for tet in old)
        geometry = load(root/"geometry_primitives.py", "worker_exact_geometry", GEOMETRY_SHA)
        contract = load(root/"centroid_contract.py", "worker_centroid_contract", CONTRACT_SHA)
        faces, ideal = contract.volume_centroid(nodes, old, geometry)
        assert len(faces) <= 196
        point = [float(value) for value in ideal]
        augmented = nodes+[point]
        new = [[len(nodes), *face] for face in faces]
        proof = contract.certify(augmented, old, new, geometry)
        before = condition_counts(nodes, old, geometry); after = condition_counts(augmented, new, geometry)
        assert all(a >= b for a, b in zip(before, after)), "A fixed exact condition threshold worsens"
        result.update(admitted=True, verdict="exact_local_partition_passed_pending_global_independent_verification",
            old_cells=len(old), new_cells=new, new_point_hex=[value.hex() for value in point],
            ideal_centroid=[[str(value.numerator), str(value.denominator)] for value in ideal],
            exact_domain_volume=[str(proof["exact_domain_volume"].numerator), str(proof["exact_domain_volume"].denominator)],
            old_bins=proof["old_bins"], new_bins=proof["new_bins"],
            old_condition_counts=dict(zip(LABELS, before)), new_condition_counts=dict(zip(LABELS, after)),
            new_minimum_quality_approx=float(proof["new_minimum_quality_cubed"])**(1/3),
            old_pair_separations=proof["old_pair_separations"], new_pair_separations=proof["new_pair_separations"],
            new_points=1, unchanged_complete_boundary=True, all_original_points_retained=True,
            source_module_sha256={"geometry": GEOMETRY_SHA, "contract": CONTRACT_SHA})
    except AssertionError as error:
        result.update(verdict="candidate_refused", reason=str(error) or "source_shape_contract")
    except Exception as error:
        result.update(verdict="unexpected_worker_error", error_type=type(error).__name__)
    result["seconds"] = time.monotonic()-started
    return result


def initialize_worker():
    signal.signal(signal.SIGTERM, signal.SIG_DFL)
    resource.setrlimit(resource.RLIMIT_AS, (2*1024**3, 2*1024**3))


def check_control(root, job):
    geometry = load(root/"geometry_primitives.py", "worker_identity_geometry", GEOMETRY_SHA)
    nodes = [[0., 0., 0.], [1., 0., 0.], [0., 1., 0.], [0., 0., 1.]]
    points, _ = geometry.exact_points(nodes, range(4))
    assert reciprocal_condition([0, 1, 2, 3], points, geometry) == Q(1, 9)
    result = compute_case((str(root), job["control_case"]))
    assert result["admitted"] and result["exact_domain_volume"] == ["7", "6"]
    expected_y = float(Q(27, 56)+Q(1, 1 << 26)).hex()
    assert result["new_point_hex"] == [float(0).hex(), expected_y, float(0).hex()]
    assert len(result["new_cells"]) == 12 and result["old_bins"][0] == 2 and result["new_bins"][0] == 0
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--case")
    args = parser.parse_args(); root = args.job.parent.resolve(); original_job_sha = sha(args.job)
    job = json.loads(args.job.read_text())
    assert job["schema"] == "935-exact-cavity-job-1" and job["source_mesh_sha256"] == SOURCE_MESH_SHA
    assert 1 <= args.workers <= 8 and struct.calcsize("d") == 8 and sys.float_info.mant_dig == 53
    assert 0 < len(job["cases"]) <= 256
    paths = [row["path"] for row in job["files"]]
    assert len(paths) == len(set(paths))
    for row in job["files"]:
        path = root/row["path"]
        assert path.resolve().is_relative_to(root) and not path.is_symlink() and sha(path) == row["sha256"]
    args.output.mkdir(mode=0o700, exist_ok=False)
    assert shutil.disk_usage(args.output).free >= 4*1024**3
    started = time.monotonic()
    def deadline(signum, frame):
        raise TimeoutError("Worker global deadline")
    signal.signal(signal.SIGALRM, deadline); signal.alarm(600)
    pool = None; complete = False; results = []
    try:
        control = check_control(root, job); save(args.output/"control.json", control)
        benchmark = compute_case((str(root), job["benchmark_case"]))
        expected = job["benchmark_expected"]
        assert benchmark["admitted"] and benchmark["new_point_hex"] == expected["new_point_hex"]
        assert cell_digest(benchmark["new_cells"]) == expected["new_cells_u32_sha256"]
        assert benchmark["old_bins"] == expected["old_bins"] and benchmark["new_bins"] == expected["new_bins"]
        save(args.output/"benchmark.json", benchmark)
        cases = [row for row in job["cases"] if args.case is None or row["case_id"] == args.case]
        assert cases and (args.case is None or len(cases) == 1)
        work = [(str(root), row["path"]) for row in cases]
        if args.workers == 1:
            iterator = map(compute_case, work)
        else:
            pool = mp.get_context("spawn").Pool(args.workers, initializer=initialize_worker)
            iterator = pool.imap_unordered(compute_case, work, chunksize=1)
        for result in iterator:
            assert shutil.disk_usage(args.output).free >= 4*1024**3
            assert result["verdict"] != "unexpected_worker_error", result.get("error_type")
            save(args.output/(result["case_id"]+".json"), result); results.append(result)
        if pool is not None:
            pool.close(); pool.join(); pool = None
        assert len(results) == len(cases)
        for row in job["files"]:
            assert sha(root/row["path"]) == row["sha256"]
        assert sha(args.job) == original_job_sha
        complete = True
    finally:
        if pool is not None:
            pool.terminate(); pool.join()
        signal.alarm(0)
        summary = {"source_sha256": sha(Path(__file__)), "job_sha256": sha(args.job),
            "complete": complete, "case_filter": args.case, "cases_completed": len(results),
            "cases_admitted": sum(r["admitted"] for r in results), "workers": args.workers,
            "all_owned_workers_joined": True, "python": sys.version.split()[0],
            "machine": os.uname().machine, "float_mantissa_bits": sys.float_info.mant_dig,
            "no_numpy_igl_or_network_dependency": True, "source_inputs_rehashed_unchanged": complete,
            "seconds": time.monotonic()-started, "physics_admitted": False, "manufacturing_qualified": False}
        save(args.output/"terminal.json", summary)
        files = [{"path": p.name, "bytes": p.stat().st_size, "sha256": sha(p)} for p in sorted(args.output.iterdir()) if p.is_file()]
        save(args.output/"manifest.json", {"files": files, "complete": complete})
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
