"""Independent saved-only Cartesian word validation. SOURCE HELD / UNRUN.

No file, process, solver, emitter, mesh writer or runtime entry point is present.
The caller must separately admit access to all23 named saved byte payloads.
Model-event truth is provenance only; the accepted scope is the actual word vector.
"""

from fractions import Fraction
from itertools import combinations
import hashlib
import json
import math
import struct


INPUT_MAP_SHA256 = "61a9482457279b33b43ae53aae18c5a7ebc6717e21a72ede8bab0e22e8cdc0e5"
PREFIX = "work/962-engineering/"
REPORT = PREFIX + "head-star-current110-pass62-application-001/worker-report.json"
PARENT = PREFIX + "head-star-current110-pass62-application-root-execution-001/result-peer-acceptance.json"
CLOSED = PREFIX + "head-star-current110-pass62-application-root-execution-001/closed-result.json"
MANIFEST = PREFIX + "head-star-current110-component-sicn-prep-001/component-manifest.json"
SELECTED = PREFIX + "head-star-current110-pass62-apply-prep-002/selected-proposals.json"
ANCESTRAL_HELD = PREFIX + "head-star-current24-analytic-apex-prep-001/held-preparation.json"
BOUNDARY = 871731
BLOCKS = ((2, (1393392,), 32, 2, 0),
          (7, (1436404, 1613783), 55, 3, 5),
          (8, (1436405, 1613757), 53, 3, 7),
          (9, (1436406, 1613784), 49, 3, 7),
          (10, (1436407, 1613756), 53, 3, 7),
          (21, (1459657, 1534323), 77, 3, 7),
          (28, (1476316,), 46, 2, 0), (30, (1485102,), 52, 2, 0),
          (31, (1487573,), 22, 1, 0), (39, (1520064,), 32, 1, 0),
          (45, (1549537,), 28, 1, 0))


def need(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def sha(value):
    return hashlib.sha256(value).hexdigest()


def strict_json(payload):
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, "Duplicate JSON object key")
            result[key] = value
        return result
    def bad_constant(value):
        raise ValueError("Nonfinite JSON constant: " + value)
    need(type(payload) is bytes, "Saved payload must be bytes")
    return json.loads(payload.decode("utf-8"), object_pairs_hook=pairs,
                      parse_constant=bad_constant)


def ordered_ints(values, count=None):
    need(type(values) is list and all(type(x) is int and x > 0 for x in values),
         "Positive integer list required")
    need(values == sorted(set(values)), "Complete increasing unique integer list required")
    if count is not None:
        need(len(values) == count, "Complete integer-list count mismatch")
    return values


def fraction_word(word):
    """IEEE754 binary64 exact integer decoder; signed zero stays in the word."""
    need(type(word) is int and 0 <= word < 2**64, "Unsigned64 word required")
    exponent = (word >> 52) & 2047
    significand = word & (2**52 - 1)
    need(exponent != 2047, "NaN/infinity word refused")
    if exponent:
        significand += 2**52
        power = exponent - 1075
    else:
        power = -1074
    value = Fraction(significand * 2**power) if power >= 0 else Fraction(significand, 2**(-power))
    return -value if word >> 63 else value


def coordinate(row, proposed=False):
    need(float.__getformat__("double") in ("IEEE, little-endian","IEEE, big-endian") and
         struct.calcsize("<d") == 8, "Supported IEEE754 binary64 float representation required")
    need(type(row) is dict and type(row.get("node_tag")) is int and row["node_tag"] > 0,
         "Tagged coordinate object required")
    xyz, spellings = row.get("coordinates_mm"), row.get("binary64_hex")
    need(type(xyz) is list and len(xyz) == 3 and type(spellings) is list and len(spellings) == 3,
         "Three coordinate values and spellings required")
    words, values = [], []
    for value, spelling in zip(xyz, spellings):
        need(type(value) in (int, float), "Boolean or nonnumeric coordinate refused")
        numeric = float(value)
        need(math.isfinite(numeric) and type(spelling) is str and numeric.hex() == spelling,
             "Finite canonical binary64 hex roundtrip required")
        word = int.from_bytes(struct.pack("<d", numeric), "little")
        words.append(word)
        values.append(fraction_word(word))
    raw = b"".join(w.to_bytes(8, "little") for w in words).hex()
    if proposed:
        need(set(row) == {"node_tag", "coordinates_mm", "binary64_hex", "words_le_hex"},
             "Unexpected proposed coordinate fields")
        need(row["words_le_hex"] == raw, "All three actual coordinate words must agree")
    return tuple(values), tuple(words), raw


