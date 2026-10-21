"""Prepare tiny declared inputs or inspect saved outputs; never execute CGAL."""
import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import struct


def fixture(rotated=False, split=True):
    s = 76.0; d = 1/1024
    p = [(-s, -s, -s), (s, -s, -s), (s, s, -s), (-s, s, -s),
         (-s, -s, s), (s, -s, s), (s, s, s), (-s, s, s), (0.0, 0.0, s)]
    bottom = [(0, 2, 1), (0, 3, 2)]
    sides = [(0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
             (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]
    top = [(8, 4, 5), (8, 5, 6), (8, 6, 7), (8, 7, 4)]
    if split:
        p.append((d, d, s))
        top = [(8, 4, 5), (8, 5, 9), (9, 5, 6), (8, 9, 7), (9, 6, 7), (8, 7, 4)]
    if rotated:
        p = [(z, y, -x) for x, y, z in p]  # determinant+1; all vertices x=+-76.
    return p, bottom+top+sides


def pack(p, f):
    return b"962SURF1"+struct.pack("<QQ", len(p), len(f))+b"".join(
        struct.pack("<ddd", *row) for row in p)+b"".join(struct.pack("<QQQ", *row) for row in f)


def read(path):
    raw = path.read_bytes()
    if len(raw) < 24 or raw[:8] != b"962SURF1":
        raise ValueError("Complete indexed surface required")
    nv, nf = struct.unpack_from("<QQ", raw, 8)
    if not 0 < nv <= 10 or not 0 < nf <= 16 or len(raw) != 24+24*(nv+nf):
        raise ValueError("Only the declared tiny fixture arrays are accepted")
    p = list(struct.iter_unpack("<ddd", raw[24:24+24*nv]))
    f = list(struct.iter_unpack("<QQQ", raw[24+24*nv:]))
    if not all(math.isfinite(x) for row in p for x in row) or any(max(row) >= nv for row in f):
        raise ValueError("Finite complete fixture coordinates and indices required")
    return p, f


def triangles(p, f):
    def canonical(row):
        return min(row, row[1:]+row[:1], row[2:]+row[:2])
    return Counter(canonical(tuple(p[i] for i in row)) for row in f)


def qualities(p, f):
    out = []
    for a, b, c in f:
        u = tuple(p[b][i]-p[a][i] for i in range(3))
        v = tuple(p[c][i]-p[a][i] for i in range(3))
        cross = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])
        q = 2*math.sqrt(3)*math.sqrt(sum(x*x for x in cross))/(
            sum(x*x for x in u)+sum(x*x for x in v)+sum((v[i]-u[i])**2 for i in range(3)))
        if not math.isfinite(q) or q <= 0:
            raise ValueError("Finite nondegenerate triangles required")
        out.append(q)
    return dict(triangles=len(f), below_necessary_bound=sum(x < 2/29 for x in out),
                minimum_triangle_SICN=min(out))


def closed_volume(p, f):
    edges = Counter((a, b) for row in f for a, b in zip(row, row[1:]+row[:1]))
    if any(n != 1 or edges[b, a] != 1 for (a, b), n in edges.items()):
        raise ValueError("Exact opposite closed oriented edge incidence required")
    if set(range(len(p))) != {i for row in f for i in row}:
        raise ValueError("Unreferenced fixture vertex")
    volume = Fraction(0)
    for row in f:
        a, b, c = [tuple(Fraction(x) for x in p[i]) for i in row]
        volume += (a[0]*(b[1]*c[2]-b[2]*c[1])+a[1]*(b[2]*c[0]-b[0]*c[2])
                   +a[2]*(b[0]*c[1]-b[1]*c[0]))/6
    if volume != 152**3:
        raise ValueError("The exact known cube volume changed")
    return int(volume)


