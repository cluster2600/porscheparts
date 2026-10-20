"""HELD/UNRUN exact intake and pure QF_NRA DAG source; no process or file IO."""
from fractions import Fraction
from itertools import combinations
import copy,hashlib,json,math,struct
REPORT_REL="work/962-engineering/head-star-current110-pass62-application-001/worker-report.json"
CLOSED_REL="work/962-engineering/head-star-current110-pass62-application-root-execution-001/closed-result.json"
BOUNDARY=871731


def coordinate_rows(rows,expected_tags):
    """Strict ordered row/hex association; floats are compared by binary64 representation."""
    if (not isinstance(rows,list) or len(rows)!=len(expected_tags)
            or any(type(t) is not int or t<=0 for t in expected_tags)
            or expected_tags!=sorted(set(expected_tags))):
        raise ValueError("Complete increasing positive coordinate-tag rows required")
    coordinates=[]
    for row,tag in zip(rows,expected_tags):
        if not isinstance(row,dict):raise ValueError("Coordinate row must be an object")
        xyz=row.get("coordinates_mm");bits=row.get("binary64_hex")
        if (row.get("node_tag")!=tag or type(row.get("node_tag")) is not int
                or not isinstance(xyz,list) or len(xyz)!=3 or not isinstance(bits,list) or len(bits)!=3
                or any(type(x) not in (int,float) or not math.isfinite(x) for x in xyz)
                or any(type(h) is not str for h in bits)
                or [float(x).hex() for x in xyz]!=bits):
            raise ValueError("Exact node-tag/finite coordinate/binary64-hex association required")
        coordinates.append([float(x) for x in xyz])
    return coordinates


def need(condition,message):
    if not condition:raise ValueError(message)


def typed_hash(values,fmt):
    return hashlib.sha256(b"".join(struct.pack("<"+fmt,value) for value in values)).hexdigest()