def quality_gate(determinant, edge_sum, gram_sum):
    return determinant > 0 and edge_sum > 0 and gram_sum > 0 and 3600*determinant**2-edge_sum*gram_sum >= 0


def metrics(vertices):
    """Six-term Cartesian determinant, all6 edges, all4 face Gram determinants."""
    need(len(vertices) == 4 and all(len(p) == 3 for p in vertices), "Four3D vertices required")
    a, b, c = [tuple(p[i] - vertices[0][i] for i in range(3)) for p in vertices[1:]]
    determinant = (a[0]*b[1]*c[2] + a[1]*b[2]*c[0] + a[2]*b[0]*c[1]
                   - a[2]*b[1]*c[0] - a[1]*b[0]*c[2] - a[0]*b[2]*c[1])
    edge_sum = sum(sum((vertices[i][k]-vertices[j][k])**2 for k in range(3))
                   for i, j in combinations(range(4), 2))
    gram_sum = Fraction(0)
    for i, j, k in combinations(range(4), 3):
        u = tuple(vertices[j][d]-vertices[i][d] for d in range(3))
        v = tuple(vertices[k][d]-vertices[i][d] for d in range(3))
        uu, vv, uv = sum(x*x for x in u), sum(x*x for x in v), sum(x*y for x, y in zip(u, v))
        gram_sum += uu*vv-uv*uv
    margin = 3600*determinant*determinant-edge_sum*gram_sum
    return dict(D=determinant, S=edge_sum, T=gram_sum, margin=margin,
                Q_squared=36*determinant*determinant/(edge_sum*gram_sum)
                if edge_sum > 0 and gram_sum > 0 else None,
                gate=quality_gate(determinant,edge_sum,gram_sum))


def encoded_fraction(value):
    return None if value is None else [value.numerator, value.denominator]


def encoded_metrics(value):
    return {key: (item if type(item) is bool else encoded_fraction(item))
            for key, item in value.items()}


def boundary_faces(cells):
    """Local oriented incidence only: no whole-mesh incidence or embedding claim."""
    incidence = {}
    def cyclic(face):
        rotations = (face, face[1:]+face[:1], face[2:]+face[:2])
        return min(rotations)
    for conn in cells:
        need(len(conn) == 4 and len(set(conn)) == 4, "Distinct TET4 vertices required")
        for face in ((conn[1],conn[2],conn[3]), (conn[0],conn[3],conn[2]),
                     (conn[0],conn[1],conn[3]), (conn[0],conn[2],conn[1])):
            incidence.setdefault(tuple(sorted(face)), []).append(face)
    exposed = []
    for key in sorted(incidence):
        rows = incidence[key]
        need(len(rows) in (1, 2), "Local nonmanifold face multiplicity")
        if len(rows) == 2:
            need(cyclic(rows[0]) == cyclic(tuple(reversed(rows[1]))),
                 "Local internal face orientation fails cancellation")
        else:
            exposed.append(cyclic(rows[0]))
    return sorted(exposed), sum(len(v) == 2 for v in incidence.values())


def typed_digest(values, code):
    return sha(b"".join(struct.pack("<"+code, v) for v in values))


