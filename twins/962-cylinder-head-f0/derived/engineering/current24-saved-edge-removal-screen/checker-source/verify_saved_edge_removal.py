"""HELD independent saved-only verifier. No imports of worker or driver.

One future --verify invocation runs five retained plus four new guards, then one saved check.
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


def polygon_templates(n):
    """Maximal noncrossing diagonal sets, independent of root-edge recursion."""
    require(type(n) is int and 4 <= n <= 8, "Only finite degree4..8 polygons")
    rim = {tuple(sorted((i, (i+1) % n))) for i in range(n)}
    diagonals = sorted(set(combinations(range(n), 2))-rim)
    disks = set()
    for selected in combinations(diagonals, n-3):
        if any(a < c < b < d or c < a < d < b
               for (a,b),(c,d) in combinations(selected,2)):
            continue
        edges = rim | set(selected)
        triangles = tuple(t for t in combinations(range(n),3)
                          if set(combinations(t,2)) <= edges)
        require(len(triangles) == n-2, "Maximal diagonal set must give n-2 faces")
        incidence = {e:sum(set(e) <= set(t) for t in triangles) for e in edges}
        require(all(v == (1 if e in rim else 2) for e,v in incidence.items()),
                "Complete triangle disk internal cancellation")
        disks.add(triangles)
    require(len(disks) == {4:2,5:5,6:14,7:42,8:132}[n], "Full diagonal Catalan count")
    return sorted(disks)


def cycle_from_owners(edge, tags, cells):
    require(len(edge) == len(set(edge)) == 2 and 4 <= len(tags) <= 8
            and len(tags) == len(set(tags)), "Complete finite edge star")
    opposite = []
    neighbors = {}
    for tag in tags:
        require(tag in cells and set(edge) <= set(cells[tag]), "Edge owner incidence")
        link_edge = tuple(sorted(set(cells[tag])-set(edge)))
        require(len(link_edge) == 2, "Opposite edge has two distinct vertices")
        opposite.append(link_edge)
        for a,b in (link_edge,link_edge[::-1]):
            neighbors.setdefault(a,set()).add(b)
    n = len(tags)
    require(len(set(opposite)) == len(opposite) and len(neighbors) == n
            and all(len(v) == 2 for v in neighbors.values()), "Simple degree-two link graph")
    start = min(neighbors)
    walks = []
    for first in sorted(neighbors[start]):
        walk = [start]
        previous,node = start,first
        while node != start and len(walk) <= n:
            require(node not in walk, "Link traversal repeats before closing")
            walk.append(node)
            following = neighbors[node]-{previous}
            require(len(following) == 1, "Unique next link edge")
            previous,node = node,next(iter(following))
        require(node == start and len(walk) == n and set(walk) == set(neighbors),
                "One connected closed n-cycle, no disconnected subsets")
        walks.append(tuple(walk))
    return list(min(walks)), [list(e) for e in opposite]


def edge_family(cells, poor, seeds):
    candidates = set()
    for tag in poor:
        for edge in combinations(cells[tag],2):
            if set(edge) & seeds:
                candidates.add(tuple(sorted(edge)))
    selected,outside = [],[]
    for edge in sorted(candidates):
        owners = sorted(t for t,cell in cells.items() if set(edge) <= set(cell))
        row = dict(case_ID="edge:"+",".join(map(str,edge)),central_edge=list(edge),
            removed_cell_tags=owners,removed_poor_cell_tags=sorted(set(owners)&poor),
            owner_scope_complete=True,owner_scope_basis="contains accepted complete-star seed",
            observed_degree=len(owners))
        if 4 <= len(owners) <= 8:
            selected.append(row)
        else:
            row["disposition"] = "outside selected degree4..8 route; retained, not infeasible"
            outside.append(row)
    require(len(selected) == 55, "All55 central-seed edge stars, not a subset")
    require({t for c in selected for t in c["removed_poor_cell_tags"]} == poor
            and {t for c in selected for t in c["central_edge"] if t in seeds} == seeds,
            "Full24poor/16seed selected-family coverage")
    return selected,outside


def cell_measure(cell, points, cache):
    """Cache one exact unordered four-set; preserve every signed ordered join."""
    require(len(cell) == len(set(cell)) == 4 and set(cell) <= set(points), "Four distinct saved nodes")
    key = tuple(sorted(cell))
    if key not in cache:
        cache[key] = face_gram_quality([points[t] for t in key])
    determinant,q2 = cache[key]
    return sign_permutation(cell)*determinant,q2


def independent_cavity(case, points, cells, protected, cache):
    tags = case["removed_cell_tags"]
    edge = case["central_edge"]
    cycle,opposite = cycle_from_owners(edge,tags,cells)
    n = len(tags)
    old = [cells[t] for t in tags]
    vertices = sorted({t for cell in old for t in cell})
    old_rows = []
    determinants = []
    for tag,cell in zip(tags,old):
        d,q2 = cell_measure(cell,points,cache)
        determinants.append(d)
        old_rows.append(dict(tetrahedron_tag=tag,node_tags=list(cell),D=rational(d),
            Q_squared=None if q2 is None else rational(q2),positive=d>0))
    valid,boundary = oriented_faces(old)
    expected = {tuple(sorted((apex,cycle[i],cycle[(i+1)%n])))
                for apex in edge for i in range(n)}
    sphere = (len(vertices) == n+2 and valid and len(boundary) == 2*n
              and {tuple(sorted(f)) for f in boundary} == expected)
    support = []
    for face in boundary:
        for other in vertices:
            if other not in face:
                d,_ = cell_measure((*face,other),points,cache)
                support.append(dict(outward_face=list(face),other_node_tag=other,
                                    D=rational(d),strict_inside=d<0))
    positive = bool(old_rows) and all(d>0 for d in determinants)
    strict = sphere and len(support) == 2*n*(n-1) and all(s["strict_inside"] for s in support)
    protected_ok = not set(tags)&protected
    reasons = []
    if not sphere:
        reasons.append("old oriented cone-cycle sphere not established")
    if not positive:
        reasons.append("old orientation/nondegeneracy failed")
    if not strict:
        reasons.append("strict convex supporting-facet certificate unresolved")
    if not protected_ok:
        reasons.append("removed cells intersect protected history")
    return dict(case=case,link=dict(valid=True,reasons=[],cycle=cycle,
                opposite_link_edges=opposite,degree=n),vertices=vertices,old_rows=old_rows,
        old_oriented_boundary=[list(f) for f in boundary],
        old_signed_volume=rational(sum(determinants,F())/6),
        abstract_edge_cycle_ball_and_boundary_sphere=sphere,
        all_old_tetrahedra_positive=positive,strict_support_rows=support,
        strict_convex_boundary_bijection_certified=strict,
        old_embedded_convex_filling_certified=sphere and positive and strict,
        protected_prior_cells_disjoint=protected_ok,reasons=reasons,
        source_region_interface_exterior_or_BIN_evidence=None,
        whole_head_embedding_or_nonoverlap_accepted=False)


def feature_index(cells):
    result = {2:{},3:{}}
    for tag,cell in cells.items():
        for k in (2,3):
            for feature in combinations(sorted(cell),k):
                result[k].setdefault(feature,set()).add(tag)
    return result


def independent_candidate(cavity, triangles, disk_family, ordinal, points, cells, seeds, owners, cache):
    case = cavity["case"]
    cycle = cavity["link"]["cycle"]
    tris = tuple(sorted(tuple(sorted(t)) for t in triangles))
    require(len(tris) == len(set(tris)) == len(cycle)-2, "One complete triangle disk")
    replacements,rows,determinants = [],[],[]
    for apex in case["central_edge"]:
        for triangle in tris:
            cell = (apex,)+triangle
            d,q2 = cell_measure(cell,points,cache)
            if d < 0:
                cell = (cell[0],cell[1],cell[3],cell[2])
                d,q2 = cell_measure(cell,points,cache)
            replacements.append(cell)
            determinants.append(d)
            rows.append(dict(node_tags=list(cell),D=rational(d),
                Q_squared=None if q2 is None else rational(q2),positive=d>0,
                exact_quality_gate_passed=quality_gate(d,q2)))
    valid,boundary = oriented_faces(replacements)
    chain = valid and [list(f) for f in boundary] == cavity["old_oriented_boundary"]
    volume = rational(sum(determinants,F())/6)
    same_volume = volume == cavity["old_signed_volume"]
    quality = bool(rows) and all(r["exact_quality_gate_passed"] for r in rows)
    keys = [tuple(sorted(cell)) for cell in replacements]
    duplicates = sorted(key for key in set(keys) if keys.count(key)>1)
    removed = set(case["removed_cell_tags"])
    complement = {tuple(sorted(cell)):tag for tag,cell in cells.items() if tag not in removed}
    existing = [dict(node_tags=list(key),existing_tetrahedron_tag=complement[key])
                for key in sorted(set(keys)&set(complement))]
    introduced = []
    for k in (2,3):
        old_features = {tuple(sorted(f)) for t in removed for f in combinations(cells[t],k)}
        new_features = {tuple(sorted(f)) for cell in replacements for f in combinations(cell,k)}
        for feature in sorted(new_features-old_features):
            outside = sorted(owners[k].get(feature,set())-removed)
            complete = bool(set(feature)&seeds)
            introduced.append(dict(dimension=k-1,node_tags=list(feature),
                observed_complement_owner_tags=outside,complete_owner_scope=complete,
                absent_from_observed_complement=not outside,
                global_missing_owner_absence=(not outside) if complete else None,
                semantic_region_interface_or_exterior_evidence=None))
    disk = cavity["link"]["valid"] and tris in disk_family
    embedded = (disk and cavity["old_embedded_convex_filling_certified"] and chain
                and len(replacements) == 2*(len(cycle)-2) and bool(rows)
                and all(r["positive"] for r in rows))
    reasons = list(cavity["reasons"])
    if not disk:
        reasons.append("replacement is not a complete Catalan link disk")
    if not chain:
        reasons.append("full oriented boundary/internal cancellation mismatch")
    if not same_volume:
        reasons.append("exact signed-volume mismatch")
    if not quality:
        reasons.append("replacement quality/orientation failure")
    if duplicates:
        reasons.append("duplicate replacement unordered four-set")
    if existing:
        reasons.append("replacement duplicates observed unchanged cell")
    if any(r["observed_complement_owner_tags"] for r in introduced):
        reasons.append("introduced feature already present in observed complement")
    if not embedded:
        reasons.append("local embedded convex filling not certified")
    return dict(candidate_ID=case["case_ID"]+":triangulation:"+str(ordinal),
        case_ID=case["case_ID"],removed_cell_tags=case["removed_cell_tags"],
        link_triangles=[list(t) for t in tris],replacement_cells=[list(c) for c in replacements],
        replacement_exact_rows=rows,abstract_suspension_of_triangulated_disk_ball=disk,
        oriented_boundary=[list(f) for f in boundary],oriented_boundary_equal=chain,
        signed_volume=volume,exact_signed_volume_equal=same_volume,
        all_replacement_exact_quality_gates_passed=quality,
        duplicate_replacement_four_sets=[list(k) for k in duplicates],
        observed_unchanged_cell_duplicates=existing,introduced_feature_owner_rows=introduced,
        local_embedded_convex_filling_certified=embedded,
        local_finite_predicates_passed=not reasons,reasons=reasons,
        complete_application_eligibility=None,global_embedding_and_nonoverlap_accepted=False,
        mesh_application_authorized=False,physics_material_LPBF_or_manufacturing_accepted=False)


def candidate_membership(rows, expected_IDs):
    observed = [row["candidate_ID"] for row in rows]
    require(observed == expected_IDs and len(observed) == len(set(observed)),
            "Every candidate in exact case/ordinal order, no missing/extra/duplicate rows")


def conflict_certificate(cases, candidates):
    """Derive full pair relation independently before checking its factorization."""
    by_case = {c["case"]["case_ID"]:[] for c in cases}
    removals = {c["case"]["case_ID"]:set(c["case"]["removed_cell_tags"]) for c in cases}
    proposed = {}
    for candidate in candidates:
        ident = candidate["candidate_ID"]
        by_case[candidate["case_ID"]].append(ident)
        proposed[ident] = {tuple(sorted(cell)) for cell in candidate["replacement_cells"]}
    expected_pairs = set()
    for first,second in combinations(candidates,2):
        if (removals[first["case_ID"]]&removals[second["case_ID"]]
                or proposed[first["candidate_ID"]]&proposed[second["candidate_ID"]]):
            expected_pairs.add(tuple(sorted((first["candidate_ID"],second["candidate_ID"]))))
    within,cross,duplicates = [],[],[]
    decoded_pairs = set()
    for case,ids in sorted(by_case.items()):
        if len(ids)>1:
            within.append(dict(case_ID=case,candidate_IDs=ids,
                               shared_removed_cell_tags=sorted(removals[case])))
            decoded_pairs.update(tuple(sorted(pair)) for pair in combinations(ids,2))
    for first,second in combinations(sorted(by_case),2):
        shared = sorted(removals[first]&removals[second])
        if shared:
            cross.append(dict(case_IDs=[first,second],shared_removed_cell_tags=shared,
                relation="every candidate from first case conflicts with every candidate from second"))
            decoded_pairs.update(tuple(sorted((a,b))) for a in by_case[first] for b in by_case[second])
    inverse = {}
    for ident,keys in proposed.items():
        for key in keys:
            inverse.setdefault(key,set()).add(ident)
    for key,ids in sorted(inverse.items()):
        if len(ids)>1:
            ids = sorted(ids)
            duplicates.append(dict(unordered_four_set=list(key),candidate_IDs=ids))
            decoded_pairs.update(combinations(ids,2))
    require(decoded_pairs == expected_pairs, "Factorized relation equals complete direct pair union")
    return dict(encoding="exact union of within-case cliques, cross-case complete products, duplicate-four-set cliques",
        case_candidate_memberships=by_case,within_case_conflict_cliques=within,
        cross_case_removed_cell_conflict_products=cross,duplicate_proposed_cell_cliques=duplicates,
        distinct_conflicting_candidate_pair_count=len(expected_pairs),
        all_pairs_represented_without_truncation=True,application_subset_selected=False),expected_pairs


def analytic_guards():
    retained = guards()
    for n,count in [(4,2),(5,5),(6,14),(7,42),(8,132)]:
        require(len(polygon_templates(n)) == count, "Independent maximal-diagonal counts")
    ids = ["a:1","a:2"]
    candidate_membership([dict(candidate_ID=x) for x in ids],ids)
    for malformed in [[dict(candidate_ID="a:1")],
                      [dict(candidate_ID="a:1"),dict(candidate_ID="a:1")],
                      [dict(candidate_ID="a:1"),dict(candidate_ID="extra")]]:
        refused = False
        try:
            candidate_membership(malformed,ids)
        except ValueError:
            refused = True
        require(refused, "Malformed completeness must refuse")
    cases = [dict(case=dict(case_ID="A",removed_cell_tags=[1,2])),
             dict(case=dict(case_ID="B",removed_cell_tags=[3,4]))]
    candidates = [dict(case_ID="A",candidate_ID="A:1",replacement_cells=[[10,11,12,13]]),
                  dict(case_ID="B",candidate_ID="B:1",replacement_cells=[[13,12,11,10]])]
    relation,pairs = conflict_certificate(cases,candidates)
    require(pairs == {("A:1","B:1")} and relation["cross_case_removed_cell_conflict_products"] == []
            and relation["duplicate_proposed_cell_cliques"] == [
                dict(unordered_four_set=[10,11,12,13],candidate_IDs=["A:1","B:1"])],
            "Disjoint-removal duplicate-output conflict remains visible")
    disconnected = {i:(0,1,*edge) for i,edge in enumerate(
        [(2,3),(3,4),(4,2),(5,6),(6,7),(7,5)],10)}
    refused = False
    try:
        cycle_from_owners([0,1],sorted(disconnected),disconnected)
    except ValueError:
        refused = True
    require(refused, "Two degree-two cycles cannot become a selected subset cycle")
    return dict(guard_count=retained["guard_count"]+4,
        names=retained["names"]+["maximal_diagonal_Catalan_complete",
        "missing_duplicate_extra_candidate_refusal","disjoint_removal_duplicate_conflict",
        "disconnected_link_no_subset_refusal"],all_passed=True)


def verify_saved():
    held = decode((PREP/"held-preparation.json").read_bytes())
    loaded,before = {},{}
    require(held["status"] == "HELD_UNRUN_SOURCE_FOR_INDEPENDENT_REVIEW", "Exact held preparation")
    require(descriptor(Path(__file__),Path(__file__).read_bytes()) == held["source"], "Exact checker source")
    for name,pin in held["input_records"].items():
        require(not Path(name).is_absolute() and ".." not in Path(name).parts
                and name.startswith("work/962-engineering/") and pin["path"] == name,
                "Fixed first-party input namespace")
        raw = (ROOT/name).read_bytes()
        before[name] = descriptor(ROOT/name,raw)
        require(before[name] == pin, "Fixed saved input identity changed: "+name)
        if name.endswith(".json"):
            loaded[name] = decode(raw)
    report = loaded[held["saved_report"]["path"]]
    worker_held = loaded[held["worker_held"]["path"]]
    capture = loaded[held["capture_receipt"]["path"]]
    require(capture["schema"] == "962-current24-fixed23-saved-edge-removal-once-receipt/v1"
            and capture["report"] == held["saved_report"] and capture["returncode"] == 0
            and capture["failure"] is None and capture["complete_saved_diagnostic"] is True
            and capture["independent_arithmetic_acceptance"] is False,
            "Saved capture/report join only; arithmetic acceptance remained pending")
    require(report["worker_source"] == report["worker_source_after"] == held["worker_source"]
            and report["worker_held"] == report["worker_held_after"] == held["worker_held"],
            "Exact producer source/held before-after joins")
    require(report["input_records_before"] == report["input_records_after"] == worker_held["input_records"]
            and len(worker_held["input_records"]) == 23
            and len(worker_held["inherited_intake_input_records"]) == 15
            and all(worker_held["input_records"].get(k) == v
                    for k,v in worker_held["inherited_intake_input_records"].items()),
            "Exact23/retained15 descriptor maps")
    prior = loaded[report["accepted_prior_flip_report"]["path"]]
    prior_root = loaded[report["accepted_prior_flip_root"]["path"]]
    require(report["accepted_prior_flip_report"] == held["input_records"][report["accepted_prior_flip_report"]["path"]]
            and report["accepted_prior_flip_root"] == held["input_records"][report["accepted_prior_flip_root"]["path"]],
            "Accepted complete earlier flip report/root identities")
    require(prior_root["independent_kernel_completion_accepted"] is True
            and prior_root["finite_family_local_refusals_accepted"] is True
            and (prior_root["association_count"],prior_root["failed_local_patterns"],
                 prior_root["passing_local_patterns"],prior_root["pair_conflicts"]) == (204,65,0,89)
            and prior_root["saved_producer_report"] == report["accepted_prior_flip_report"],
            "Historical accepted full204/65/89 result, no new replay")
    context,points,cells,poor,seeds,protected,rows,nodes = parent_context(loaded,worker_held)
    require(report["schema"] == "962-current24-complete-fixed-word-edge-removal-screen/v1"
            and report["status"] == "COMPLETE_FINITE_LOCAL_SCREEN_APPLICATION_ELIGIBILITY_UNAVAILABLE",
            "Exact fixed-word saved55 schema/status")
    for phase in ("before","after"):
        require(canonical(report["context_"+phase]) == canonical(context)
                and canonical(prior["complete_context_"+phase]) == canonical(context),
                "Complete independent271/499/protected context: "+phase)
        require(hashlib.sha256(canonical(context)).hexdigest() == report[phase+"_snapshot_sha256"]
                == prior[phase+"_snapshot_sha256"], "Complete snapshot digest")
    require(report["full_saved_native_cell_rows"] == rows
            and report["full_saved_coordinate_classification_rows"] == nodes,
            "Every saved native metric/index/connectivity/classification row")
    selected,outside = edge_family(cells,poor,seeds)
    require(canonical(report["outside_degree_route_associations"]) == canonical(outside),
            "Every outside-degree association retained")
    cache = {}
    cavities = [independent_cavity(case,points,cells,protected,cache) for case in selected]
    require(canonical(report["selected_complete_edge_stars"]) == canonical(cavities),
            "All55 link/oldD/Q2/support/sphere/volume/protection rows")
    require(type(report["selected_case_count"]) is int and report["selected_case_count"] == len(cavities)
            and type(report["valid_link_count"]) is int and report["valid_link_count"] == len(cavities),
            "All55 exact valid links")
    templates = {n:polygon_templates(n) for n in range(4,9)}
    owners = feature_index(cells)
    expected = []
    for cavity in cavities:
        cycle = cavity["link"]["cycle"]
        triangulations = sorted(tuple(sorted(tuple(sorted(cycle[i] for i in t)) for t in disk))
                                for disk in templates[len(cycle)])
        require(len(triangulations) == len(set(triangulations)), "Every mapped disk exactly once")
        for ordinal,triangles in enumerate(triangulations,1):
            expected.append(independent_candidate(cavity,triangles,triangulations,ordinal,points,cells,seeds,owners,cache))
    candidate_membership(report["all_candidate_rows"],[r["candidate_ID"] for r in expected])
    require(len(expected) == 1033 and type(report["candidate_count"]) is int
            and report["candidate_count"] == report["conditional_Catalan_bound"] == len(expected),
            "Full1033 conditional Catalan candidate family")
    require(canonical(report["all_candidate_rows"]) == canonical(expected),
            "Every replacement D/Q2/word association/boundary/volume/feature/reason/authority row")
    conflicts,pairs = conflict_certificate(cavities,expected)
    require(canonical(report["conflicts"]) == canonical(conflicts),
            "Full within/cross/duplicate conflict memberships and exact pair union")
    for key in ("procedure_preservation_passed","complete_context_byte_identical","all_finite_rows_retained",
                "all_failed_unavailable_and_outside_rows_retained","all23_descriptor_and_original15_intake_joins_checked"):
        require(report[key] is True, "Complete saved preservation: "+key)
    require(report["complete_application_eligibility"] is None
            and report["region_interface_exterior_or_BIN_evidence"] is None, "Unavailable semantic/owner evidence")
    for key in ("whole_head_embedding_or_nonoverlap_accepted","mesh_application_authorized",
                "optimizer_or_native_called","coordinates_or_connectivity_written",
                "physics_material_LPBF_or_manufacturing_accepted","global_infeasibility_proved",
                "topology_change_necessity_proved","automatic_retry","raw_MSH_BIN_native_fields_or_runtime_body_read"):
        require(report[key] is False, "No elevated authority: "+key)
    local_pass = [r["candidate_ID"] for r in expected if r["local_finite_predicates_passed"]]
    quality_failed = [r["candidate_ID"] for r in expected if not r["all_replacement_exact_quality_gates_passed"]]
    require(type(report["local_finite_pass_count"]) is int and report["local_finite_pass_count"] == len(local_pass),
            "Independently reconstructed finite pass count")
    after = {name:descriptor(ROOT/name,(ROOT/name).read_bytes()) for name in held["input_records"]}
    require(after == before, "Every saved input byte identity remains unchanged")
    return dict(schema="962-current24-independent-saved55-edge-removal-exact-verification/v1",
        complete_finite_family_verified=True,complete_case_count=len(cavities),
        complete_candidate_count=len(expected),outside_degree_association_count=len(outside),
        original_D_Q2_rows=sum(len(c["old_rows"]) for c in cavities),
        strict_support_D_rows=sum(len(c["strict_support_rows"]) for c in cavities),
        replacement_D_Q2_rows=sum(len(c["replacement_exact_rows"]) for c in expected),
        unique_unordered_four_sets_measured=len(cache),
        introduced_feature_rows=sum(len(c["introduced_feature_owner_rows"]) for c in expected),
        complete_conflicting_pair_count=len(pairs),
        exact_conflicting_pair_union_sha256=hashlib.sha256(canonical(sorted(pairs))).hexdigest(),
        conflict_case_products=len(conflicts["cross_case_removed_cell_conflict_products"]),
        conflict_duplicate_four_set_cliques=len(conflicts["duplicate_proposed_cell_cliques"]),
        full_candidate_quality_failure_IDs=quality_failed,full_local_finite_pass_IDs=local_pass,
        confirmed_complete_case_sha256=hashlib.sha256(canonical(cavities)).hexdigest(),
        confirmed_complete_candidate_sha256=hashlib.sha256(canonical(expected)).hexdigest(),
        confirmed_complete_conflicts_sha256=hashlib.sha256(canonical(conflicts)).hexdigest(),
        full271_words499_cells_and_six_typed_hashes_parent_associated=True,
        prior1983_cells66_nodes86_poor_protected=True,
        inputs_before=before,inputs_after=after,complete_application_eligibility=None,
        mesh_application_authorized=False,global_embedding_accepted=False,
        global_infeasibility_or_topology_necessity_proved=False,
        native_or_physical_or_manufacturing_accepted=False,
        limits="Only the complete saved fixed-word55-edge Catalan family. Unknown outside/semantic/interface/exterior/BIN/global evidence stays unavailable; no mesh application or PDE admission.")


if __name__ == "__main__":
    require(sys.flags.isolated == sys.flags.no_site == sys.flags.dont_write_bytecode == 1
            and sys.flags.optimize == 0 and "site" not in sys.modules
            and "_distutils_hack" not in sys.modules, "Selected-B-I-S runtime required")
    require(sys.implementation.name == "cpython" and sys.float_info.radix == 2
            and sys.float_info.mant_dig == 53 and struct.calcsize("d") == 8,
            "Binary64 CPython float required")
    require(len(sys.argv) == 2 and sys.argv[1] == "--verify", "One fixed future operation required")
    guard_result = analytic_guards()
    output = verify_saved()
    output["analytic_guards"] = guard_result
    encoded = (json.dumps(output,indent=2,allow_nan=False)+"\n").encode()
    require(len(encoded) <= CAP, "Complete verifier output must fit32MiB")
    sys.stdout.buffer.write(encoded)