def current_faces(report,parent,closed,held):
    need(parent["decision"]=="ACCEPT_REVIEWED_COORDINATE_ONLY_PARTIAL_IMPROVEMENT_PRESERVE_WHOLE_HEAD_QUALITY_REFUSAL",
        "Accepted current24 parent required")
    for name in ("fresh_native_complete_census_and_procedural_checks_accepted_in_recorded_software_scope",
            "selected66_coordinate_rows_applied_and_saved","unselected1097202_nodes_and_connectivity_boundary_fixed",
            "strict_full_head_quality_rejected","no_source_scientific_or_native_reexecution_by_acceptance"):
        need(parent[name] is True,"Required parent preservation field: "+name)
    need((parent["poor_before"],parent["poor_after"],parent["removed_original_poor"])==(110,24,86),
        "Current accepted partial improvement counts changed")
    need(parent["saved_partial_mesh"]==held["opaque_saved_mesh_identity"],"Saved mesh identity metadata changed")
    need(parent["root_closed"]==held["input_records"][CLOSED_REL],"Closed result association changed")
    need(parent["root_own_review"]==held["input_records"][parent["root_own_review"]["path"]],
        "Root own-review association changed")
    for key in ("independent_peer","independent_bindings"):
        need(parent[key]==held["input_records"][parent[key]["path"]],"Result peer association changed")
    need(parent["remaining16_seed_499_cell_271_context_metadata_scope"]==
        dict(good=475,incident_cells=499,movable=16,poor=24,shared=33,unique_context=271),"Parent remaining scope changed")
    expected=held["input_records"][REPORT_REL]
    captured=closed["outputs"]["worker-report.json"]
    need(captured["sha256"]==expected["sha256"] and captured["bytes"]==expected["bytes"],"Closed report association changed")
    need(report["status"]=="failed_outputs_preserved" and report["procedural_checks_passed"] is True
        and report["saved_mesh_identity_exact"] is True and report["bound_inputs_unchanged"] is True,
        "Accepted procedural report required")
    need(report["after"]==report["saved_reopen"] and report["full_native_census_after_saved_reopen"] is True,
        "Saved reopen complete census required")
    need(report["rejected11_proposed_coordinate_rows_applied"] is False
        and report["actual_whole_head_positive_poor_count"]==24
        and report["actual_whole_head_SICN_gate_passed"] is False,"Preserved rejected proposals/current24 required")
    need((report["setNode_call_count"],report["element_cache_refresh_count"],report["mesh_write_call_count"])==(66,1,1),
        "Original partial application counts changed")
    need(report["mesh_sha256"]==parent["saved_partial_mesh"]["sha256"]
        and report["mesh_bytes"]==parent["saved_partial_mesh"]["bytes"],"Report mesh metadata changed")
    after=report["after"];boundary=after["source_boundary_identity"]
    need(boundary==held["source_boundary_identity"],"Exact saved source-boundary identity changed")
    need(report["comparison"]["source_boundary_identity_unchanged"] is True
        and report["comparison"]["sorted_node_tags_tetra_tags_and_oriented_connectivity_unchanged"] is True
        and report["comparison"]["full_classifications_and_counts_unchanged"] is True,
        "Saved complete boundary/connectivity/classification preservation required")
    quality=after["quality"]["minimum_SICN"]
    need(quality["count"]==3622025 and quality["nonpositive_count"]==0 and quality["below_point1_count"]==24,
        "Complete positive poor scope changed")
    need(quality["minimum"]==parent["minimum_native_SICN_unchanged"] and
        quality["array_sha256"]==held["minimum_SICN_array_sha256"],"Whole-array quality metadata changed")
    census=after["complete_native_census"];stars=census["complete_seed_star_census"]
    need(stars["schema"]=="962-complete-current-poor-seed-stars/v1","Current saved census schema required")
    expected_counts=dict(movable_count=16,prospective_coordinate_variables=48,complete_incident_tetrahedron_count=499,
        initially_positive_poor_incident_tetrahedra=24,initially_good_incident_tetrahedra=475,
        shared_by_multiple_movable_nodes_tetrahedra=33,unique_incident_node_count=271,
        unique_incident_boundary_node_count=179,unique_incident_other_interior_node_count=76)
    for key,value in expected_counts.items():need(type(stars[key]) is int and stars[key]==value,"Complete current count changed: "+key)
    need(stars["all_seed_stars_complete_including_initially_good_and_shared_cells"] is True
        and stars["all_positive_poor_rows_covered_by_movable_stars"] is True,"Complete current saved stars required")
    movable=stars["movable_node_tags"]
    need(isinstance(movable,list) and len(movable)==16 and movable==sorted(set(movable))
        and all(type(t) is int and t>BOUNDARY for t in movable),"Sixteen ordered interior seeds required")
    nodes=stars["unique_incident_nodes"]
    need(isinstance(nodes,list) and len(nodes)==271,"All271 saved context rows required")
    tags=[row["node_tag"] for row in nodes];xyz=coordinate_rows(nodes,tags)
    points=dict(zip(tags,xyz));node_rows=dict(zip(tags,nodes));moving=set(movable)
    need(moving<=set(tags),"Every current seed must have a context row")
    for row in nodes:
        tag=row["node_tag"]
        need(type(row["source_boundary_tag"]) is bool and row["source_boundary_tag"]==(tag<=BOUNDARY),
            "Source boundary tag classification association changed")
        need(type(row["in_movable_seed_set"]) is bool and row["in_movable_seed_set"]==(tag in moving),
            "Saved seed association changed")
        expected_scope="below_dim3" if tag<=BOUNDARY else "dim3"
        need(row["freshly_proved_classification_scope"]==expected_scope,"Saved classification word changed")
    need(sum(t<=BOUNDARY for t in tags)==179 and sum(t>BOUNDARY and t not in moving for t in tags)==76,
        "Complete271 context classifications required")
    cells=stars["complete_incident_tetrahedra"]
    need(isinstance(cells,list) and len(cells)==499,"All499 saved incident cells required")
    cell_tags=[row["tetrahedron_tag"] for row in cells]
    need(cell_tags==sorted(set(cell_tags)) and all(type(t) is int and t>0 for t in cell_tags),
        "Increasing unique positive tetrahedron tags required")
    by_cell={};poor_tags=[];shared=0
    for row in cells:
        tag=row["tetrahedron_tag"];conn=row["node_tags"];q=row["initial_native_SICN"]
        need(isinstance(conn,list) and len(conn)==4 and len(set(conn))==4
            and all(type(t) is int and t in points for t in conn),"Full original ordered connectivity required")
        need(type(row["native_array_index"]) is int and 0<=row["native_array_index"]<3622025,"Valid saved native index required")
        need(type(q) in (int,float) and math.isfinite(q) and 0<q<=1,"Finite positive saved native SICN required")
        is_poor=0<q<0.1
        need(type(row["initially_positive_poor"]) is bool and row["initially_positive_poor"]==is_poor,
            "Saved poor classification changed")
        free=[t for t in conn if t in moving]
        need(free and isinstance(row["movable_node_tags"],list) and
            sorted(row["movable_node_tags"])==sorted(free),"Complete cell/seed incidence required")
        if is_poor:poor_tags.append(tag)
        shared+=len(free)>1;by_cell[tag]=row
    need(len({row["native_array_index"] for row in cells})==499,"Unique complete native indices required")
    need(set(t for row in cells for t in row["node_tags"])==set(tags),"Full271 context union required")
    need(stars["per_movable_node_complete_incident_counts"]==
        [[t,sum(t in row["node_tags"] for row in cells)] for t in movable],"Every seed full incident count required")
    need(stars["unseedable_positive_poor_tetrahedron_tags"]==[],"No unseedable current poor cells permitted")
    need(len(poor_tags)==24 and shared==33 and stars["positive_poor_tetrahedron_tags"]==poor_tags,
        "All24 positive poor cells and33 shared associations required")
    calculated=dict(movable_node_tags_u64=typed_hash(movable,"Q"),
        selected_tetrahedron_tags_u64=typed_hash(cell_tags,"Q"),
        selected_tetrahedron_connectivity_u64=typed_hash([t for row in cells for t in row["node_tags"]],"Q"),
        union_node_tags_u64=typed_hash(tags,"Q"),
        union_coordinates_f64=typed_hash([v for row in xyz for v in row],"d"),
        selected_initial_SICN_f64=typed_hash([row["initial_native_SICN"] for row in cells],"d"))
    need(calculated==stars["ordered_tagged_array_sha256s"]==held["current_typed_array_sha256s"],
        "Full ordered typed census hashes changed")
    poor=census["positive_poor_SICN_cells"]
    rows=poor["complete_tagged_cells"]
    need(poor["total"]==24 and isinstance(rows,list) and len(rows)==24
        and [row["tetrahedron_tag"] for row in rows]==poor_tags,"Complete ordered24 poor-cell rowset required")
    faces=[]
    for row in rows:
        tag=row["tetrahedron_tag"];cell=by_cell[tag];conn=cell["node_tags"]
        need(row["node_tags"]==conn and row["native_array_index"]==cell["native_array_index"],
            "Poor cell/native/corner association changed")
        need(type(row["SICN"]) in (int,float) and float(row["SICN"]).hex()==float(cell["initial_native_SICN"]).hex(),
            "Saved poor quality word changed")
        need(row["coordinates_mm"]==[points[t] for t in conn]
            and row["binary64_hex"]==[node_rows[t]["binary64_hex"] for t in conn],
            "Complete poor-cell coordinate/word association changed")
        need(isinstance(row["coordinates_mm"],list) and len(row["coordinates_mm"])==4
            and [[float(x).hex() for x in p] for p in row["coordinates_mm"]]==row["binary64_hex"],
            "Poor-cell binary64 words required")
        fixed=[t for t in conn if node_rows[t]["source_boundary_tag"]]
        free=[t for t in conn if not node_rows[t]["source_boundary_tag"]]
        need(row["original_boundary_node_count"]==3 and row["interior_node_count"]==1
            and len(fixed)==3 and len(free)==1 and free[0] in moving,
            "Exactly three fixed source-boundary-tag vertices and one current seed required")
        faces.append(dict(tetrahedron_tag=tag,native_array_index=cell["native_array_index"],
            original_ordered_tetrahedron_node_tags=conn,saved_native_SICN=row["SICN"],
            fixed_face_node_tags=fixed,coordinates_mm=[points[t] for t in fixed],
            binary64_hex=[node_rows[t]["binary64_hex"] for t in fixed],
            interior_seed_node_tag=free[0],explicit_source_exterior_face_membership=None,
            source_BIN_membership=None))
    return faces,dict(full_context_rows=271,full_incident_cells=499,current_poor_cells=24,
        good_incident_cells=475,shared_cells=33,movable_nodes=16,source_boundary_context=179,
        other_interior_context=76,all24_have_three_fixed_boundary_tag_vertices=True,
        full_typed_arrays_verified=calculated,source_boundary_identity=boundary,
        explicit_exterior_facet_membership_computed=False,source_BIN_read=False,raw_MSH_read=False)