def proposed_word_rows(rows, tags, seeds, original_words):
    need(type(rows) is list and all(type(r) is dict for r in rows) and
         [r.get("node_tag") for r in rows] == tags, "Complete increasing proposed coordinate rows required")
    points, words = {}, {}
    for row in rows:
        point, word, _ = coordinate(row,proposed=True)
        tag = row["node_tag"]
        points[tag], words[tag] = point,word
        if tag not in seeds:
            need(word == original_words[tag], "Fixed/context/protected signed word changed")
    return points,words


def rebuild_baseline(saved_payloads, input_records):
    """Fresh independent schema/lineage adapter; no producer/helper imports."""
    need(type(input_records) is dict and len(input_records) == 23 and
         sha(canonical(input_records)) == INPUT_MAP_SHA256, "Frozen23 descriptor map required")
    need(type(saved_payloads) is dict and set(saved_payloads) == set(input_records),
         "Exactly all23 saved payloads required")
    for path, descriptor in input_records.items():
        need(set(descriptor) == {"path", "sha256", "bytes"} and descriptor["path"] == path,
             "Exact path descriptor required")
        raw = saved_payloads[path]
        need(type(raw) is bytes and len(raw) == descriptor["bytes"] and sha(raw) == descriptor["sha256"],
             "Saved input bytes differ: " + path)
    report, parent, closed, manifest, selected, held = [strict_json(saved_payloads[p])
        for p in (REPORT, PARENT, CLOSED, MANIFEST, SELECTED, ANCESTRAL_HELD)]
    need(parent["decision"] == "ACCEPT_REVIEWED_COORDINATE_ONLY_PARTIAL_IMPROVEMENT_PRESERVE_WHOLE_HEAD_QUALITY_REFUSAL",
         "Accepted current24 parent required")
    for flag in ("fresh_native_complete_census_and_procedural_checks_accepted_in_recorded_software_scope",
                 "selected66_coordinate_rows_applied_and_saved", "unselected1097202_nodes_and_connectivity_boundary_fixed",
                 "strict_full_head_quality_rejected", "no_source_scientific_or_native_reexecution_by_acceptance"):
        need(parent[flag] is True, "Required parent scope: " + flag)
    need((parent["poor_before"], parent["poor_after"], parent["removed_original_poor"]) == (110,24,86),
         "Accepted110/24/86 scope changed")
    need(parent["remaining16_seed_499_cell_271_context_metadata_scope"] ==
         dict(good=475,incident_cells=499,movable=16,poor=24,shared=33,unique_context=271),
         "Accepted remaining complete-star scope mismatch")
    need(parent["saved_partial_mesh"] == held["opaque_saved_mesh_identity"] and
         parent["root_closed"] == input_records[CLOSED], "Parent/capture identity mismatch")
    for role in ("root_own_review", "independent_peer", "independent_bindings"):
        need(parent[role] == input_records[parent[role]["path"]], "Parent review association mismatch")
    captured = closed["outputs"]["worker-report.json"]
    need((captured["sha256"], captured["bytes"]) == (input_records[REPORT]["sha256"], input_records[REPORT]["bytes"]),
         "Closed saved report association mismatch")
    need(report["status"] == "failed_outputs_preserved" and report["after"] == report["saved_reopen"],
         "Preserved refused head and saved reopen required")
    for flag in ("procedural_checks_passed", "saved_mesh_identity_exact", "bound_inputs_unchanged",
                 "full_native_census_after_saved_reopen"):
        need(report[flag] is True, "Saved procedural preservation required")
    need(report["actual_whole_head_positive_poor_count"] == 24 and
         report["actual_whole_head_SICN_gate_passed"] is False and
         report["rejected11_proposed_coordinate_rows_applied"] is False,
         "Original24 refusal and rejected proposals must remain preserved")
    need((report["setNode_call_count"],report["element_cache_refresh_count"],report["mesh_write_call_count"]) == (66,1,1),
         "Prior66 coordinate application identity mismatch")
    need((report["mesh_sha256"],report["mesh_bytes"]) ==
         (parent["saved_partial_mesh"]["sha256"],parent["saved_partial_mesh"]["bytes"]),
         "Report/accepted saved mesh identity mismatch")
    identity = report["selected_coordinate_identity"]
    need(identity["selected_nodes"] == 66 and identity["all_unselected_coordinate_bits_identical"] is True and
         identity["all_selected_coordinate_bits_equal_proposal"] is True and identity["signed_zero_included"] is True,
         "Saved accepted66 word identity scope mismatch")
    after = report["after"]
    need(after["source_boundary_identity"] == held["source_boundary_identity"], "Inherited boundary identity mismatch")
    for flag in ("source_boundary_identity_unchanged", "sorted_node_tags_tetra_tags_and_oriented_connectivity_unchanged",
                 "full_classifications_and_counts_unchanged"):
        need(report["comparison"][flag] is True, "Saved fixed topology/classification association mismatch")
    native_quality = after["quality"]["minimum_SICN"]
    need((native_quality["count"],native_quality["nonpositive_count"],native_quality["below_point1_count"]) == (3622025,0,24)
         and native_quality["array_sha256"] == held["minimum_SICN_array_sha256"], "Whole-array identity mismatch")
    stars = after["complete_native_census"]["complete_seed_star_census"]
    need(stars["schema"] == "962-complete-current-poor-seed-stars/v1", "Saved complete-star schema mismatch")
    expected_counts = dict(movable_count=16, prospective_coordinate_variables=48,
        complete_incident_tetrahedron_count=499, initially_positive_poor_incident_tetrahedra=24,
        initially_good_incident_tetrahedra=475, shared_by_multiple_movable_nodes_tetrahedra=33,
        unique_incident_node_count=271, unique_incident_boundary_node_count=179,
        unique_incident_other_interior_node_count=76)
    for key, value in expected_counts.items():
        need(type(stars[key]) is int and stars[key] == value, "Complete-star count mismatch: " + key)
    need(stars["all_seed_stars_complete_including_initially_good_and_shared_cells"] is True and
         stars["all_positive_poor_rows_covered_by_movable_stars"] is True and
         stars["unseedable_positive_poor_tetrahedron_tags"] == [], "Incomplete saved seed stars")
    seeds = ordered_ints(stars["movable_node_tags"], 16)
    nodes = stars["unique_incident_nodes"]
    need(type(nodes) is list and len(nodes) == 271, "All271 context nodes required")
    node_tags = ordered_ints([r["node_tag"] for r in nodes], 271)
    need(set(seeds) <= set(node_tags) and all(t > BOUNDARY for t in seeds), "Interior seed association mismatch")
    points, words = {}, {}
    for row in nodes:
        tag = row["node_tag"]
        point, bits, _ = coordinate(row)
        points[tag], words[tag] = point, bits
        need(type(row["source_boundary_tag"]) is bool and row["source_boundary_tag"] == (tag <= BOUNDARY),
             "Boundary tag classification mismatch")
        need(type(row["in_movable_seed_set"]) is bool and row["in_movable_seed_set"] == (tag in seeds),
             "Seed classification mismatch")
        need(row["freshly_proved_classification_scope"] == ("below_dim3" if tag <= BOUNDARY else "dim3"),
             "Saved classification label mismatch")
    need(sum(t <= BOUNDARY for t in node_tags) == 179 and
         sum(t > BOUNDARY and t not in seeds for t in node_tags) == 76, "179/76 fixed context mismatch")
    rows = stars["complete_incident_tetrahedra"]
    need(type(rows) is list and len(rows) == 499, "All499 original cell rows required")
    cell_tags = ordered_ints([r["tetrahedron_tag"] for r in rows], 499)
    cells, indices, poor, shared = {}, [], [], []
    for row in rows:
        tag, conn, idx = row["tetrahedron_tag"], row["node_tags"], row["native_array_index"]
        need(type(conn) is list and len(conn) == len(set(conn)) == 4 and
             all(type(t) is int and t in points for t in conn), "Original ordered TET4 connectivity required")
        need(type(idx) is int and 0 <= idx < 3622025, "Native array index mismatch")
        free = sorted(set(conn) & set(seeds))
        need(len(free) in (1,2) and row["movable_node_tags"] == free, "Exact one/two seed incidence required")
        q = row["initial_native_SICN"]
        need(type(q) in (int,float) and math.isfinite(q) and 0 < q <= 1 and
             type(row["initially_positive_poor"]) is bool and row["initially_positive_poor"] == (q < 0.1),
             "Saved native quality classification mismatch")
        if row["initially_positive_poor"]:
            poor.append(tag)
        if len(free) == 2:
            shared.append(tag)
        cells[tag], indices = tuple(conn), indices + [idx]
    need(len(set(indices)) == len({frozenset(c) for c in cells.values()}) == 499,
         "Duplicate native index or unordered cell")
    need(set(t for c in cells.values() for t in c) == set(node_tags), "Complete271 union mismatch")
    need(len(poor) == 24 and len(shared) == 33 and stars["positive_poor_tetrahedron_tags"] == poor,
         "Exact24poor/33shared association mismatch")
    need(stars["per_movable_node_complete_incident_counts"] ==
         [[t, sum(t in c for c in cells.values())] for t in seeds], "Complete per-seed incidence mismatch")
    arrays = dict(movable_node_tags_u64=typed_digest(seeds,"Q"),
        selected_tetrahedron_tags_u64=typed_digest(cell_tags,"Q"),
        selected_tetrahedron_connectivity_u64=typed_digest([t for c in cells.values() for t in c],"Q"),
        union_node_tags_u64=typed_digest(node_tags,"Q"),
        union_coordinates_f64=sha(b"".join(w.to_bytes(8,"little") for t in node_tags for w in words[t])),
        selected_initial_SICN_f64=typed_digest([r["initial_native_SICN"] for r in rows],"d"))
    need(arrays == stars["ordered_tagged_array_sha256s"] == held["current_typed_array_sha256s"],
         "Saved typed arrays differ")
    poor_rows = after["complete_native_census"]["positive_poor_SICN_cells"]
    need(poor_rows["total"] == 24 and [r["tetrahedron_tag"] for r in poor_rows["complete_tagged_cells"]] == poor,
         "Complete independently tagged24 rows mismatch")
    by_tag = {r["tetrahedron_tag"]: r for r in rows}
    by_node = {r["node_tag"]: r for r in nodes}
    for row in poor_rows["complete_tagged_cells"]:
        original = by_tag[row["tetrahedron_tag"]]
        need(row["node_tags"] == original["node_tags"] and row["native_array_index"] == original["native_array_index"]
             and struct.pack("<d",row["SICN"]) == struct.pack("<d",original["initial_native_SICN"]),
             "Poor native/tag/quality association mismatch")
        need(row["binary64_hex"] == [by_node[t]["binary64_hex"] for t in row["node_tags"]] and
             b"".join(struct.pack("<3d",*p) for p in row["coordinates_mm"]) ==
             b"".join(w.to_bytes(8,"little") for t in row["node_tags"] for w in words[t]),
             "Poor coordinate words mismatch")
    need(manifest["group_count"] == len(manifest["cases"]) == 73 and
         manifest["all82_variable_nodes_and2482_cells_are_pairwise_disjoint_complete_partitions"] is True and
         manifest["all110_poor2372_good58_shared_memberships_preserved"] is True, "Original complete73 partition required")
    groups = {r["component_ID"]: r for r in manifest["cases"]}
    accepted = ordered_ints(selected["component_IDs"],62)
    rejected = ordered_ints(selected["rejected_component_IDs"],11)
    need(len(groups) == 73 and not set(accepted)&set(rejected) and set(accepted+rejected) == set(groups),
         "Complete accepted62/rejected11 partition mismatch")
    all_cells = [t for g in groups.values() for t in g["tetrahedron_tags"]]
    all_seeds = [t for g in groups.values() for t in g["movable_node_tags"]]
    need(len(all_cells) == len(set(all_cells)) == 2482 and len(all_seeds) == len(set(all_seeds)) == 82,
         "Original2482/82 disjoint partition mismatch")
    protected_cells = sorted(t for i in accepted for t in groups[i]["tetrahedron_tags"])
    protected_nodes = ordered_ints(selected["selected_node_tags"],66)
    improved = sorted(t for i in accepted for t in groups[i]["initially_positive_poor_tetrahedron_tags"])
    need(len(protected_cells) == selected["selected_incident_tetrahedra"] == 1983 and len(improved) == 86 and
         selected["original_poor_cells_in_passed_groups"] == 86 and not set(protected_cells)&set(cells) and
         not set(protected_nodes)&set(seeds), "Prior66/1983/86 protected scope mismatch")
    need(protected_nodes == sorted(t for i in accepted for t in groups[i]["movable_node_tags"]),
         "Protected66 tag association mismatch")
    components = []
    for component_ID, expected_seeds, count, poor_count, shared_count in BLOCKS:
        group = groups[component_ID]
        members = ordered_ints(group["tetrahedron_tags"],count)
        free = ordered_ints(group["movable_node_tags"],len(expected_seeds))
        need(tuple(free) == expected_seeds and set(members) == {t for t,c in cells.items() if set(c)&set(free)},
             "Complete block incident-cell membership mismatch")
        need(group["initially_positive_poor_tetrahedron_tags"] == [t for t in members if t in poor] and
             group["initially_good_tetrahedron_tags"] == [t for t in members if t not in poor] and
             group["shared_by_multiple_movable_nodes_tetrahedron_tags"] == [t for t in members if t in shared] and
             sum(t in poor for t in members) == poor_count and sum(t in shared for t in members) == shared_count,
             "Block poor/good/shared rows mismatch")
        union = sorted({t for cell in members for t in cells[cell]})
        need(group["all_incident_node_tags"] == union and
             group["fixed_context_node_tags"] == sorted(set(union)-set(free)) and
             group["fixed_source_boundary_node_tags"] == [t for t in union if t <= BOUNDARY] and
             group["fixed_other_interior_node_tags"] == [t for t in union if t > BOUNDARY and t not in free],
             "Full block context classification mismatch")
        components.append(dict(component_ID=component_ID,movable_node_tags=free,tetrahedron_tags=members))
    need(rejected == [b[0] for b in BLOCKS] and
         sorted(t for c in components for t in c["tetrahedron_tags"]) == cell_tags and
         sorted(t for c in components for t in c["movable_node_tags"]) == seeds, "Complete11/499/16 coverage mismatch")
    intake = dict(full_context_rows=271,full_incident_cells=499,current_poor_cells=24,good_incident_cells=475,
        shared_cells=33,movable_nodes=16,source_boundary_context=179,other_interior_context=76,
        all24_have_three_fixed_boundary_tag_vertices=True,full_typed_arrays_verified=arrays,
        source_boundary_identity=after["source_boundary_identity"],explicit_exterior_facet_membership_computed=False,
        source_BIN_read=False,raw_MSH_read=False)
    for row in poor_rows["complete_tagged_cells"]:
        need(sum(t <= BOUNDARY for t in row["node_tags"]) == 3 and
             row["original_boundary_node_count"] == 3 and row["interior_node_count"] == 1,
             "Original24 fixed-face seed association mismatch")
    snapshot = dict(points=[dict(node_tag=r["node_tag"],coordinates_mm=r["coordinates_mm"],
        actual_coordinate_binary64_hex=r["binary64_hex"],
        actual_coordinate_words_le_hex=b"".join(w.to_bytes(8,"little") for w in words[r["node_tag"]]).hex()) for r in nodes],
        words=[[r["node_tag"],r["binary64_hex"]] for r in nodes],
        cells=[dict(tetrahedron_tag=t,ordered_node_tags=list(c)) for t,c in cells.items()],
        poor=poor,seeds=seeds,protected_cells=protected_cells,protected_nodes=protected_nodes,
        intake=intake,classification_rows=nodes)
    return dict(points=points,words=words,cells=cells,rows=rows,poor=poor,seeds=seeds,
        components=components,snapshot=snapshot,protected_nodes=protected_nodes,protected_cells=protected_cells,
        improved_cells=improved,boundary_identity=after["source_boundary_identity"])


