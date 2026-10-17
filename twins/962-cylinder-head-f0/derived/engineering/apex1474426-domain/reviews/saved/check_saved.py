"""Independent saved-domain association/Fraction check; never imports creator predicates."""
from pathlib import Path
from fractions import Fraction as F
from itertools import combinations
from collections import defaultdict, Counter
import hashlib, json, math, struct

ROOT = Path(__file__).resolve().parents[3]
B = ROOT / "work/962-engineering"
HERE = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
load = lambda p: json.loads(Path(p).read_text())
rat = lambda v: F(int(v["numerator"]), int(v["denominator"]))
enc = lambda v: {"numerator": str(v.numerator), "denominator": str(v.denominator)}
sub = lambda a, b: tuple(x-y for x, y in zip(a, b))
dot = lambda a, b: sum(x*y for x, y in zip(a, b))
cross = lambda a, b: (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
cycle = lambda row: min(tuple(row[i:]+row[:i]) for i in range(3))
ap = B/"apex1474426-domain-equivalence-execution-prep-001/actual-contract.json"
cp = B/"apex1474426-domain-equivalence-root-execution-001/closed-result.json"
rp = B/"apex1474426-domain-equivalence-001/report.json"
a, closed, result = load(ap), load(cp), load(rp)
assert sha(ap) == closed["actual_sha256"] == result["contract_sha256"]
assert result["source_sha256"] == a["source_sha256"]
assert result["input_hashes"] == a["input_hashes"] and len(a["input_hashes"]) == 32
assert set(p.name for p in rp.parent.iterdir()) == {"report.json"}
assert closed["outputs"] == {"report.json": {"bytes": rp.stat().st_size, "sha256": sha(rp)}}
assert closed["returncode"] == 0 and closed["stop_reason"] is None and closed["signals_sent"] == []
assert closed["wait_reaped"] and closed["individual_owned_PID_absent"]
assert closed["all32_inputs_unchanged"] and set(closed["input_match_by_path"]) == set(a["input_hashes"])
assert all(closed["input_match_by_path"].values()) and closed["actual_unchanged"] and closed["child_peer_unchanged"]
assert closed["selected_python_unchanged"] and not closed["native_or_head_edit_or_PDE_performed"]
assert not closed["universal_process_absence_claimed"]
assert sha(B/"apex1474426-domain-equivalence-child-peer-001/review.json") == closed["child_peer_sha256"]
for name, meta in [("stdout.log", closed["stdout"]), ("stderr.log", closed["stderr"])]:
    p = cp.parent/name
    assert p.stat().st_size == meta["bytes"] == 0 and sha(p) == meta["sha256"]
launch = load(cp.parent/"launch.json")
assert launch["actual_sha256"] == sha(ap) and launch["child_peer_sha256"] == closed["child_peer_sha256"]
assert launch["timeout_seconds"] == 300 and launch["start_new_session"] and not launch["automatic_retry"]
assert launch["owned_PID"] == launch["owned_PGID"] == closed["owned_PID"]
obs = load(B/"direct-sicn-apex1474426-cavity-study-001/saved-star-observation.json")
shell = load(B/"direct-sicn-apex1474426-cavity-study-001/local-shell-input-001.json")
arrays = load(B/"fixed-shell-netgen-apex1474426-001/arrays.json")
worker = load(B/"fixed-shell-netgen-apex1474426-001/fixture-report.json")
prior_peer = load(B/"fixed-shell-netgen-apex1474426-result-peer-001/review.json")
assert result["source_candidate_report_sha256"] == sha(B/"fixed-shell-netgen-apex1474426-001/fixture-report.json")
assert result["source_candidate_arrays_sha256"] == sha(B/"fixed-shell-netgen-apex1474426-001/arrays.json")
assert result["source_candidate_independent_peer_sha256"] == sha(B/"fixed-shell-netgen-apex1474426-result-peer-001/review.json")
assert prior_peer["decision"] == "CLEAR_COMPLETED_LOCAL_SICN_GATE_PASS_ONLY"
assert worker["after"] == worker["saved_reopen"] and arrays["after"] == arrays["saved_reopen"]
mapping = {t: i+1 for i, t in enumerate(shell["local_to_global_node_tags"])}
mapping[1474426] = 33
assert result["original_global_to_comparison_node_tags"] == {str(k): v for k, v in mapping.items()}
assert obs["apex"] == 1474426 and len(obs["selected_node_rows"]) == 33
old_xyz = {}
for row in obs["selected_node_rows"]:
    xyz = row["coordinates_mm"]
    assert [float(v).hex() for v in xyz] == row["binary64_hex"]
    old_xyz[mapping[row["node_tag"]]] = xyz
old_cells = {row["tetrahedron_tag"]: [mapping[t] for t in row["node_tags"]] for row in obs["native_ordered_cell_rows"]}
saved = arrays["saved_reopen"]
new_xyz = dict(zip(saved["node_tags"], saved["coordinates_mm"]))
new_cells = dict(zip(saved["tetra_tags"], saved["tetra_node_tags"]))
assert set(old_xyz) == set(range(1,34)) and set(new_xyz) == set(range(1,41))
assert len(old_cells) == 60 and len(new_cells) == 101
for row in shell["vertex_rows"]:
    t = row["local_node_tag"]
    assert struct.pack("<3d", *old_xyz[t]).hex() == struct.pack("<3d", *new_xyz[t]).hex() == row["binary64_little_endian_bytes_hex"]
expected = sorted(cycle(row["local_node_tags"]) for row in shell["oriented_triangle_rows"])
assert len(expected) == len(set(expected)) == 60
reference = rat(shell["exact_enclosed_volume_mm3"])
summaries = {}
for name, xyz, cells, count, internals in [("old", old_xyz, old_cells, 1770, 90), ("candidate", new_xyz, new_cells, 5050, 172)]:
    assert len({struct.pack("<3d", *v) for v in xyz.values()}) == len(xyz)
    points = {t: tuple(F.from_float(float(v)) for v in row) for t, row in xyz.items()}
    stored = result[name]
    assert stored["cell_count"] == len(cells) and stored["all_exact_positive"] is True
    assert [r["tetrahedron_tag"] for r in stored["quality_rows"]] == sorted(cells)
    assert len({tuple(sorted(v)) for v in cells.values()}) == len(cells)
    assert set().union(*(set(v) for v in cells.values())) == set(points)
    incidence = defaultdict(list)
    volume = F(0)
    poor = 0
    for tag, row, qrow in [(tag, cells[tag], qrow) for tag, qrow in zip(sorted(cells), stored["quality_rows"])]:
        assert qrow["ordered_node_tags"] == row and len(set(row)) == 4
        p = [points[t] for t in row]
        e1, e2, e3 = [sub(p[j], p[0]) for j in (1,2,3)]
        det = dot(e1, cross(e2,e3))
        b = tuple(2*y-x for x,y in zip(e1,e2))
        c = tuple(z-(x+y)/3 for x,y,z in zip(e1,e2,e3))
        N = dot(e1,e1)+dot(b,b)/3+F(3,2)*dot(c,c)
        ec, bc, ce = cross(e1,e2), cross(b,c), cross(c,e1)
        C = F(4,3)*dot(ec,ec)+F(1,2)*dot(bc,bc)+F(3,2)*dot(ce,ce)
        assert det > 0 and N > 0 and C > 0
        Q2 = 18*det*det/(N*C)
        assert rat(qrow["exact_determinant_mm3"]) == det and rat(qrow["exact_SICN_squared"]) == Q2
        assert qrow["exact_point1_gate_passed"] is (Q2 >= F(1,100))
        poor += Q2 < F(1,100)
        volume += det/6
        for pattern in [(0,2,1),(0,1,3),(0,3,2),(1,2,3)]:
            face = [row[j] for j in pattern]
            incidence[tuple(sorted(face))].append(cycle(face))
    outer, internal = [], 0
    for faces in incidence.values():
        assert len(faces) in (1,2)
        if len(faces) == 1:
            outer.append(faces[0])
        else:
            assert faces[0] == cycle(list(reversed(faces[1])))
            internal += 1
    assert internal == internals == stored["internal_face_pairs"]
    assert sorted(outer) == expected == [tuple(row) for row in stored["oriented_boundary"]]
    assert volume == reference == rat(stored["exact_signed_volume_mm3"])
    if name == "candidate":
        assert poor == 0
    pair_rows = result["pair_results"][name]
    assert len(pair_rows) == count
    dimensions, shared_counts = Counter(), Counter()
    for row, (first, second) in zip(pair_rows, combinations(sorted(cells),2)):
        shared = sorted(set(cells[first]) & set(cells[second]))
        assert row["tetrahedron_tags"] == [first, second]
        assert row["shared_node_tags"] == shared and row["expected_simplex_dimension"] == len(shared)-1
        assert len(shared) <= 3 and row["plane_triples_enumerated"] == 56
        assert type(row["independent_plane_triples"]) is int and 4 <= row["independent_plane_triples"] <= 56
        assert type(row["intersection_vertices"]) is int and row["intersection_vertices"] == len(shared)
        assert row["illegal_intersection_vertices"] == 0 and row["all_illegal_rational_witnesses"] == []
        assert row["intersection_equals_tagged_shared_simplex"] is True
        dimensions[str(len(shared)-1)] += 1
        shared_counts[str(len(shared))] += 1
    assert result["pair_failures"][name] == 0
    summaries[name] = {"nodes": len(xyz), "cells": len(cells), "exact_positive_determinants": len(cells), "exact_quality_rows_equal_saved": True, "positive_cells_below_point1": int(poor), "exact_volume_mm3": enc(volume), "opposed_internal_pairs": internal, "common_oriented_boundary_faces": len(outer), "complete_pair_count": count, "pair_dimensions": dict(sorted(dimensions.items())), "pair_shared_counts": dict(sorted(shared_counts.items())), "all_saved_verdicts_true_zero_illegal_witnesses": True, "pair_geometric_predicate_independently_reexecuted": False}
assert result["old_complete_unordered_pairs"] == 1770 and result["candidate_complete_unordered_pairs"] == 5050
assert result["complete_unordered_pairs"] == 6820 and result["plane_triples_enumerated"] == 381920
assert all(result[k] is True for k in ["exact_common32_coordinate_words","exact_identical_oriented60_boundary","exact_signed_volume_identity","exact_old_pair_embedding","exact_candidate_pair_embedding","local_domain_equivalence_proved","bound_inputs_unchanged"])
assert result["status"] == "same_compact_oriented_local_domain"
assert all(v is False for v in result["qualification"].values()) and result["qualification"] == a["qualification"]
assert result["native_optimizer_or_meshwrite_calls"] == 0 and result["coordinates_changed"] is False
check = {"schema": "962-independent-apex1474426-domain-saved-association-check/v1", "bindings": {"report_sha256": sha(rp), "actual_sha256": sha(ap), "root_closed_sha256": sha(cp), "source_sha256": a["source_sha256"], "child_peer_sha256": closed["child_peer_sha256"]}, "stages": summaries, "complete161_exact_det_quality_volume_and_incidence_checked": True, "all32_coordinate_words_equal_and_common60_boundary": True, "all6820_saved_pair_ids_order_shared_dimensions_and56_metadata_checked": True, "all_saved_verdicts_true_zero_illegal_witnesses": True, "geometric_intersection_predicate_independently_reexecuted": False, "conclusion": "Completed root exact query reports both local embeddings and equal compact oriented occupied local domains. Saved associations/coverage/verdicts agree with independently reconstructed positive complexes/common shell; all-pair intersection geometry itself is source-reviewed and root-executed, not independently rerun here.", "head_stitch_or_physical_acceptance": False}
f = HERE/"independent-saved-check.json"
with f.open("x") as stream:
    json.dump(check,stream,indent=2,allow_nan=False)
    stream.write("\n")
print(json.dumps({"decision":"CLEAR_LOCAL_DOMAIN_SAVED_ASSOCIATIONS","old_cells":60,"candidate_cells":101,"pairs":6820,"check_sha256":sha(f)},sort_keys=True))