def prepare_context(report,parent,closed,manifest,selected,held):
    """Reuse accepted complete intake; protect the earlier66/1983/86 scope."""
    faces,intake=current_faces(report,parent,closed,held)
    stars=report["after"]["complete_native_census"]["complete_seed_star_census"]
    rows=stars["complete_incident_tetrahedra"]
    cells={r["tetrahedron_tag"]:tuple(r["node_tags"]) for r in rows}
    need(len({frozenset(c) for c in cells.values()})==499,
         "No duplicate original unordered4-set permitted in saved context")
    points={r["node_tag"]:tuple(float(x) for x in r["coordinates_mm"])
            for r in stars["unique_incident_nodes"]}
    words={r["node_tag"]:tuple(r["binary64_hex"]) for r in stars["unique_incident_nodes"]}
    poor=set(stars["positive_poor_tetrahedron_tags"])
    need(poor=={r["tetrahedron_tag"] for r in faces},"Same complete24 poor set required")
    need(manifest["group_count"]==73 and len(manifest["cases"])==73
         and manifest["all82_variable_nodes_and2482_cells_are_pairwise_disjoint_complete_partitions"] is True
         and manifest["all110_poor2372_good58_shared_memberships_preserved"] is True,
         "Accepted original complete73 partition required")
    groups={r["component_ID"]:r for r in manifest["cases"]}
    accepted=set(selected["component_IDs"]);rejected=set(selected["rejected_component_IDs"])
    need(len(groups)==73 and len(accepted)==62 and len(rejected)==11
         and not accepted&rejected and accepted|rejected==set(groups),"Complete62/11 partition required")
    all_tags=[t for g in groups.values() for t in g["tetrahedron_tags"]]
    all_seeds=[t for g in groups.values() for t in g["movable_node_tags"]]
    need(len(all_tags)==len(set(all_tags))==2482 and len(all_seeds)==len(set(all_seeds))==82,
         "Exact disjoint2482/82 partition required")
    protected_cells={t for i in accepted for t in groups[i]["tetrahedron_tags"]}
    protected_nodes=set(selected["selected_node_tags"])
    need({t for i in rejected for t in groups[i]["tetrahedron_tags"]}==set(cells)
         and {t for i in rejected for t in groups[i]["movable_node_tags"]}==set(stars["movable_node_tags"]),
         "Same complete remaining499/16 scope required")
    need(len(protected_cells)==selected["selected_incident_tetrahedra"]==1983
         and len(protected_nodes)==66 and selected["original_poor_cells_in_passed_groups"]==86
         and not protected_cells&set(cells)
         and not protected_nodes&set(stars["movable_node_tags"]),"Prior66/1983/86 protection required")
    return dict(points=points,words=words,cells=cells,poor=poor,
                seeds=set(stars["movable_node_tags"]),protected_cells=protected_cells,
                protected_nodes=protected_nodes,intake=intake,
                classification_rows=stars["unique_incident_nodes"])


