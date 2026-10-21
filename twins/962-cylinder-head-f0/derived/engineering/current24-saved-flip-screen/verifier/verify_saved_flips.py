"""HELD independent saved-only verifier. No imports of worker or driver.

One future --verify invocation runs five analytic guards then one saved check.
Nothing has run. An external owner/admission must bind this source and inputs.
"""
from pathlib import Path
from fractions import Fraction as F
from itertools import combinations, permutations
import hashlib
import json
import math
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
PREP = Path(__file__).resolve().parent
CAP = 32 * 1024**2
BOUNDARY = 871731
REPORT = "work/962-engineering/head-star-current110-pass62-application-001/worker-report.json"
PARENT = "work/962-engineering/head-star-current110-pass62-application-root-execution-001/result-peer-acceptance.json"
CLOSED = "work/962-engineering/head-star-current110-pass62-application-root-execution-001/closed-result.json"
MANIFEST = "work/962-engineering/head-star-current110-component-sicn-prep-001/component-manifest.json"
SELECTED = "work/962-engineering/head-star-current110-pass62-apply-prep-002/selected-proposals.json"


def require(ok, message):
    if not ok:
        raise ValueError(message)


def decode(raw):
    def unique(pairs):
        out = {}
        for key, value in pairs:
            require(key not in out, "Duplicate JSON key: " + key)
            out[key] = value
        return out
    def finite(token):
        raise ValueError("Nonfinite JSON token: " + token)
    return json.loads(raw, object_pairs_hook=unique, parse_constant=finite)