def validate_proposal(proposal, saved_payloads, input_records):
    """One complete11-block actual-word vector; no partial acceptance or alternate model."""
    baseline = rebuild_baseline(saved_payloads, input_records)
    need(type(proposal) is dict and proposal.get("schema") == "962-current24-qfnra-one-model-word-proposal/v1",
         "Complete one-model word proposal schema required")
    need(proposal.get("complete_application_eligibility", "missing") is None,
         "Application eligibility must remain unavailable")
    for flag in ("application_authorized", "global_embedding_accepted", "physical_accepted", "manufacturing_authorized"):
        need(proposal.get(flag) is False, "Proposal cannot grant authority: " + flag)
    need(canonical(proposal.get("input_records")) == canonical(input_records) and
         canonical(proposal.get("context_before")) == canonical(baseline["snapshot"]), "Original full context mismatch")
    need(canonical(proposal.get("original_cell_rows")) == canonical(baseline["rows"]) and
         canonical(proposal.get("components")) == canonical(baseline["components"]), "Complete original499/11 association mismatch")
    rows = proposal.get("proposed_coordinate_rows")
    tags = list(baseline["points"])
    seeds = set(baseline["seeds"])
    final_points,final_words = proposed_word_rows(rows,tags,seeds,baseline["words"])
    mappings = proposal.get("coordinate_mapping_records")
    need(type(mappings) is list and len(mappings) == 48, "All48 coordinate mapping records required")
    expected = [(c["component_ID"],t,axis) for c in baseline["components"]
                for t in c["movable_node_tags"] for axis in ("x","y","z")]
    need([(r.get("component_ID"),r.get("node_tag"),r.get("axis")) for r in mappings] == expected,
         "Complete increasing block/node/axis mapping mismatch")
    symbols, model_ids = set(), {}
    for row, (component_ID,tag,axis) in zip(mappings,expected):
        need(set(row) == {"component_ID","node_tag","axis","symbol","word_u64","word_le_hex","model_ID","events"}
             and type(row["component_ID"]) is int and type(row["node_tag"]) is int,
             "Exact typed coordinate mapping fields required")
        word = final_words[tag][("x","y","z").index(axis)]
        need(type(row.get("word_u64")) is int and row["word_u64"] == word and
             row.get("word_le_hex") == word.to_bytes(8,"little").hex(), "Model/actual word association mismatch")
        need(type(row.get("symbol")) is str and row["symbol"] and row["symbol"] not in symbols,
             "Unique coordinate symbol required")
        symbols.add(row["symbol"])
        need(type(row.get("model_ID")) is str and row["model_ID"] and type(row.get("events")) is list and row["events"],
             "Retained nonempty model/event provenance required")
        model_ids.setdefault(component_ID,row["model_ID"])
        need(model_ids[component_ID] == row["model_ID"], "One retained model per block required")
    cell_results, component_results = [], []
    before_metrics = {}
    by_tag = {r["tetrahedron_tag"]:r for r in baseline["rows"]}
    for tag, conn in baseline["cells"].items():
        old = metrics([baseline["points"][t] for t in conn])
        need(old["D"] > 0 and old["S"] > 0 and old["T"] > 0, "Saved baseline contains nonpositive cell")
        need((not old["gate"]) == (tag in baseline["poor"]), "Exact baseline/native poor-set mismatch")
        before_metrics[tag] = old
    for component in baseline["components"]:
        members = component["tetrahedron_tags"]
        exposed, internal_count = boundary_faces([baseline["cells"][t] for t in members])
        need(all(not seeds.intersection(face) for face in exposed), "Moving seed on exposed local face: incomplete star")
        exposed_words = [dict(oriented_node_tags=list(face),
            words_le_hex=[b"".join(w.to_bytes(8,"little") for w in baseline["words"][t]).hex() for t in face]) for face in exposed]
        need(all(final_words[t] == baseline["words"][t] for face in exposed for t in face),
             "Exposed oriented-face coordinate words changed")
        old_volume = sum((before_metrics[t]["D"] for t in members),Fraction(0))/6
        local_final = {t:metrics([final_points[n] for n in baseline["cells"][t]]) for t in members}
        new_volume = sum((v["D"] for v in local_final.values()),Fraction(0))/6
        component_results.append(dict(component_ID=component["component_ID"],
            movable_node_tags=component["movable_node_tags"],tetrahedron_tags=members,
            exposed_oriented_faces=exposed_words,internal_cancelled_face_pairs=internal_count,
            signed_volume_before_mm3=encoded_fraction(old_volume),signed_volume_after_mm3=encoded_fraction(new_volume),
            exact_own_volume_equal=old_volume == new_volume,
            local_quality_failed_cell_tags=[t for t in members if not local_final[t]["gate"]]))
    # Fresh combined check. Do not reuse the per-component candidate metrics.
    for tag, conn in baseline["cells"].items():
        result = metrics([final_points[t] for t in conn])
        reasons = []
        for key in ("D","S","T"):
            if result[key] <= 0:
                reasons.append(key+"_not_strictly_positive")
        if result["margin"] < 0:
            reasons.append("3600_D_squared_minus_S_times_T_negative")
        cell_results.append(dict(tetrahedron_tag=tag,native_array_index=by_tag[tag]["native_array_index"],
            original_ordered_node_tags=list(conn),initially_positive_poor=tag in baseline["poor"],
            shared_by_two_moving_seeds=len(seeds.intersection(conn)) == 2,
            before=encoded_metrics(before_metrics[tag]),after=encoded_metrics(result),failure_reasons=reasons))
    combined_faces, combined_internal = boundary_faces(list(baseline["cells"].values()))
    need(all(not seeds.intersection(face) and
             all(final_words[t] == baseline["words"][t] for t in face) for face in combined_faces),
         "Combined499 exposed oriented face is not fixed")
    failed = [r["tetrahedron_tag"] for r in cell_results if not r["after"]["gate"]]
    volumes_ok = all(r["exact_own_volume_equal"] for r in component_results)
    accepted = not failed and volumes_ok
    return dict(schema="962-current24-independent499-word-validation/v1",
        status="COMPLETE_WORD_QUALITY_VECTOR_ACCEPTED" if accepted else "COMPLETE_WORD_VECTOR_REFUSED",
        complete11_blocks=True,complete499_cells=True,complete48_mappings=True,
        full271_context_words_checked=True,fixed255_context_words_unchanged=True,
        preserved_prior66_nodes=baseline["protected_nodes"],preserved_prior1983_cells=baseline["protected_cells"],
        preserved_prior86_improved_cells=baseline["improved_cells"],
        source_boundary_identity_inherited=baseline["boundary_identity"],
        proposal_canonical_sha256=sha(canonical(proposal)),context_before=baseline["snapshot"],
        proposed_coordinate_rows=rows,
        original_cell_rows=baseline["rows"],component_results=component_results,cell_results=cell_results,
        combined499_exposed_oriented_faces=[list(face) for face in combined_faces],
        combined499_internal_cancelled_face_pairs=combined_internal,
        failed_cell_tags=failed,exact_all11_own_volumes_equal=volumes_ok,
        actual_binary64_word_quality_vector_accepted=accepted,
        coordinate_mapping_records=mappings,model_event_truth_independently_verified=False,
        nearest_word_rounding_independently_verified=False,
        outside_saved271_coordinate_words_newly_observed=False,
        whole_mesh_incidence_or_global_embedding_verified=False,application_eligible=None,
        geometry_or_native_application_authorized=False,strength_or_LPBF_qualified=False,
        manufacturing_authorized=False,automatic_retry_authorized=False)
