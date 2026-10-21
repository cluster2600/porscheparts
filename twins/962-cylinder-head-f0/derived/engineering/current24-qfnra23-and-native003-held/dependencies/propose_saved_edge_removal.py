"""HELD SOURCE ONLY: complete fixed-word degree4..8 seed-edge removal screen.

No entrypoint/file IO/runtime/mesh writer/actual/launch or execution authority.
All functions and fixtures are UNRUN. Strict-convex local certificates do not
establish whole-head, semantic-interface, material or manufacturing acceptance.
"""
from fractions import Fraction
import copy
import hashlib
from itertools import combinations
import json
import math
import struct

REPORT_REL="work/962-engineering/head-star-current110-pass62-application-001/worker-report.json"
CLOSED_REL="work/962-engineering/head-star-current110-pass62-application-root-execution-001/closed-result.json"
BOUNDARY=871731

# Frozen saved incidence identities, copied from accepted reason accounting; no geometry computation.
EXPECTED_EDGE_DEGREES={'edge:123712,1436406': 6, 'edge:223544,1520064': 4, 'edge:223689,1520064': 4, 'edge:224470,1520064': 5, 'edge:250618,1549537': 7, 'edge:251580,1549537': 4, 'edge:251581,1549537': 4, 'edge:332107,1436407': 6, 'edge:353122,1485102': 8, 'edge:353124,1534323': 8, 'edge:355230,1485102': 4, 'edge:355231,1485102': 5, 'edge:355232,1534323': 5, 'edge:355233,1534323': 4, 'edge:356628,1534323': 6, 'edge:357990,1485102': 6, 'edge:362061,1459657': 4, 'edge:362062,1459657': 5, 'edge:362640,1459657': 8, 'edge:431665,1476316': 7, 'edge:431981,1476316': 8, 'edge:432123,1476316': 5, 'edge:517789,1436405': 6, 'edge:626184,1487573': 5, 'edge:626352,1487573': 4, 'edge:627517,1487573': 7, 'edge:64520,1393392': 5, 'edge:64982,1393392': 5, 'edge:65123,1393392': 4, 'edge:66221,1393392': 6, 'edge:735799,1436404': 7, 'edge:866059,1436405': 5, 'edge:866059,1613757': 4, 'edge:866062,1436405': 5, 'edge:866062,1613757': 4, 'edge:866095,1436404': 5, 'edge:866095,1613783': 4, 'edge:866248,1613756': 7, 'edge:866364,1436407': 5, 'edge:866364,1613756': 4, 'edge:866366,1436407': 5, 'edge:866366,1613756': 4, 'edge:866572,1613757': 7, 'edge:866966,1436406': 5, 'edge:866966,1613784': 4, 'edge:867101,1613783': 5, 'edge:868045,1613784': 7, 'edge:868201,1436404': 5, 'edge:868201,1613783': 4, 'edge:868245,1436406': 5, 'edge:868245,1613784': 4, 'edge:869526,1613784': 4, 'edge:870008,1613756': 4, 'edge:870364,1613757': 4, 'edge:870846,1613783': 4}

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


def rational(value):
    return dict(numerator=str(value.numerator),denominator=str(value.denominator))


def subtract(a,b):
    return [x-y for x,y in zip(a,b)]


def dot(a,b):
    return sum(x*y for x,y in zip(a,b))


def cross(a,b):
    return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]


def exact_quality(coordinates):
    if len(coordinates)!=4 or any(len(p)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in p) for p in coordinates):
        raise ValueError('Four finite binary64 triples required')
    p=[[Fraction.from_float(float(x)) for x in row] for row in coordinates]
    a,e2,e3=[subtract(row,p[0]) for row in p[1:]]
    b=[2*y-x for x,y in zip(a,e2)];c=[3*z-x-y for x,y,z in zip(a,e2,e3)]
    determinant=dot(a,cross(e2,e3))
    norm2=dot(a,a)+dot(b,b)/3+dot(c,c)/6
    bc,ca,ab=cross(b,c),cross(c,a),cross(a,b)
    cofactor2=dot(bc,bc)/18+dot(ca,ca)/6+dot(ab,ab)/3
    q2=18*determinant**2/(norm2*cofactor2) if norm2*cofactor2>0 else None
    return determinant,q2


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