def assess_arrays(source, result, expected, origin_bytes):
    p, f = source; q, g = result; ep, ef = expected
    if Counter(q) != Counter(ep) or triangles(q, g) != triangles(ep, ef):
        raise ValueError("Actual complete coordinates/oriented triangles differ from the declared reference")
    original_lookup = {point: i for i, point in enumerate(p)}
    if len(original_lookup) != len(p):
        raise ValueError("Unique declared original fixture coordinates required")
    independently_derived_origins = [original_lookup[point] for point in q]
    if origin_bytes != b"".join(struct.pack("<Q", i) for i in independently_derived_origins):
        raise ValueError("Native source-coordinate origins disagree with exact coordinate lookup")
    before = qualities(p, f); after = qualities(q, g)
    seeds = {i for row in f if qualities(p, [row])["below_necessary_bound"] for i in row}
    exterior = [row for row in f if not any(i in seeds for i in row)]
    fixed = {i for row in exterior for i in row} | {i for i, point in enumerate(p) if abs(point[0]) == 76}
    if any(Counter(q)[p[i]] != 1 for i in fixed) or triangles(p, exterior)-triangles(q, g):
        raise ValueError("Fixed coordinates or exterior oriented faces changed")
    volume = closed_volume(q, g)
    return dict(before=before, after=after, actual_vertices=len(q), fixed_vertices=len(fixed),
                all_fixed_coordinates_exact=True, all_exterior_oriented_faces_exact=True,
                all_complete_coordinate_triangles_match_known_reference=True,
                exact_signed_volume_mm3=volume, source_origin_map_independently_checked=True,
                analytical_whole_surface_bidirectional_distance_mm=0,
                distance_basis="Exact known cube triangulation after an exact planar radial-edge subdivision; no sampled distance or CUB/head query.",
                original_transport_or_runtime_receipt_authenticated=False,
                head_geometry_used=False, solver_admission_established=False, engineering_accepted=False)


def require_native_flags(native, checked, improves):
    if native["full_surface_before"] != checked["before"] or native["full_surface_after"] != checked["after"]:
        raise ValueError("Native quality report differs from all actual fixture arrays")
    if type(native["accepted_collapses"]) is not int or native["accepted_collapses"] != int(improves):
        raise ValueError("The declared exact collapse count was not observed")
    for name in ["candidate_written", "full_quality_objective"]:
        if native[name] is not improves:
            raise ValueError("Native improvement/writing flags disagree with the declared case")
    for name in ["fixed_source_coordinates_exact", "exterior_oriented_faces_exact",
                 "retained_coordinates_are_exact_source_points", "closed_valid_triangle_mesh",
                 "collapse_count_bookkeeping"]:
        if native[name] is not True:
            raise ValueError("Native invariant flag disagrees with actual full-array fixture proof")
    if native["geometry_budget_mm"] != 0.0625 or native["soft_stop_requested"] is not False:
        raise ValueError("Complete unchanged-budget fixture output required")


def prepare(output):
    output.mkdir(parents=True, exist_ok=False)
    records = {}
    for name, kwargs in [("common-fixed-neighbor", {}), ("all-fixed-rotated", {"rotated": True}),
                         ("known-centered-cube", {"split": False})]:
        arrays = fixture(**kwargs); closed_volume(*arrays)
        raw = pack(*arrays)
        with (output/(name+".bin")).open("xb") as stream:
            stream.write(raw)
        records[name] = dict(input_sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw),
                             vertices=len(arrays[0]), **qualities(*arrays))
    with (output/"fixture-inputs.json").open("x") as stream:
        json.dump(dict(schema="962-finest-endpoint-fixture-inputs/v1", fixtures=records,
                       native_executed=False, synthetic_inputs_only=True), stream, indent=2)
        stream.write("\n")
    return records


def assess(directory):
    cases = [("common-neighbor-source001", False, False), ("common-neighbor-source002", False, True),
             ("all-fixed-source002", True, False)]
    results = {}
    for label, rotated, improves in cases:
        target = directory/label
        source = fixture(rotated=rotated)
        expected = fixture() if not improves else fixture(split=False)
        if rotated:
            expected = fixture(rotated=True)
        result = read(target/"proposed-surface.bin")
        checked = assess_arrays(source, result, expected, (target/"vertex-coordinate-origins.u64").read_bytes())
        native = json.loads((target/"report.json").read_text())
        require_native_flags(native, checked, improves)
        if (target/"quality-candidate.bin").exists() is not improves:
            raise ValueError("Complete declared candidate/stagnation outputs required")
        if improves and (target/"quality-candidate.bin").read_bytes() != (target/"proposed-surface.bin").read_bytes():
            raise ValueError("Candidate differs from independently assessed proposal")
        results[label] = checked
    with (directory/"fixture-array-assessment.json").open("x") as stream:
        json.dump(dict(status="synthetic_actual_array_checks_passed_execution_receipts_still_separate",
                       results=results, head_execution_authorized=False), stream, indent=2); stream.write("\n")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare-fresh", type=Path)
    mode.add_argument("--assess", type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.prepare_fresh) if args.prepare_fresh else assess(args.assess), indent=2))