def oriented_boundary(cells):
    """Exact combinatorial oriented boundary and internal cancellation."""
    def canonical(face):
        k=face.index(min(face));return face[k:]+face[:k]
    incidence={}
    for conn in cells:
        for order in [(0,2,1),(0,1,3),(1,2,3),(2,0,3)]:
            face=tuple(conn[i] for i in order)
            incidence.setdefault(tuple(sorted(face)),[]).append(face)
    valid=all(len(rows) in (1,2) and (len(rows)==1 or
              canonical(rows[0])==canonical(rows[1][::-1])) for rows in incidence.values())
    boundary=sorted(canonical(rows[0]) for rows in incidence.values() if len(rows)==1)
    return valid,boundary


def context_snapshot(context):
    """Complete case-specific snapshot, including actual signed-zero word bits."""
    expected={"points","words","cells","poor","seeds","protected_cells",
              "protected_nodes","intake","classification_rows"}
    if set(context)!=expected:raise ValueError("Unexpected context field set")
    return dict(points=[dict(node_tag=t,coordinates_mm=list(p),
                    actual_coordinate_binary64_hex=[float(v).hex() for v in p],
                    actual_coordinate_words_le_hex=struct.pack("<3d",*p).hex())
                for t,p in sorted(context["points"].items())],
        words=[[t,list(w)] for t,w in sorted(context["words"].items())],
        cells=[dict(tetrahedron_tag=t,ordered_node_tags=list(c))
               for t,c in sorted(context["cells"].items())],
        poor=sorted(context["poor"]),seeds=sorted(context["seeds"]),
        protected_cells=sorted(context["protected_cells"]),
        protected_nodes=sorted(context["protected_nodes"]),
        intake=copy.deepcopy(context["intake"]),
        classification_rows=copy.deepcopy(context["classification_rows"]))