def canonical_bytes(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")


def link_cycle(context,case):
    """Validate a complete edge star combinatorially; never infer geometric order."""
    edge=tuple(case["central_edge"]);tags=case["removed_cell_tags"]
    reasons=[];opposite=[];adj={}
    if (len(edge)!=2 or len(set(edge))!=2 or not set(edge)&context["seeds"]
            or case["owner_scope_complete"] is not True):
        reasons.append("complete central-seed owner coverage unavailable")
    if len(tags)!=len(set(tags)) or not 4<=len(tags)<=8:
        reasons.append("degree outside4..8 or duplicate owner tags")
    for tag in tags:
        conn=context["cells"].get(tag,())
        if len(conn)!=4 or len(set(conn))!=4 or not set(edge)<=set(conn):
            reasons.append("invalid edge-owner tetrahedron");continue
        pair=tuple(sorted(set(conn)-set(edge)));opposite.append(pair)
        for a,b in (pair,pair[::-1]):adj.setdefault(a,set()).add(b)
    if len(set(opposite))!=len(opposite):reasons.append("duplicate link edge")
    n=len(tags)
    if len(adj)!=n or any(len(v)!=2 for v in adj.values()):reasons.append("link is not a degree-two n-cycle")
    cycle=[]
    if not reasons:
        start=min(adj);previous=None;node=start
        for _ in range(n):
            if node in cycle:break
            cycle.append(node)
            choices=sorted(adj[node]-({previous} if previous is not None else set()))
            previous,node=node,choices[0]
        if len(cycle)!=n or node!=start or set(cycle)!=set(adj):
            reasons.append("link disconnected or fails single-cycle closure")
    return dict(valid=not reasons,reasons=reasons,cycle=cycle,
                opposite_link_edges=[list(e) for e in opposite],degree=n)


def link_triangulations(cycle):
    """Complete root-edge Catalan recursion on an abstract cycle, without projection."""
    cycle=tuple(cycle)
    need(4<=len(cycle)<=8 and len(set(cycle))==len(cycle),"A simple4..8 cycle required")
    def disk(poly):
        if len(poly)==2:return ((),)
        rows=[]
        for k in range(1,len(poly)-1):
            for left in disk(poly[:k+1]):
                for right in disk(poly[k:]):
                    triangle=tuple(sorted((poly[0],poly[k],poly[-1])))
                    rows.append(tuple(sorted(left+right+(triangle,))))
        return tuple(sorted(rows))
    rows=disk(cycle)
    need(len(rows)==len(set(rows))=={4:2,5:5,6:14,7:42,8:132}[len(cycle)],
         "Complete distinct Catalan family required")
    need(all(len(r)==len(cycle)-2 for r in rows),"Every triangulation must have n-2 faces")
    return rows


def enumerate_edge_stars(context):
    """All seed-containing poor edges; retain out-of-scope rows rather than dropping them."""
    cells=context["cells"];seeds=context["seeds"]
    edges=sorted({tuple(sorted(e)) for tag in context["poor"]
                  for e in combinations(cells[tag],2) if set(e)&seeds})
    selected=[];outside=[]
    for edge in edges:
        owners=sorted(t for t,c in cells.items() if set(edge)<=set(c))
        complete=bool(set(edge)&seeds)
        row=dict(case_ID="edge:"+",".join(map(str,edge)),central_edge=list(edge),
            removed_cell_tags=owners,removed_poor_cell_tags=sorted(set(owners)&context["poor"]),
            owner_scope_complete=complete,owner_scope_basis="contains accepted complete-star seed",
            observed_degree=len(owners))
        if complete and 4<=len(owners)<=8:selected.append(row)
        else:
            row["disposition"]="outside selected degree4..8 route; retained, not infeasible"
            outside.append(row)
    return selected,outside


def convex_edge_cavity(context,case):
    """Strict convex boundary + known abstract ball + consistent old orientation.

    METHOD supplies the boundary-facet proof and Lipman Theorem1 prerequisites.
    Positivity or volume equality alone never sets this certificate true.
    """
    points=context["points"];cells=context["cells"];link=link_cycle(context,case)
    tags=case["removed_cell_tags"];entries=[(t,cells[t]) for t in tags if t in cells]
    old=[c for _,c in entries]
    vertices=sorted({v for c in old for v in c});rows=[];total=Fraction(0)
    for tag,conn in entries:
        d,q=exact_quality([points[t] for t in conn]);total+=d/6
        rows.append(dict(tetrahedron_tag=tag,node_tags=list(conn),D=rational(d),
                         Q_squared=None if q is None else rational(q),positive=d>0))
    valid,boundary=oriented_boundary(old)
    expected={tuple(sorted((apex,link["cycle"][i],link["cycle"][(i+1)%len(link["cycle"])])))
              for apex in case["central_edge"] for i in range(len(link["cycle"]))}
    sphere=(link["valid"] and len(vertices)==link["degree"]+2 and valid
            and len(boundary)==2*link["degree"]
            and {tuple(sorted(f)) for f in boundary}==expected)
    support=[]
    for face in boundary:
        for other in vertices:
            if other in face:continue
            d,_=exact_quality([points[t] for t in face]+[points[other]])
            support.append(dict(outward_face=list(face),other_node_tag=other,D=rational(d),strict_inside=d<0))
    positive=len(rows)==len(tags) and bool(rows) and all(r["positive"] for r in rows)
    strict=sphere and len(support)==2*link["degree"]*(link["degree"]-1) and all(r["strict_inside"] for r in support)
    protected=not set(tags)&context["protected_cells"]
    reasons=list(link["reasons"])
    if not sphere:reasons.append("old oriented cone-cycle sphere not established")
    if not positive:reasons.append("old orientation/nondegeneracy failed")
    if not strict:reasons.append("strict convex supporting-facet certificate unresolved")
    if not protected:reasons.append("removed cells intersect protected history")
    return dict(case=case,link=link,vertices=vertices,old_rows=rows,
        old_oriented_boundary=[list(f) for f in boundary],old_signed_volume=rational(total),
        abstract_edge_cycle_ball_and_boundary_sphere=sphere,
        all_old_tetrahedra_positive=positive,strict_support_rows=support,
        strict_convex_boundary_bijection_certified=strict,
        old_embedded_convex_filling_certified=sphere and positive and strict,
        protected_prior_cells_disjoint=protected,reasons=reasons,
        source_region_interface_exterior_or_BIN_evidence=None,
        whole_head_embedding_or_nonoverlap_accepted=False)


def screen_edge_candidate(context,cavity,triangulation,ordinal):
    """One full Catalan replacement; failed candidates remain complete records."""
    points=context["points"];case=cavity["case"];cycle=cavity["link"]["cycle"]
    tris=tuple(sorted(tuple(sorted(t)) for t in triangulation))
    disk=cavity["link"]["valid"] and tris in link_triangulations(cycle)
    cells=[];rows=[];total=Fraction(0)
    for apex in case["central_edge"]:
        for tri in tris:
            conn=(apex,)+tri;d,q=exact_quality([points[t] for t in conn])
            if d<0:
                conn=conn[:2]+(conn[3],conn[2]);d,q=exact_quality([points[t] for t in conn])
            cells.append(conn);total+=d/6
            rows.append(dict(node_tags=list(conn),D=rational(d),
                Q_squared=None if q is None else rational(q),positive=d>0,
                exact_quality_gate_passed=d>0 and q is not None and q>=Fraction(1,100)))
    valid,boundary=oriented_boundary(cells)
    chain=valid and [list(f) for f in boundary]==cavity["old_oriented_boundary"]
    volume=rational(total)==cavity["old_signed_volume"]
    quality=bool(rows) and all(r["exact_quality_gate_passed"] for r in rows)
    sets=[tuple(sorted(c)) for c in cells]
    duplicates=sorted(s for s in set(sets) if sets.count(s)>1)
    removed=set(case["removed_cell_tags"])
    complement={tuple(sorted(c)):t for t,c in context["cells"].items() if t not in removed}
    existing=[dict(node_tags=list(s),existing_tetrahedron_tag=complement[s])
              for s in sorted(set(sets)&set(complement))]
    old=[context["cells"][t] for t in case["removed_cell_tags"]]
    old_features={k:{tuple(sorted(s)) for c in old for s in combinations(c,k)} for k in (2,3)}
    introduced=[]
    for k in (2,3):
        features={tuple(sorted(s)) for c in cells for s in combinations(c,k)}-old_features[k]
        for feature in sorted(features):
            owners=sorted(t for t,c in context["cells"].items()
                          if t not in removed and set(feature)<=set(c))
            introduced.append(dict(dimension=k-1,node_tags=list(feature),observed_complement_owner_tags=owners,
                complete_owner_scope=bool(set(feature)&context["seeds"]),
                absent_from_observed_complement=not owners,
                global_missing_owner_absence=None if not set(feature)&context["seeds"] else not owners,
                semantic_region_interface_or_exterior_evidence=None))
    introduced_conflict=any(r["observed_complement_owner_tags"] for r in introduced)
    embedded=(disk and cavity["old_embedded_convex_filling_certified"] and chain
              and len(cells)==2*(len(cycle)-2) and bool(rows) and all(r["positive"] for r in rows))
    reasons=list(cavity["reasons"])
    if not disk:reasons.append("replacement is not a complete Catalan link disk")
    if not chain:reasons.append("full oriented boundary/internal cancellation mismatch")
    if not volume:reasons.append("exact signed-volume mismatch")
    if not quality:reasons.append("replacement quality/orientation failure")
    if duplicates:reasons.append("duplicate replacement unordered four-set")
    if existing:reasons.append("replacement duplicates observed unchanged cell")
    if introduced_conflict:reasons.append("introduced feature already present in observed complement")
    if not embedded:reasons.append("local embedded convex filling not certified")
    return dict(candidate_ID=case["case_ID"]+":triangulation:"+str(ordinal),case_ID=case["case_ID"],
        removed_cell_tags=case["removed_cell_tags"],link_triangles=[list(t) for t in tris],
        replacement_cells=[list(c) for c in cells],replacement_exact_rows=rows,
        abstract_suspension_of_triangulated_disk_ball=disk,
        oriented_boundary=[list(f) for f in boundary],oriented_boundary_equal=chain,
        signed_volume=rational(total),exact_signed_volume_equal=volume,
        all_replacement_exact_quality_gates_passed=quality,
        duplicate_replacement_four_sets=[list(s) for s in duplicates],observed_unchanged_cell_duplicates=existing,
        introduced_feature_owner_rows=introduced,local_embedded_convex_filling_certified=embedded,
        local_finite_predicates_passed=not reasons,reasons=reasons,
        complete_application_eligibility=None,global_embedding_and_nonoverlap_accepted=False,
        mesh_application_authorized=False,physics_material_LPBF_or_manufacturing_accepted=False)


def complete_conflict_relations(cases,candidates):
    """Lossless cliques/cartesian products, not a quadratic repeated JSON pair table."""
    by_case={r["case"]["case_ID"]:[] for r in cases}
    for r in candidates:by_case[r["case_ID"]].append(r["candidate_ID"])
    removals={r["case"]["case_ID"]:set(r["case"]["removed_cell_tags"]) for r in cases}
    case_pairs=[];pairs=set()
    for a,b in combinations(sorted(by_case),2):
        shared=sorted(removals[a]&removals[b])
        if shared:
            case_pairs.append(dict(case_IDs=[a,b],shared_removed_cell_tags=shared,
                relation="every candidate from first case conflicts with every candidate from second"))
            pairs.update(tuple(sorted((x,y))) for x in by_case[a] for y in by_case[b])
    within=[]
    for case,ids in sorted(by_case.items()):
        if len(ids)>1:
            within.append(dict(case_ID=case,candidate_IDs=ids,shared_removed_cell_tags=sorted(removals[case])))
            pairs.update(tuple(sorted(p)) for p in combinations(ids,2))
    proposed={}
    for r in candidates:
        for cell in {tuple(sorted(c)) for c in r["replacement_cells"]}:
            proposed.setdefault(cell,set()).add(r["candidate_ID"])
    duplicate=[]
    for cell,ids in sorted(proposed.items()):
        if len(ids)>1:
            ids=sorted(ids);duplicate.append(dict(unordered_four_set=list(cell),candidate_IDs=ids))
            pairs.update(combinations(ids,2))
    return dict(encoding="exact union of within-case cliques, cross-case complete products, duplicate-four-set cliques",
        case_candidate_memberships=by_case,within_case_conflict_cliques=within,
        cross_case_removed_cell_conflict_products=case_pairs,duplicate_proposed_cell_cliques=duplicate,
        distinct_conflicting_candidate_pair_count=len(pairs),all_pairs_represented_without_truncation=True,
        application_subset_selected=False)


def screen_complete_saved_family(context):
    """Future finite call only: all55 stars, all valid-cycle Catalan alternatives, no choice."""
    before=context_snapshot(context)
    need((len(context["points"]),len(context["cells"]),len(context["poor"]),len(context["seeds"]))==(271,499,24,16),
         "Full271/499/24/16 context required")
    need((len(context["protected_cells"]),len(context["protected_nodes"]))==(1983,66),"Prior1983/66 protection required")
    selected,outside=enumerate_edge_stars(context)
    observed={r["case_ID"]:r["observed_degree"] for r in selected}
    need(observed==EXPECTED_EDGE_DEGREES,"All55 exact saved degree4..8 associations required")
    cases=[];candidates=[];expected_count=0
    for case in selected:
        cavity=convex_edge_cavity(context,case);cases.append(cavity)
        if cavity["link"]["valid"]:
            triangles=link_triangulations(cavity["link"]["cycle"]);expected_count+=len(triangles)
            for ordinal,triangulation in enumerate(triangles,1):
                candidates.append(screen_edge_candidate(context,cavity,triangulation,ordinal))
    need(len(candidates)==expected_count<=1033,"Complete bounded Catalan family required")
    need({t for r in selected for t in r["removed_poor_cell_tags"]}==context["poor"],"All24 poor rows covered")
    need({t for r in selected for t in r["central_edge"] if t in context["seeds"]}==context["seeds"],"All16 seeds covered")
    conflicts=complete_conflict_relations(cases,candidates)
    after=context_snapshot(context)
    need(canonical_bytes(before)==canonical_bytes(after),"Complete saved context changed; refuse")
    return dict(schema="962-current24-complete-fixed-word-edge-removal-screen/v1",
        status="COMPLETE_FINITE_LOCAL_SCREEN_APPLICATION_ELIGIBILITY_UNAVAILABLE",
        context_before=before,context_after=after,complete_context_byte_identical=True,
        selected_complete_edge_stars=cases,outside_degree_route_associations=outside,
        selected_case_count=len(cases),valid_link_count=sum(r["link"]["valid"] for r in cases),
        candidate_count=len(candidates),conditional_Catalan_bound=1033,all_candidate_rows=candidates,
        local_finite_pass_count=sum(r["local_finite_predicates_passed"] for r in candidates),
        conflicts=conflicts,all_failed_unavailable_and_outside_rows_retained=True,
        complete_application_eligibility=None,whole_head_embedding_or_nonoverlap_accepted=False,
        region_interface_exterior_or_BIN_evidence=None,mesh_application_authorized=False,
        optimizer_or_native_called=False,coordinates_or_connectivity_written=False,
        physics_material_LPBF_or_manufacturing_accepted=False,global_infeasibility_proved=False,
        topology_change_necessity_proved=False)