def descriptor(path, raw):
    return dict(path=path.relative_to(ROOT).as_posix(),
                sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def rational(value):
    return dict(numerator=str(value.numerator), denominator=str(value.denominator))


def sign_permutation(values):
    return -1 if sum(values[i] > values[j] for i in range(len(values))
                     for j in range(i + 1, len(values))) % 2 else 1


def squared_distance(a, b):
    return sum((a[i] - b[i])**2 for i in range(3))


def cartesian_determinant(points):
    """Six-term Cartesian determinant, independent of the worker cross kernel."""
    edges = [[points[j][i] - points[0][i] for i in range(3)] for j in range(1, 4)]
    return sum((sign_permutation(p) * edges[0][p[0]] * edges[1][p[1]] * edges[2][p[2]]
                for p in permutations(range(3))), F())


def face_gram_quality(points):
    """Q²=36D²/(sum six edge lengths² * sum four face Gram determinants).

    No sqrt, inverse, worker transform, copied cofactor kernel or tolerance.
    Coordinates are exact fractions of the saved binary64 values.
    """
    determinant = cartesian_determinant(points)
    edges_squared = sum((squared_distance(points[i], points[j])
                         for i, j in combinations(range(4), 2)), F())
    face_sum = F()
    for i, j, k in combinations(range(4), 3):
        u = [points[j][a] - points[i][a] for a in range(3)]
        v = [points[k][a] - points[i][a] for a in range(3)]
        uu = sum(x*x for x in u)
        vv = sum(x*x for x in v)
        uv = sum(x*y for x, y in zip(u, v))
        face_sum += uu*vv - uv*uv
    denominator = edges_squared * face_sum
    return determinant, 36*determinant**2/denominator if denominator > 0 else None


def quality_gate(determinant, q2):
    return determinant > 0 and q2 is not None and q2 >= F(1, 100)


def oriented_faces(tetrahedra):
    """Alternating simplicial boundary with signed sorted-face incidence."""
    rows = {}
    for tetrahedron in tetrahedra:
        for omitted in range(4):
            face = tuple(v for i, v in enumerate(tetrahedron) if i != omitted)
            key = tuple(sorted(face))
            coefficient = (-1 if omitted % 2 else 1) * sign_permutation(face)
            rows.setdefault(key, []).append(coefficient)
    valid = all(len(v) in (1, 2) and (len(v) == 1 or sum(v) == 0) for v in rows.values())
    boundary = []
    for face, coefficients in rows.items():
        if len(coefficients) == 1:
            boundary.append(face if coefficients[0] == 1 else (face[0], face[2], face[1]))
    return valid, sorted(boundary)


def rebuild_family(cells, poor, seeds):
    """Start with poor-cell features, then find every owner in all499 cells."""
    family = []
    for size, kind, owner_count in [(3, "2_to_3", 2), (2, "3_to_2", 3)]:
        features = {tuple(sorted(feature)) for tag in poor
                    for feature in combinations(cells[tag], size)}
        for feature in sorted(features):
            owners = sorted(tag for tag, cell in cells.items() if set(feature) <= set(cell))
            vertices = set().union(*(set(cells[tag]) for tag in owners))
            pattern = len(owners) == owner_count and len(vertices) == 5
            triangle = list(feature) if kind == "2_to_3" else sorted(vertices-set(feature))
            poles = sorted(vertices-set(feature)) if kind == "2_to_3" else list(feature)
            proposed = []
            if pattern:
                if kind == "2_to_3":
                    pattern = all(len(set(cells[tag])-set(feature)) == 1 for tag in owners)
                    proposed = [poles+list(edge) for edge in combinations(triangle, 2)]
                else:
                    pattern = {frozenset(cells[tag]) for tag in owners} == {
                        frozenset(poles+list(edge)) for edge in combinations(triangle, 2)}
                    proposed = [triangle+[pole] for pole in poles]
            if not pattern:
                proposed = []
            introduced = (poles if kind == "2_to_3" else triangle) if pattern else []
            family.append(dict(association_ID=kind+":"+",".join(map(str, feature)), kind=kind,
                removed_simplex=list(feature), observed_owner_tags=owners,
                poor_owner_tags=sorted(set(owners)&poor),
                complete_removed_simplex_owner_scope=bool(set(feature)&seeds),
                owner_scope_basis="complete saved seed star" if set(feature)&seeds else
                    "outside owners unavailable in saved499 context",
                expected_owner_count=owner_count, observed_bistellar_pattern=pattern,
                five_node_tags=sorted(vertices) if pattern else None,
                triangle=triangle if pattern else None, apices=poles if pattern else None,
                replacement_unoriented_cells=proposed, introduced_simplex=introduced,
                complete_introduced_simplex_owner_scope=bool(set(introduced)&seeds)))
    require(len(family) <= 240, "Finite240 association bound")
    require({t for row in family for t in row["poor_owner_tags"]} == poor, "All24 poor coverage")
    return family


def expected_disposition(association, points, cells, protected):
    result = dict(association_ID=association["association_ID"], local_result="not_screened",
        complete_flip_eligibility=None, mesh_application_authorized=False,
        global_embedding_or_nonoverlap_proved=False, source_exterior_or_BIN_membership=None,
        per_cell_region_and_interface_preservation=None,
        missing_evidence=["per-cell geometric entity/physical region labels",
            "internal facet/edge classification and interface labels",
            "source exterior/BIN membership and global embedding"])
    if not association["observed_bistellar_pattern"]:
        result["local_result"] = "refused_observed_incidence_not_2_or_3_five_point_pattern"
        return result
    old_tags = association["observed_owner_tags"]
    require(not set(old_tags)&protected, "Cannot remove prior1983 protected cells")
    original = [cells[t] for t in old_tags]
    old_rows = []
    replacements = []
    new_rows = []
    old_determinants = []
    new_determinants = []
    reasons = set()
    for tag, cell in zip(old_tags, original):
        d, q2 = face_gram_quality([points[t] for t in cell])
        old_determinants.append(d)
        old_rows.append(dict(tetrahedron_tag=tag, ordered_node_tags=list(cell),
            determinant_mm3=rational(d), SICN_squared=None if q2 is None else rational(q2)))
        if d <= 0:
            reasons.add("nonpositive original cavity cell")
    for slot, candidate in enumerate(association["replacement_unoriented_cells"], 1):
        cell = list(candidate)
        d, q2 = face_gram_quality([points[t] for t in cell])
        if d < 0:
            cell[-2:] = cell[-2:][::-1]
            d, q2 = face_gram_quality([points[t] for t in cell])
        passed = quality_gate(d, q2)
        replacements.append(tuple(cell))
        new_determinants.append(d)
        new_rows.append(dict(symbolic_slot=slot, ordered_node_tags=cell,
            determinant_mm3=rational(d), SICN_squared=None if q2 is None else rational(q2),
            positive_and_SICN_point1=passed))
        if not passed:
            reasons.add("replacement quality/orientation failure")
    old_valid, old_boundary = oriented_faces(original)
    new_valid, new_boundary = oriented_faces(replacements)
    if not old_valid or not new_valid or old_boundary != new_boundary or len(old_boundary) != 6:
        reasons.add("oriented six-face boundary/internal cancellation mismatch")
    supports = []
    for face in old_boundary:
        others = sorted(set(association["five_node_tags"])-set(face))
        ds = [cartesian_determinant([points[t] for t in (*face, other)]) for other in others]
        passed = len(others) == 2 and all(d < 0 for d in ds)
        supports.append(dict(oriented_face=list(face), other_node_tags=others,
            determinants_mm3=[rational(d) for d in ds], strict_outward_support=passed))
        if not passed:
            reasons.add("not a strictly convex five-point cavity")
    old_sum, new_sum = sum(old_determinants, F()), sum(new_determinants, F())
    if old_sum != new_sum:
        reasons.add("exact signed-volume mismatch")
    new_keys = [frozenset(cell) for cell in replacements]
    if len(set(new_keys)) != len(new_keys):
        reasons.add("duplicate replacement cells")
    complement = {frozenset(cell):tag for tag, cell in cells.items() if tag not in old_tags}
    duplicate = [dict(symbolic_slot=i+1, existing_tetrahedron_tag=complement[key])
                 for i, key in enumerate(new_keys) if key in complement]
    if duplicate:
        reasons.add("replacement duplicates observed unchanged cell")
    introduced = set(association["introduced_simplex"])
    outside = sorted(tag for tag, cell in cells.items()
                     if tag not in old_tags and introduced <= set(cell))
    if outside:
        reasons.add("introduced simplex already present in observed complement")
    if not association["complete_removed_simplex_owner_scope"]:
        result["missing_evidence"].append("complete outside owners of removed simplex")
    if not association["complete_introduced_simplex_owner_scope"]:
        result["missing_evidence"].append("global absence of introduced simplex/duplicates")
    result.update(local_result="failed_exact_local_screen" if reasons else "passed_exact_local_screen_only",
        reasons=sorted(reasons), original_cells=old_rows, replacement_cells=new_rows,
        oriented_boundary_original=[list(face) for face in old_boundary],
        oriented_boundary_replacement=[list(face) for face in new_boundary],
        strict_support_witnesses=supports, original_signed_volume_mm3=rational(old_sum/6),
        replacement_signed_volume_mm3=rational(new_sum/6), exact_volume_equal=old_sum == new_sum,
        observed_duplicate_cells=duplicate, introduced_simplex_observed_outside_owners=outside,
        all271_coordinate_words_unchanged=True, protected1983_removed_cells_disjoint=True,
        all_unremoved_saved_good_shared_and_poor_cells_unchanged_by_construction=True)
    return result


def expected_conflicts(family):
    output = []
    for i, a in enumerate(family):
        for b in family[i+1:]:
            if not (a["observed_bistellar_pattern"] and b["observed_bistellar_pattern"]):
                continue
            shared = sorted(set(a["observed_owner_tags"])&set(b["observed_owner_tags"]))
            a_cells = {tuple(sorted(c)) for c in a["replacement_unoriented_cells"]}
            duplicates = sorted(a_cells&{tuple(sorted(c)) for c in b["replacement_unoriented_cells"]})
            if shared or duplicates:
                output.append(dict(association_IDs=[a["association_ID"], b["association_ID"]],
                    shared_removed_cell_tags=shared, duplicate_replacement4sets=[list(c) for c in duplicates]))
    return output


def typed_hash(values, code):
    return hashlib.sha256(struct.pack("<"+code*len(values), *values)).hexdigest()


def parent_context(inputs, worker_held):
    source = inputs[REPORT]
    parent = inputs[PARENT]
    closed = inputs[CLOSED]
    require(parent["decision"] == "ACCEPT_REVIEWED_COORDINATE_ONLY_PARTIAL_IMPROVEMENT_PRESERVE_WHOLE_HEAD_QUALITY_REFUSAL", "Accepted parent decision")
    for key in ["fresh_native_complete_census_and_procedural_checks_accepted_in_recorded_software_scope",
                "selected66_coordinate_rows_applied_and_saved",
                "unselected1097202_nodes_and_connectivity_boundary_fixed",
                "strict_full_head_quality_rejected",
                "no_source_scientific_or_native_reexecution_by_acceptance"]:
        require(parent[key] is True, "Parent preservation: "+key)
    require((parent["poor_before"], parent["poor_after"], parent["removed_original_poor"]) == (110,24,86), "Parent110/24/86")
    require(parent["saved_partial_mesh"] == worker_held["opaque_saved_mesh_identity"], "Opaque mesh identity only")
    require(parent["root_closed"] == worker_held["input_records"][CLOSED], "Closed parent identity")
    for role in ["root_own_review", "independent_peer", "independent_bindings"]:
        require(parent[role] == worker_held["input_records"][parent[role]["path"]], "Parent review join")
    require(closed["outputs"]["worker-report.json"]["sha256"] == worker_held["input_records"][REPORT]["sha256"] and closed["outputs"]["worker-report.json"]["bytes"] == worker_held["input_records"][REPORT]["bytes"], "Captured parentreport")
    require(source["after"] == source["saved_reopen"] and source["full_native_census_after_saved_reopen"] is True, "Complete saved reopen")
    require(source["status"] == "failed_outputs_preserved" and source["procedural_checks_passed"] is True
            and source["saved_mesh_identity_exact"] is True and source["bound_inputs_unchanged"] is True, "Accepted procedural source")
    require((source["setNode_call_count"],source["element_cache_refresh_count"],source["mesh_write_call_count"]) == (66,1,1), "Prior exact application operations")
    require(source["rejected11_proposed_coordinate_rows_applied"] is False and source["actual_whole_head_positive_poor_count"] == 24 and source["actual_whole_head_SICN_gate_passed"] is False, "Prior fullhead refusal preserved")
    after = source["after"]
    require(after["source_boundary_identity"] == worker_held["source_boundary_identity"], "Boundary identity")
    quality = after["quality"]["minimum_SICN"]
    require((quality["count"], quality["nonpositive_count"], quality["below_point1_count"]) == (3622025,0,24), "Parent quality census")
    require(quality["array_sha256"] == worker_held["minimum_SICN_array_sha256"] and quality["minimum"] == parent["minimum_native_SICN_unchanged"], "Originalworst array identity")
    stars = after["complete_native_census"]["complete_seed_star_census"]
    for key, count in dict(movable_count=16, prospective_coordinate_variables=48,
            complete_incident_tetrahedron_count=499, initially_positive_poor_incident_tetrahedra=24,
            initially_good_incident_tetrahedra=475, shared_by_multiple_movable_nodes_tetrahedra=33,
            unique_incident_node_count=271, unique_incident_boundary_node_count=179,
            unique_incident_other_interior_node_count=76).items():
        require(type(stars[key]) is int and stars[key] == count, "Full native census count: "+key)
    require(stars["schema"] == "962-complete-current-poor-seed-stars/v1"
            and stars["all_seed_stars_complete_including_initially_good_and_shared_cells"] is True
            and stars["all_positive_poor_rows_covered_by_movable_stars"] is True
            and stars["unseedable_positive_poor_tetrahedron_tags"] == [], "Complete source star scopes")
    nodes = stars["unique_incident_nodes"]
    rows = stars["complete_incident_tetrahedra"]
    seeds = set(stars["movable_node_tags"])
    require(len(nodes) == 271 and len(rows) == 499 and len(seeds) == 16, "271/499/16 context")
    require([r["node_tag"] for r in nodes] == sorted({r["node_tag"] for r in nodes}), "Ordered unique nodes")
    require([r["tetrahedron_tag"] for r in rows] == sorted({r["tetrahedron_tag"] for r in rows}), "Ordered unique cells")
    points, words, snapshot_points = {}, {}, []
    for row in nodes:
        tag = row["node_tag"]
        xyz = row["coordinates_mm"]
        require(type(tag) is int and tag > 0 and len(xyz) == 3 and all(type(x) in (int,float) and math.isfinite(x) for x in xyz), "Finite saved node")
        hx = [float(x).hex() for x in xyz]
        require(hx == row["binary64_hex"], "Source coordinate words")
        require(row["source_boundary_tag"] is (tag <= BOUNDARY) and row["in_movable_seed_set"] is (tag in seeds), "Node memberships")
        require(row["freshly_proved_classification_scope"] == ("below_dim3" if tag <= BOUNDARY else "dim3"), "Saved classification")
        points[tag] = [F.from_float(float(x)) for x in xyz]
        words[tag] = hx
        snapshot_points.append(dict(node_tag=tag, coordinates_mm=[float(x) for x in xyz],
            actual_coordinate_binary64_hex=hx, actual_coordinate_words_le_hex=struct.pack("<3d",*xyz).hex()))
    cells = {r["tetrahedron_tag"]:tuple(r["node_tags"]) for r in rows}
    require(len({frozenset(c) for c in cells.values()}) == 499 and set().union(*(set(c) for c in cells.values())) == set(points), "Full499 unique-cell/271union")
    poor = set()
    for row in rows:
        q = row["initial_native_SICN"]
        require(type(q) in (int,float) and math.isfinite(q) and 0 < q <= 1, "Saved native SICN")
        require(type(row["initially_positive_poor"]) is bool and row["initially_positive_poor"] == (q < .1), "Poor source label")
        if q < .1:
            poor.add(row["tetrahedron_tag"])
        require(len(row["node_tags"]) == len(set(row["node_tags"])) == 4 and set(row["node_tags"]) <= set(points), "Saved tetra connectivity")
        require(sorted(row["movable_node_tags"]) == sorted(seeds&set(row["node_tags"])), "Complete seed incidence")
    require(len(poor) == 24 and poor == set(stars["positive_poor_tetrahedron_tags"]), "All24 poor")
    require(len({r["native_array_index"] for r in rows}) == 499 and all(type(r["native_array_index"]) is int and 0 <= r["native_array_index"] < 3622025 for r in rows), "499native index associations")
    require(stars["per_movable_node_complete_incident_counts"] == [[t,sum(t in c for c in cells.values())] for t in sorted(seeds)], "Complete seed counts")
    hashes = dict(movable_node_tags_u64=typed_hash(sorted(seeds),"Q"),
        selected_tetrahedron_tags_u64=typed_hash(sorted(cells),"Q"),
        selected_tetrahedron_connectivity_u64=typed_hash([t for r in rows for t in r["node_tags"]],"Q"),
        union_node_tags_u64=typed_hash([r["node_tag"] for r in nodes],"Q"),
        union_coordinates_f64=typed_hash([x for r in nodes for x in r["coordinates_mm"]],"d"),
        selected_initial_SICN_f64=typed_hash([r["initial_native_SICN"] for r in rows],"d"))
    require(hashes == stars["ordered_tagged_array_sha256s"] == worker_held["current_typed_array_sha256s"], "All six full typed hashes")
    manifest, selected = inputs[MANIFEST], inputs[SELECTED]
    groups = {g["component_ID"]:g for g in manifest["cases"]}
    require(manifest["group_count"] == 73 and len(manifest["cases"]) == 73
            and manifest["all82_variable_nodes_and2482_cells_are_pairwise_disjoint_complete_partitions"] is True
            and manifest["all110_poor2372_good58_shared_memberships_preserved"] is True, "Original full partition metadata")
    accepted, rejected = set(selected["component_IDs"]), set(selected["rejected_component_IDs"])
    require(len(groups) == 73 and len(accepted) == 62 and len(rejected) == 11 and not accepted&rejected and accepted|rejected == set(groups), "Complete73/62/11 partition")
    all_cells = [t for g in groups.values() for t in g["tetrahedron_tags"]]
    all_seeds = [t for g in groups.values() for t in g["movable_node_tags"]]
    require(len(all_cells) == len(set(all_cells)) == 2482 and len(all_seeds) == len(set(all_seeds)) == 82, "2482/82 disjoint groups")
    protected = {t for g in accepted for t in groups[g]["tetrahedron_tags"]}
    protected_nodes = set(selected["selected_node_tags"])
    require(protected_nodes == {t for g in accepted for t in groups[g]["movable_node_tags"]}, "All accepted66 variable node tags")
    require(len(protected) == 1983 and len(protected_nodes) == 66 and not protected&set(cells) and not protected_nodes&seeds and selected["original_poor_cells_in_passed_groups"] == 86, "Prior1983/66/86 protection")
    require({t for g in rejected for t in groups[g]["tetrahedron_tags"]} == set(cells) and {t for g in rejected for t in groups[g]["movable_node_tags"]} == seeds, "Complete remaining rejected context")
    intake = dict(full_context_rows=271, full_incident_cells=499, current_poor_cells=24,
        good_incident_cells=475, shared_cells=33, movable_nodes=16, source_boundary_context=179,
        other_interior_context=76, all24_have_three_fixed_boundary_tag_vertices=True,
        full_typed_arrays_verified=hashes, source_boundary_identity=after["source_boundary_identity"],
        explicit_exterior_facet_membership_computed=False, source_BIN_read=False, raw_MSH_read=False)
    require(sum(t <= BOUNDARY for t in points) == 179 and sum(t > BOUNDARY and t not in seeds for t in points) == 76 and sum(len(set(c)&seeds) > 1 for c in cells.values()) == 33, "Complete classification/shared counts")
    poor_rows = after["complete_native_census"]["positive_poor_SICN_cells"]["complete_tagged_cells"]
    require([r["tetrahedron_tag"] for r in poor_rows] == sorted(poor), "All24 full poor rows")
    by_tag = {r["tetrahedron_tag"]:r for r in rows}
    by_node = {r["node_tag"]:r for r in nodes}
    for row in poor_rows:
        native = by_tag[row["tetrahedron_tag"]]
        require(row["node_tags"] == native["node_tags"] and row["native_array_index"] == native["native_array_index"] and float(row["SICN"]).hex() == float(native["initial_native_SICN"]).hex(), "Poor native association")
        require(row["binary64_hex"] == [words[t] for t in row["node_tags"]] and [[float(x).hex() for x in p] for p in row["coordinates_mm"]] == row["binary64_hex"], "All24 source coordinate words")
        require(sum(t <= BOUNDARY for t in row["node_tags"]) == 3 and len(set(row["node_tags"])&seeds) == 1, "24fixed-three/source seed associations")
    expected = dict(points=snapshot_points, words=[[t,words[t]] for t in sorted(words)],
        cells=[dict(tetrahedron_tag=t,ordered_node_tags=list(cells[t])) for t in sorted(cells)],
        poor=sorted(poor), seeds=sorted(seeds), protected_cells=sorted(protected),
        protected_nodes=sorted(protected_nodes), intake=intake, classification_rows=nodes)
    return expected, points, cells, poor, seeds, protected, rows, nodes


def guards():
    right = [[F(x) for x in p] for p in [(0,0,0),(1,0,0),(0,1,0),(0,0,1)]]
    regular = [[F(x) for x in p] for p in [(0,0,0),(1,1,0),(0,1,1),(1,0,1)]]
    require(face_gram_quality(right) == (F(1),F(2,3)), "Right tetra analytic D1/Q2=2/3")
    require(face_gram_quality(regular) == (F(2),F(1)), "Regular tetra analytic D2/Q2=1")
    require(face_gram_quality([right[0],right[2],right[1],right[3]]) == (F(-1),F(2,3)), "Orientation sign and invariant quality")
    require(face_gram_quality([right[0]]*4) == (F(),None), "Degenerate base refusal")
    planar = [right[0],right[1],right[2],[F(1),F(1),F()]]
    require(face_gram_quality(planar) == (F(),F()), "Planar zero quality distinguished from null metric")
    valid, faces = oriented_faces([(0,1,2,3),(0,2,1,4)])
    require(valid and len(faces) == 6 and quality_gate(F(1),F(1,100))
            and not quality_gate(F(1),F(1,101)) and not quality_gate(F(),F(1)), "Boundary cancellation and exact threshold")
    return dict(guard_count=5, names=["right_D1_Q2_2over3","regular_D2_Q2_1",
        "orientation_sign_quality_invariant","coincident_refusal","boundary_and_exact_threshold"], all_passed=True)


def verify_saved():
    held = decode((PREP/"held-preparation.json").read_bytes())
    loaded = {}
    before = {}
    for name, pin in held["input_records"].items():
        require(not Path(name).is_absolute() and ".." not in Path(name).parts
                and name.startswith("work/962-engineering/") and pin["path"] == name, "Fixed first-party input namespace")
        raw = (ROOT/name).read_bytes()
        before[name] = descriptor(ROOT/name,raw)
        require(before[name] == pin, "Held input identity changed: "+name)
        if name.endswith(".json"):
            loaded[name] = decode(raw)
    report = loaded[held["saved_report"]["path"]]
    worker_held = loaded[held["worker_held"]["path"]]
    require(report["worker_source"] == report["worker_source_after"] == held["worker_source"]
            and report["worker_held"] == report["worker_held_after"] == held["worker_held"], "Report exact worker ancestry")
    require(report["input_records_before"] == report["input_records_after"] == worker_held["input_records"], "Exact15 reportinput maps")
    context, points, cells, poor, seeds, protected, rows, nodes = parent_context(loaded,worker_held)
    require(report["schema"] == "962-current24-complete-saved-interior-flip-local-screen/v1" and report["status"] == "complete_saved_local_screen_only_eligibility_unavailable", "Saved diagnostic schema/status")
    for phase in ["before","after"]:
        require(canonical(report["complete_context_"+phase]) == canonical(context), "Complete independent parent context: "+phase)
        require(hashlib.sha256(canonical(context)).hexdigest() == report[phase+"_snapshot_sha256"], "Context snapshot digest")
    require(report["full_saved_native_cell_rows"] == rows and report["full_saved_coordinate_classification_rows"] == nodes, "Full parent499/271 saved rows")
    family = rebuild_family(cells,poor,seeds)
    require(canonical(report["associations"]) == canonical(family) and report["association_count"] == len(family), "Complete independent feature/owner family")
    expected = [expected_disposition(a,points,cells,protected) for a in family]
    require(canonical(report["complete_local_dispositions"]) == canonical(expected) and report["local_disposition_count"] == len(expected), "All independent exact witnesses/dispositions/reasons")
    conflicts = expected_conflicts(family)
    require(canonical(report["observed_pair_conflicts"]) == canonical(conflicts) and report["observed_pair_conflict_count"] == len(conflicts), "Complete observed pair conflicts")
    statuses = {}
    for row in expected:
        statuses[row["local_result"]] = statuses.get(row["local_result"],0)+1
    require(report["local_status_counts"] == statuses, "Complete local status counts")
    require(report["procedure_preservation_passed"] is True and report["complete_context_byte_identical"] is True and report["all_finite_rows_retained"] is True, "Saved preservation")
    require(report["complete_flip_eligibility"] is None and report["source_interface_region_exterior_or_BIN_evidence"] is None, "Missing evidence preserved")
    for key in ["global_embedding_or_nonoverlap_accepted","mesh_application_authorized",
                "head_PDE_or_strength_or_material_or_LPBF_or_manufacturing_accepted",
                "raw_MSH_BIN_or_native_runtime_body_read","optimizer_called",
                "combined_subset_or_flip_sequence_selected","automatic_retry"]:
        require(report[key] is False, "Forbidden authority/result: "+key)
    after = {name:descriptor(ROOT/name,(ROOT/name).read_bytes()) for name in held["input_records"]}
    require(after == before, "No verifier input may change")
    return dict(schema="962-current24-independent-saved-flip-exact-verification/v1",
        complete_finite_family_verified=True, complete_association_count=len(family),
        original_cell_witnesses=sum(len(row.get("original_cells",[])) for row in expected),
        replacement_cell_witnesses=sum(len(row.get("replacement_cells",[])) for row in expected),
        support_determinant_witnesses=sum(len(s["determinants_mm3"]) for row in expected
            for s in row.get("strict_support_witnesses",[])),
        independent_local_status_counts=statuses, observed_pair_conflicts=len(conflicts),
        full271_words_and499_cells_parent_associated=True, prior1983_66_86_protected=True,
        inputs_before=before, inputs_after=after, complete_flip_eligibility=None,
        mesh_application_authorized=False, global_embedding_accepted=False,
        native_or_physical_or_manufacturing_accepted=False,
        limits="Finite saved family only; unavailable owners/interfaces/regions/exterior/BIN/global evidence remain unavailable. No global infeasibility or topology necessity.")


if __name__ == "__main__":
    require(sys.flags.isolated == sys.flags.no_site == sys.flags.dont_write_bytecode == 1
            and sys.flags.optimize == 0 and "site" not in sys.modules
            and "_distutils_hack" not in sys.modules, "Selected-B-I-S runtime required")
    require(sys.implementation.name == "cpython" and sys.float_info.radix == 2
            and sys.float_info.mant_dig == 53 and struct.calcsize("d") == 8,
            "Binary64 CPython float required")
    require(len(sys.argv) == 2 and sys.argv[1] == "--verify", "One fixed future operation required")
    guard_result = guards()
    output = verify_saved()
    output["analytic_guards"] = guard_result
    encoded = (json.dumps(output,indent=2,allow_nan=False)+"\n").encode()
    require(len(encoded) <= CAP, "Complete verifier output must fit32MiB")
    sys.stdout.buffer.write(encoded)