EDGE_HELD_SHA256 = 'eec69197200e1d1c1651b2ae172f0ddca379262997d35d8e5461f30d49eda4b7'
EDGE_HELD_BYTES = 20559
EXPECTED_INPUT_MAP_SHA256 = '61a9482457279b33b43ae53aae18c5a7ebc6717e21a72ede8bab0e22e8cdc0e5'
PARENT_REL = 'work/962-engineering/head-star-current110-pass62-application-root-execution-001/result-peer-acceptance.json'
MANIFEST_REL = 'work/962-engineering/head-star-current110-component-sicn-prep-001/component-manifest.json'
SELECTED_REL = 'work/962-engineering/head-star-current110-pass62-apply-prep-002/selected-proposals.json'
EXPECTED_COMPONENTS = (2, 7, 8, 9, 10, 21, 28, 30, 31, 39, 45)
CAP = 32 * 1024**2
# Untested command/parameter plans. No transport or call site exists in this module.
SOLVER_PLAN = dict(argv=['/opt/homebrew/bin/z3', '-in', '-smt2'],
    version_expected_root_metadata='Z3 version 5.1.0 - 64 bit\n',
    source_tag='z3-5.1.0', source_runtime_equivalence=None,
    status_semantics=dict(sat='model candidate only', unsat='solver-attributed; no checked proof',
                          unknown='incomplete; never empty feasibility'),
    unique_or_cross_version_model_claim=False)
SMT_PROLOGUE = ('(set-option :print-success false)\n'
                '(set-option :produce-models true)\n'
                '(set-option :pp.decimal false)\n'
                '(set-logic QF_NRA)\n')
SMT_CHECK = ('(check-sat-using (using-params qfnra-nlsat '
             ':randomize false :shuffle_vars false :reorder false :seed 0 :zero_accuracy 0))\n')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def strict_json(data):
    need(type(data) is bytes, 'Explicit saved JSON bytes required')
    def pairs(rows):
        result = {}
        for name, value in rows:
            need(name not in result, 'Duplicate JSON key')
            result[name] = value
        return result
    def reject(value):
        raise ValueError('Nonfinite JSON token: ' + value)
    return json.loads(data.decode('utf-8'), object_pairs_hook=pairs, parse_constant=reject)


def admit_current(saved_bytes, edge_held_bytes):
    """Pure23-byte-map intake. No path is opened and no source is imported."""
    need(type(edge_held_bytes) is bytes and len(edge_held_bytes) == EDGE_HELD_BYTES
         and hashlib.sha256(edge_held_bytes).hexdigest() == EDGE_HELD_SHA256,
         'Exact accepted edge intake contract required')
    held = strict_json(edge_held_bytes)
    pins = held['input_records']
    need(hashlib.sha256(canonical(pins).encode()).hexdigest() == EXPECTED_INPUT_MAP_SHA256,
         'Original exact23 descriptor map required')
    need(type(saved_bytes) is dict and len(pins) == 23 and set(saved_bytes) == set(pins),
         'Exactly23 existing saved inputs required')
    observed = {}
    for name, pin in pins.items():
        data = saved_bytes[name]
        need(type(data) is bytes and type(pin['bytes']) is int,
             'Input bytes and exact bytecount required')
        observed[name] = dict(path=name, sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))
        need(observed[name] == pin, 'Changed saved input: ' + name)
    report, parent, closed, manifest, selected = [strict_json(saved_bytes[name]) for name in
        (REPORT_REL, PARENT_REL, CLOSED_REL, MANIFEST_REL, SELECTED_REL)]
    context = prepare_context(report, parent, closed, manifest, selected, held)
    groups = {g['component_ID']:g for g in manifest['cases']}
    need(tuple(sorted(selected['rejected_component_IDs'])) == EXPECTED_COMPONENTS,
         'Exactly the complete11 remaining components required')
    blocks = []
    cells_seen = set()
    seeds_seen = set()
    for cid in EXPECTED_COMPONENTS:
        g = groups[cid]
        seeds = g['movable_node_tags']
        tags = g['tetrahedron_tags']
        need(type(cid) is int and len(seeds) in (1, 2)
             and all(type(t) is int and t in context['seeds'] for t in seeds),
             'One/two current seeds per block required')
        need(not seeds_seen.intersection(seeds) and not cells_seen.intersection(tags),
             'Disjoint complete variable/cell blocks required')
        need(set(tags) == {t for t,c in context['cells'].items() if set(c).intersection(seeds)},
             'Every good/shared/poor incident cell belongs to its block')
        need(all(set(context['cells'][t]).intersection(context['seeds']) <= set(seeds) for t in tags),
             'No omitted cross-block variable coupling allowed')
        seeds_seen.update(seeds)
        cells_seen.update(tags)
        blocks.append(dict(component_ID=cid, movable_node_tags=list(seeds), tetrahedron_tags=list(tags)))
    need(seeds_seen == context['seeds'] and cells_seen == set(context['cells']), 'Full16/499 union required')
    rows = report['after']['complete_native_census']['complete_seed_star_census']['complete_incident_tetrahedra']
    return dict(context=context, context_before=context_snapshot(context), blocks=blocks,
                native_cell_rows=copy.deepcopy(rows), input_records=observed,
                edge_held=dict(sha256=EDGE_HELD_SHA256, bytes=EDGE_HELD_BYTES))


def integer_normalization(context):
    """Common K=2^k; no real head arithmetic occurs until a separately admitted call."""
    fractions = {t:tuple(Fraction.from_float(x) for x in p) for t,p in context['points'].items()}
    exponent = 0
    for point in fractions.values():
        for q in point:
            denominator = q.denominator
            need(denominator > 0 and denominator & (denominator - 1) == 0, 'Dyadic denominator required')
            exponent = max(exponent, denominator.bit_length() - 1)
    scale = 1 << exponent
    integers = {}
    for tag, point in fractions.items():
        row = tuple(q * scale for q in point)
        need(all(q.denominator == 1 for q in row), 'Exact common integer coordinates required')
        integers[tag] = tuple(q.numerator for q in row)
    return dict(power_of_two_exponent=exponent, scale_integer=str(scale),
                fixed_coordinate_projection='y=K*x; native x=y/K',
                positive_homogeneous_powers=dict(D=3, S=2, T=4, P=6), integers=integers)


def variable_symbol(component, tag, axis):
    need(type(component) is int and component > 0 and type(tag) is int and tag > 0
         and type(axis) is int and 0 <= axis < 3, 'Exact coordinate identity required')
    return 'c%03d_n%d_%s' % (component, tag, 'xyz'[axis])


class IntegerDAG:
    """Small exact +,-,* expression DAG; no polynomial solver or dense expansion."""
    def __init__(self):
        self.nodes = []
        self.keys = {}
        self.degrees = []
    def node(self, key, record, degree):
        if key not in self.keys:
            self.keys[key] = len(self.nodes)
            self.nodes.append(record)
            self.degrees.append(degree)
        return self.keys[key]
    def integer(self, value):
        need(type(value) is int, 'Exact integer coefficient required')
        return self.node(('integer', value), dict(op='integer', value=str(value)), 0)
    def variable(self, name):
        return self.node(('variable', name), dict(op='variable', symbol=name), 1)
    def binary(self, op, a, b):
        need(op in ('+', '-', '*') and type(a) is int and type(b) is int
             and 0 <= a < len(self.nodes) and 0 <= b < len(self.nodes), 'Earlier exact DAG operands required')
        x, y = self.nodes[a], self.nodes[b]
        if x['op'] == y['op'] == 'integer':
            u, v = int(x['value']), int(y['value'])
            return self.integer(u + v if op == '+' else u - v if op == '-' else u * v)
        degree = self.degrees[a] + self.degrees[b] if op == '*' else max(self.degrees[a], self.degrees[b])
        return self.node((op, a, b), dict(op=op, args=[a, b]), degree)
    def sum(self, values):
        result = self.integer(0)
        for value in values:
            result = self.binary('+', result, value)
        return result
    def subtract(self, a, b):
        return [self.binary('-', x, y) for x,y in zip(a,b)]
    def dot(self, a, b):
        return self.sum(self.binary('*', x, y) for x,y in zip(a,b))
    def cross(self, a, b):
        return [self.binary('-', self.binary('*',a[i],b[j]), self.binary('*',a[j],b[i]))
                for i,j in ((1,2),(2,0),(0,1))]
    def evaluate(self, variables):
        values = []
        for node in self.nodes:
            op = node['op']
            if op == 'integer':
                value = int(node['value'])
            elif op == 'variable':
                value = variables[node['symbol']]
                need(type(value) is int, 'Exact baseline substitution required')
            else:
                a, b = (values[i] for i in node['args'])
                value = a + b if op == '+' else a - b if op == '-' else a * b
            values.append(value)
        return values


def cell_roots(dag, connectivity, points, seeds):
    """Fixed-base determinant preserves native sign and the degree4/6 bounds."""
    fixed = [i for i,t in enumerate(connectivity) if t not in seeds]
    moving = len(connectivity) - len(fixed)
    need(moving in (1, 2), 'Every affected cell has exactly one/two admitted variables')
    base = fixed[0]
    order = [base] + [i for i in range(4) if i != base]
    p = [points[connectivity[i]] for i in order]
    a, b, c = [dag.subtract(row, p[0]) for row in p[1:]]
    determinant = dag.dot(a, dag.cross(b,c))
    if base % 2:
        determinant = dag.binary('*', dag.integer(-1), determinant)
    edges = []
    for i,j in combinations(range(4),2):
        edge = dag.subtract(points[connectivity[i]], points[connectivity[j]])
        edges.append(dag.dot(edge,edge))
    S = dag.sum(edges)
    faces = []
    for face in combinations(range(4),3):
        pivot = next(i for i in face if connectivity[i] not in seeds)
        other = [i for i in face if i != pivot]
        u,v = [dag.subtract(points[connectivity[i]], points[connectivity[pivot]]) for i in other]
        normal = dag.cross(u,v)
        faces.append(dag.dot(normal,normal))
    T = dag.sum(faces)
    P = dag.binary('-', dag.binary('*',dag.integer(3600),dag.binary('*',determinant,determinant)),
                   dag.binary('*',S,T))
    need(dag.degrees[determinant] <= moving and dag.degrees[P] <= (4 if moving == 1 else 6),
         'Exact fixed-base degree scope changed')
    return dict(D=determinant,S=S,T=T,P=P,maximum_total_degree=dag.degrees[P])


def emit_block(admitted, block, normalization):
    context = admitted['context']
    cid = block['component_ID']
    seeds = set(block['movable_node_tags'])
    dag = IntegerDAG()
    integers = normalization['integers']
    variables = [dict(component_ID=cid,node_tag=t,axis=a,symbol=variable_symbol(cid,t,a))
                 for t in sorted(seeds) for a in range(3)]
    baseline_variables = {v['symbol']:integers[v['node_tag']][v['axis']] for v in variables}
    points = {t:[dag.variable(variable_symbol(cid,t,a)) if t in seeds else dag.integer(p[a])
                 for a in range(3)] for t,p in integers.items()}
    by_tag = {r['tetrahedron_tag']:r for r in admitted['native_cell_rows']}
    tags = sorted(block['tetrahedron_tags'], key=lambda t:by_tag[t]['native_array_index'])
    valid,boundary = oriented_boundary([context['cells'][t] for t in tags])
    need(valid and all(t not in seeds for f in boundary for t in f),
         'Own complete oriented boundary must cancel internally and be fixed')
    rows = []
    for tag in tags:
        conn = context['cells'][tag]
        roots = cell_roots(dag,conn,points,seeds)
        rows.append(dict(component_ID=cid,tetrahedron_tag=tag,
            native_array_index=by_tag[tag]['native_array_index'],ordered_node_tags=list(conn),
            moving_node_tags=sorted(set(conn)&seeds),initially_positive_poor=tag in context['poor'],
            roots=roots))
    baseline = dag.evaluate(baseline_variables)
    need(all(baseline[r['roots']['D']] > 0 for r in rows), 'Original exact orientation must be positive')
    volume_root = dag.sum(r['roots']['D'] for r in rows)
    baseline_sum = sum(baseline[r['roots']['D']] for r in rows)
    predicates = []
    for row in rows:
        predicates.extend(dict(name='c%03d_t%d_%s'%(cid,row['tetrahedron_tag'],name),
            component_ID=cid,tetrahedron_tag=row['tetrahedron_tag'],root=row['roots'][name],
            relation='>=' if name=='P' else '>',integer_rhs='0') for name in ('D','S','T','P'))
    predicates.append(dict(name='c%03d_own_volume'%cid,component_ID=cid,root=volume_root,
                           relation='=',integer_rhs=str(baseline_sum)))
    result = dict(component_ID=cid,variables=variables,normalization={k:v for k,v in normalization.items() if k!='integers'},
        nodes=dag.nodes,cell_rows=rows,predicates=predicates,
        exact_oriented_boundary=[list(f) for f in boundary],baseline_scaled_six_volume=str(baseline_sum),
        integer_coefficient_DAG_sha256=hashlib.sha256(canonical(dag.nodes).encode()).hexdigest(),
        complete_application_eligibility=None,application_authorized=False)
    need(len(canonical(result).encode()) <= CAP, 'Full block DAG exceeds32MiB; no truncation')
    return result


def smt_integer(value):
    q = int(value)
    return str(q) if q >= 0 else '(- ' + str(-q) + ')'


def smt_block(block):
    """Only source text is returned; the planned check is never called here."""
    cid = block['component_ID']
    name = lambda i:'d_c%03d_%d'%(cid,i)
    lines = [SMT_PROLOGUE]
    for variable in block['variables']:
        lines.append('(declare-fun '+variable['symbol']+' () Real)\n')
    for i,node in enumerate(block['nodes']):
        if node['op']=='integer':expression=smt_integer(node['value'])
        elif node['op']=='variable':expression=node['symbol']
        else:expression='('+node['op']+' '+ ' '.join(name(j) for j in node['args'])+')'
        lines.append('(define-fun '+name(i)+' () Real '+expression+')\n')
    for predicate in block['predicates']:
        expression='('+predicate['relation']+' '+name(predicate['root'])+' '+smt_integer(predicate['integer_rhs'])+')'
        lines.append('(assert (! '+expression+' :named '+predicate['name']+'))\n')
    lines.append(SMT_CHECK)
    text=''.join(lines)
    need(len(text.encode())<=CAP,'Full SMT text exceeds32MiB; no truncation')
    return text


def emit_all(admitted):
    before = canonical(context_snapshot(admitted['context']))
    need(before == canonical(admitted['context_before']), 'Unchanged complete context required')
    normalization = integer_normalization(admitted['context'])
    blocks = [emit_block(admitted,b,normalization) for b in admitted['blocks']]
    need(len(blocks)==11 and sum(len(b['cell_rows']) for b in blocks)==499
         and sum(len(b['variables']) for b in blocks)==48, 'Complete11/499/48 emission required')
    need(canonical(context_snapshot(admitted['context']))==before, 'Emitter mutated context')
    result = dict(schema='962-current24-coupled-qfnra-exact-DAGs/v1',blocks=blocks,
        context_before=admitted['context_before'],context_after=context_snapshot(admitted['context']),
        original_native_cell_rows=admitted['native_cell_rows'],input_records=admitted['input_records'],
        geometry_and_global_eligibility=None,application_authorized=False,physical_accepted=False)
    need(len(canonical(result).encode())<=CAP,'Complete11-case output exceeds32MiB; no truncation')
    return result


def word_proposal(admitted, mapping_evidence):
    """Full48 mappings -> full271 proposed rows; no validation or mesh mutation.

    A separately authored exact499-cell validator must decide coordinate quality.
    This construction never selects an accepted subset or replaces missing words.
    """
    context = admitted['context']
    before = context_snapshot(context)
    need(canonical(before) == canonical(admitted['context_before']), 'Current context drift')
    wanted = [(b['component_ID'],t,a) for b in admitted['blocks']
              for t in sorted(b['movable_node_tags']) for a in range(3)]
    need(len(wanted) == 48 and type(mapping_evidence) is list and len(mapping_evidence) == 48,
         'Exactly48 mappings for all16 seeds; no partial selection')
    proposed = {t:list(p) for t,p in context['points'].items()}
    records = []
    model_ids = {}
    for evidence, (cid,tag,axis) in zip(mapping_evidence,wanted):
        coord = evidence['coordinate']
        expected = dict(component_ID=cid,node_tag=tag,axis=axis,symbol=variable_symbol(cid,tag,axis))
        need(coord == expected and type(coord['axis']) is int, 'Exact ordered coordinate association required')
        word = evidence['word_u64']
        need(type(word) is int and 0 <= word < 2**64, 'One actual binary64 word required')
        packed = struct.pack('<Q',word)
        value = struct.unpack('<d',packed)[0]
        need(math.isfinite(value) and evidence['word_le_hex'] == packed.hex(), 'Finite word/hex association required')
        model = evidence['model_id']
        need(type(model) is str and len(model)==64 and all(c in '0123456789abcdef' for c in model),
             'Retained model identity required')
        need(cid not in model_ids or model_ids[cid] == model, 'One retained model per component')
        model_ids[cid] = model
        need(type(evidence['events']) is list and evidence['events'], 'Complete oracle event record required')
        proposed[tag][axis] = value
        records.append(dict(component_ID=cid,node_tag=tag,axis='xyz'[axis],symbol=coord['symbol'],
            word_u64=word,word_le_hex=packed.hex(),model_ID=model,events=copy.deepcopy(evidence['events'])))
    need(len(model_ids) == 11, 'All11 components require model-associated mappings')
    rows = [dict(node_tag=t,coordinates_mm=list(p),binary64_hex=[float(x).hex() for x in p],
                 words_le_hex=struct.pack('<3d',*p).hex()) for t,p in sorted(proposed.items())]
    need(len(rows)==271 and canonical(context_snapshot(context))==canonical(before), 'Full unchanged271 context required')
    normalization = integer_normalization(context)
    result = dict(schema='962-current24-qfnra-one-model-word-proposal/v1',
        input_records=copy.deepcopy(admitted['input_records']),context_before=before,
        original_cell_rows=copy.deepcopy(admitted['native_cell_rows']),components=copy.deepcopy(admitted['blocks']),
        proposed_coordinate_rows=rows,coordinate_mapping_records=records,
        mapping_evidence=copy.deepcopy(mapping_evidence),
        normalization={k:v for k,v in normalization.items() if k!='integers'},
        complete_application_eligibility=None,application_authorized=False,global_embedding_accepted=False,
        physical_accepted=False,manufacturing_authorized=False)
    need(len(canonical(result).encode())<=CAP,'Complete word proposal exceeds32MiB; no truncation')
    return result
