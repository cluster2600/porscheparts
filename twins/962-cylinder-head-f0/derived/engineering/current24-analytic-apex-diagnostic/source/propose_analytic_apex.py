"""HELD saved-only nineteen analytic-apex component tuples; never writes a mesh."""
import argparse
from fractions import Fraction
import hashlib
from itertools import product
import json
import math
from pathlib import Path
import struct
import sys

ROOT=Path(__file__).resolve().parents[3]
PREP=Path(__file__).resolve().parent
HELD=PREP/"held-preparation.json"
TUPLES=PREP/"component-tuples.json"
ACTUAL=ROOT/"work/962-engineering/head-star-current24-analytic-apex-execution-prep-001/actual-contract.json"
OUTPUT=ROOT/"work/962-engineering/head-star-current24-analytic-apex-001"
REPORT_REL="work/962-engineering/head-star-current110-pass62-application-001/worker-report.json"
PARENT_REL="work/962-engineering/head-star-current110-pass62-application-root-execution-001/result-peer-acceptance.json"
CLOSED_REL="work/962-engineering/head-star-current110-pass62-application-root-execution-001/closed-result.json"
FACE_REL="work/962-engineering/head-star-current24-fixed-face-obstruction-001/fixed-face-report.json"
FACE_ROOT_REL="work/962-engineering/head-star-current24-fixed-face-obstruction-root-execution-001/result-peer-acceptance.json"
MANIFEST_REL="work/962-engineering/head-star-current110-component-sicn-prep-001/component-manifest.json"
SELECTED_REL="work/962-engineering/head-star-current110-pass62-apply-prep-002/selected-proposals.json"
BOUNDARY=871731
FREE=()
QUALIFICATION=dict(head_PDE_authorized=False,engineering_accepted=False,physics_qualified=False,
    material_qualified=False,process_calibrated=False,manufacturing_authorized=False,
    native_execution_authorized=False,optimizer_execution_authorized=False,remeshing_authorized=False,
    surface_retriangulation_authorized=False,geometry_write_authorized=False,
    automatic_retry=False,global_infeasibility_proved=False)

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

def strict_json(path):
    def pairs(values):
        result={}
        for key,value in values:
            if key in result:raise ValueError("Duplicate JSON key")
            result[key]=value
        return result
    def constant(value):raise ValueError("Nonfinite JSON constant")
    return json.loads(path.read_text(encoding="utf-8"),object_pairs_hook=pairs,parse_constant=constant)

def record(path):
    raw=path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))

def verify_records(records):
    need(isinstance(records,dict) and records,"Finite metadata input map required")
    for rel,expected in records.items():
        need(isinstance(rel,str) and (ROOT/rel).resolve().is_relative_to(ROOT),"Metadata path outside repository")
        need(record(ROOT/rel)==expected,"Bound metadata changed: "+rel)

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

def topology_diagnostic(cells,frozen_boundary):
    def canonical(face):
        face=tuple(face);i=face.index(min(face));return face[i:]+face[:i]
    incidence={}
    for row in cells.values():
        for corners in [(0,2,1),(0,1,3),(1,2,3),(2,0,3)]:
            face=tuple(row[i] for i in corners);incidence.setdefault(tuple(sorted(face)),[]).append(face)
    exterior=[rows[0] for rows in incidence.values() if len(rows)==1]
    boundary=sorted(canonical(face) for face in exterior)
    return dict(boundary_faces=len(exterior),oriented_boundary_faces=[list(face) for face in boundary],
        internal_face_pairs=sum(len(rows)==2 for rows in incidence.values()),
        nonmanifold_faces=sum(len(rows)>2 for rows in incidence.values()),
        same_oriented_internal_faces=sum(len(rows)==2 and canonical(rows[0])!=canonical(rows[1][::-1]) for rows in incidence.values()),
        frozen_boundary_supplied=frozen_boundary is not None,
        exact_frozen_oriented_boundary=None if frozen_boundary is None else boundary==sorted(canonical(face) for face in frozen_boundary),
        unchanged_ordered_component_connectivity=True,geometric_overlap_or_intersection_checked=False)

def fixed_bits(original,final):
    if set(final)!=set(original):raise ValueError('Complete original node-tag set required')
    return all(struct.pack('<3d',*original[t])==struct.pack('<3d',*final[t]) for t in original if t not in FREE)

def exact_rows(points,cells):
    rows=[];volume=Fraction(0)
    for tag,row in sorted(cells.items()):
        det,q2=exact_quality([points[t] for t in row]);volume+=det/6
        passed=det>0 and q2 is not None and q2>=Fraction(1,100)
        rows.append(dict(tetrahedron_tag=tag,ordered_node_tags=row,
            exact_native_ordered_determinant_mm3=rational(det),
            exact_SICN_squared=None if q2 is None else rational(q2),
            signed_SICN_approximate=None if q2 is None else (1 if det>0 else -1 if det<0 else 0)*math.sqrt(float(q2)),
            positive_orientation=det>0,exact_point1_gate_passed=passed))
    return rows,volume


def optimal_apex(face,points):
    """One fixed binary64 expression for the real centroid/normal optimum; proposal only."""
    fixed=face["fixed_face_node_tags"];free=face["interior_seed_node_tag"]
    conn=face["original_ordered_tetrahedron_node_tags"]
    need(len(fixed)==3 and len(set(fixed))==3 and free not in fixed and set(conn)==set(fixed+[free]),
        "One complete fixed-face/free-corner association required")
    original_det,_=exact_quality([points[t] for t in conn])
    need(original_det>0,"Original ordered positive tetrahedron required")
    p0,p1,p2=[points[t] for t in fixed]
    exact=[[Fraction.from_float(float(v)) for v in points[t]] for t in fixed+[free]]
    exact_normal=cross(subtract(exact[1],exact[0]),subtract(exact[2],exact[0]))
    side=dot(exact_normal,subtract(exact[3],exact[0]))
    need(side!=0,"Noncoplanar original apex required")
    sign=1 if side>0 else -1
    # Fixed order; no fsum, interpolation, rescaling, nudging or fallback branch.
    edge1=subtract(p1,p0);edge2=subtract(p2,p0);normal=cross(edge1,edge2)
    normal_squared=dot(normal,normal)
    need(math.isfinite(normal_squared) and normal_squared>0,"Finite positive binary64 face normal required")
    normal_length=math.sqrt(normal_squared)
    height=math.sqrt((4.0*normal_length)/(3.0*math.sqrt(3.0)))
    scale=(sign*height)/normal_length
    centroid=[((p0[j]+p1[j])+p2[j])/3.0 for j in range(3)]
    xyz=[centroid[j]+scale*normal[j] for j in range(3)]
    need(all(math.isfinite(v) for v in normal+centroid+xyz+[normal_length,height,scale]),
        "Finite analytic-apex construction required; no fallback")
    return dict(target_tetrahedron_tag=face["tetrahedron_tag"],seed_node_tag=free,
        fixed_face_node_tags=fixed,original_ordered_tetrahedron_node_tags=conn,
        original_free_corner_index=conn.index(free),exact_original_face_side_sign=sign,
        centroid_mm=centroid,unnormalized_normal_mm2=normal,normal_length_mm2=normal_length,
        normal_height_mm=height,coordinates_mm=xyz,binary64_hex=[v.hex() for v in xyz],
        construction="c+sign*sqrt(4*norm(cross)/(3*sqrt(3)))*cross/norm(cross)",
        real_optimum_or_rounded_point_accuracy_certified=False)


def component_bindings(report,faces,face_report,face_root,manifest,selected,plan,held):
    need(face_root["decision"]=="ACCEPT_SAVED_CONDITIONAL_FACE_DIAGNOSTIC_ONLY_NO_OBSTRUCTION_IDENTIFIED",
        "Accepted fixed-face diagnostic required")
    need(face_root["report"]==held["input_records"][FACE_REL],"Current face report/root association changed")
    need(face_report["parent_acceptance"]==held["input_records"][PARENT_REL]
        and face_report["sharp_classification_counts"]==
        dict(strict_obstruction=0,equality=0,not_obstructed_by_this_test=24)
        and face_report["all24_rows_retained"] is True and face_report["refused_tetrahedron_tags"]==[],
        "All24 strictly nonobstructed saved faces required")
    saved={row["tetrahedron_tag"]:row for row in face_report["complete24_rows"]}
    need(len(saved)==24 and set(saved)=={row["tetrahedron_tag"] for row in faces},"Complete same24 fixed faces required")
    for face in faces:
        row=saved[face["tetrahedron_tag"]]
        need({k:row[k] for k in face}==face and row["status"]=="complete_exact_saved_fixed_face_diagnostic_only"
            and row["certificates"]["separate_sharp_4_over_841_test"]["classification"]=="not_obstructed_by_this_test",
            "Accepted face/native/context coordinate association changed")
    stars=report["after"]["complete_native_census"]["complete_seed_star_census"]
    points={row["node_tag"]:[float(x) for x in row["coordinates_mm"]] for row in stars["unique_incident_nodes"]}
    cells={row["tetrahedron_tag"]:row["node_tags"] for row in stars["complete_incident_tetrahedra"]}
    native_rows={row["tetrahedron_tag"]:row for row in stars["complete_incident_tetrahedra"]}
    seeds=stars["movable_node_tags"];seedset=set(seeds)
    need(manifest["group_count"]==73 and len(manifest["cases"])==73
        and manifest["all82_variable_nodes_and2482_cells_are_pairwise_disjoint_complete_partitions"] is True
        and manifest["all110_poor2372_good58_shared_memberships_preserved"] is True,"Complete original73 component partition required")
    original=manifest["cases"];by_id={case["component_ID"]:case for case in original}
    need(len(by_id)==73 and len({t for case in original for t in case["movable_node_tags"]})==82
        and sum(len(case["movable_node_tags"]) for case in original)==82
        and len({t for case in original for t in case["tetrahedron_tags"]})==2482
        and sum(len(case["tetrahedron_tags"]) for case in original)==2482,"Complete disjoint free/cell membership required")
    rejected=selected["rejected_component_IDs"];passed=selected["component_IDs"]
    need(len(rejected)==11 and len(passed)==62 and set(rejected).isdisjoint(passed)
        and set(rejected)|set(passed)==set(by_id),"Selected/rejected component partition required")
    groups=[by_id[i] for i in sorted(rejected)]
    need({t for case in groups for t in case["movable_node_tags"]}==seedset
        and {t for case in groups for t in case["tetrahedron_tags"]}==set(cells),
        "Own remaining16/499 exact component union required")
    passed_cells={t for i in passed for t in by_id[i]["tetrahedron_tags"]}
    need(len(passed_cells)==1983 and not passed_cells&set(cells)
        and selected["selected_incident_tetrahedra"]==1983
        and selected["original_poor_cells_in_passed_groups"]==86
        and len(selected["selected_node_tags"])==66 and not seedset&set(selected["selected_node_tags"]),
        "Accepted66 nodes/1983 cells/86 improvements must be disjoint")
    by_seed={tag:sorted(face["tetrahedron_tag"] for face in faces if face["interior_seed_node_tag"]==tag) for tag in seeds}
    need(sorted(map(len,by_seed.values()))==[1]*8+[2]*8,"Eight one-face/eight two-face seeds required")
    expected=[];scopes=[]
    for case in groups:
        free=case["movable_node_tags"];tags=case["tetrahedron_tags"]
        need(free==sorted(set(free)) and 1<=len(free)<=2 and tags==sorted(set(tags)),"Fixed one/two-seed component required")
        incident={t for t,row in cells.items() if set(row)&set(free)}
        need(incident==set(tags),"Complete current component incidence required")
        context=sorted({n for t in tags for n in cells[t]})
        need(context==case["all_incident_node_tags"]
            and sorted(set(context)-set(free))==case["fixed_context_node_tags"],
            "Complete fixed current component context required")
        need([t for t in tags if native_rows[t]["initially_positive_poor"]]==case["initially_positive_poor_tetrahedron_tags"],
            "Original poor component memberships must remain the current24")
        need([t for t in tags if len(set(cells[t])&set(free))>1]==case["shared_by_multiple_movable_nodes_tetrahedron_tags"],
            "Shared cell memberships changed")
        choices=list(product(*(by_seed[t] for t in free)))
        for index,choice in enumerate(choices,1):
            expected.append(dict(tuple_ID="component-%04d-apex-%02d"%(case["component_ID"],index),
                component_ID=case["component_ID"],seed_choices=[dict(seed_node_tag=t,target_tetrahedron_tag=q) for t,q in zip(free,choice)],
                full_tetrahedron_tags=tags,full_cell_count=len(tags)))
        scopes.append(dict(component_ID=case["component_ID"],movable_node_tags=free,
            full_tetrahedron_tags=tags,fixed_context_node_tags=case["fixed_context_node_tags"],
            initially_good_count=len(case["initially_good_tetrahedron_tags"]),
            initially_poor_count=len(case["initially_positive_poor_tetrahedron_tags"]),
            shared_cell_count=len(case["shared_by_multiple_movable_nodes_tetrahedron_tags"])))
    need(plan["tuples"]==expected and len(expected)==19
        and sum(row["full_cell_count"] for row in expected)==916,"Exact19 tuples/916 cell dispositions required")
    need(sum(row["initially_good_count"] for row in scopes)==475
        and sum(row["initially_poor_count"] for row in scopes)==24
        and sum(row["shared_cell_count"] for row in scopes)==33,"Complete475 good/24 poor/33 shared scope required")
    need(plan["component_scopes"]==scopes,"Explicit component scope list changed")
    return points,cells,scopes,expected,dict(accepted66_nodes_disjoint=True,
        accepted1983_cells_disjoint=True,accepted86_improvements_not_recomputed=True,
        complete_original_component_partition_verified=True,current499_complete=True)


def run(actual_path,actual_sha256):
    global FREE
    need(actual_path.resolve()==ACTUAL,"Exact future root actual path required")
    need(isinstance(actual_sha256,str) and len(actual_sha256)==64
        and all(c in "0123456789abcdef" for c in actual_sha256),"External actual digest required")
    need(record(ACTUAL)["sha256"]==actual_sha256,"Actual digest changed")
    actual=strict_json(ACTUAL)
    need(actual["schema"]=="962-current24-analytic-apex-saved-candidate-execution-authority/v1"
        and actual["saved_only_candidate_diagnostic_authorized"] is True and actual["execution_count"]==1,
        "Separate one-shot root saved-only candidate authority required")
    for name in QUALIFICATION:need(actual[name] is False,"Forbidden authority: "+name)
    need(actual["worker"]==record(Path(__file__)) and actual["held_preparation"]==record(HELD),
        "Actual source/held bindings required")
    held=strict_json(HELD)
    need(held["schema"]=="962-current24-analytic-apex-source-held/v1"
        and held["source"]==record(Path(__file__)) and held["tuple_list"]==record(TUPLES),"Exact source/tuple-list/held binding required")
    need(actual["input_records"]==held["input_records"],"Actual must preserve complete held input map")
    for name in ("independent_source_review","root_source_admission","synthetic_guard_result"):
        need(isinstance(actual[name],dict) and record(ROOT/actual[name]["path"])==actual[name],
            "Direct future source review/admission/guard metadata binding required")
    verify_records(held["input_records"])
    report=strict_json(ROOT/REPORT_REL);parent=strict_json(ROOT/PARENT_REL);closed=strict_json(ROOT/CLOSED_REL)
    faces,intake=current_faces(report,parent,closed,held)
    plan=strict_json(TUPLES)
    points,cells,scopes,tuples,protection=component_bindings(report,faces,strict_json(ROOT/FACE_REL),
        strict_json(ROOT/FACE_ROOT_REL),strict_json(ROOT/MANIFEST_REL),strict_json(ROOT/SELECTED_REL),plan,held)
    need(not OUTPUT.exists() and not OUTPUT.is_symlink(),"Fresh fixed diagnostic output required")
    proposals={};proposal_rows=[]
    for face in faces:
        try:
            item=optimal_apex(face,points);item["status"]="constructed_binary64_proposal_only"
        except (ValueError,OverflowError,ZeroDivisionError) as error:
            item=dict(target_tetrahedron_tag=face["tetrahedron_tag"],seed_node_tag=face["interior_seed_node_tag"],
                status="refused_analytic_apex_construction_retained",error=str(error),coordinates_mm=None,binary64_hex=None)
        proposals[face["tetrahedron_tag"]]=item;proposal_rows.append(item)
    baselines={};scope_by_id={row["component_ID"]:row for row in scopes}
    for scope in scopes:
        local={t:cells[t] for t in scope["full_tetrahedron_tags"]}
        before_rows,before_volume=exact_rows(points,local)
        need(all(row["positive_orientation"] for row in before_rows),"Every original current component cell must be positive")
        topology=topology_diagnostic(local,None)
        need(topology["nonmanifold_faces"]==0 and topology["same_oriented_internal_faces"]==0
            and not(set(scope["movable_node_tags"])&{n for face in topology["oriented_boundary_faces"] for n in face}),
            "Complete fixed local oriented component boundary required")
        baselines[scope["component_ID"]]=dict(exact_rows=before_rows,volume=before_volume,topology=topology)
    outcomes=[];cell_dispositions=0;quality_evaluations=0
    for descriptor in tuples:
        scope=scope_by_id[descriptor["component_ID"]];baseline=baselines[descriptor["component_ID"]]
        FREE=tuple(scope["movable_node_tags"])
        chosen=[proposals[row["target_tetrahedron_tag"]] for row in descriptor["seed_choices"]]
        failures=[row["target_tetrahedron_tag"] for row in chosen if row["status"]!="constructed_binary64_proposal_only"]
        outcome=dict(descriptor,selected_proposal_associations=[dict(seed_node_tag=row["seed_node_tag"],
            target_tetrahedron_tag=row["target_tetrahedron_tag"],status=row["status"],
            coordinates_mm=row["coordinates_mm"],binary64_hex=row["binary64_hex"]) for row in chosen])
        if failures:
            rows=[dict(tetrahedron_tag=t,ordered_node_tags=cells[t],
                status="not_evaluable_due_to_failed_apex_construction",failed_target_tetrahedron_tags=failures,
                exact_native_ordered_determinant_mm3=None,exact_SICN_squared=None,
                positive_orientation=None,exact_point1_gate_passed=None) for t in descriptor["full_tetrahedron_tags"]]
            outcome.update(status="refused_construction_tuple_retained",complete_cell_rows=rows,
                all_component_exact_quality_gate=False,procedural_checks_passed=False,
                exact_before_signed_volume_mm3=rational(baseline["volume"]),exact_final_signed_volume_mm3=None,
                exact_signed_volume_equals_own_before=None,local_quality_witness=False)
        else:
            final=dict(points)
            for row in chosen:final[row["seed_node_tag"]]=list(row["coordinates_mm"])
            local={t:cells[t] for t in descriptor["full_tetrahedron_tags"]}
            rows,volume=exact_rows(final,local);quality_evaluations+=len(rows)
            topology=topology_diagnostic(local,baseline["topology"]["oriented_boundary_faces"])
            fixed=fixed_bits(points,final)
            boundary=all(struct.pack("<3d",*points[t])==struct.pack("<3d",*final[t]) for t in points if t<=BOUNDARY)
            quality=all(row["exact_point1_gate_passed"] for row in rows)
            procedural=(fixed and boundary and topology["exact_frozen_oriented_boundary"] is True
                and topology["nonmanifold_faces"]==0 and topology["same_oriented_internal_faces"]==0
                and volume==baseline["volume"])
            outcome.update(status="exact_local_quality_witness_only" if quality and procedural else "rejected_tuple_retained",
                complete_cell_rows=rows,all_component_exact_quality_gate=quality,procedural_checks_passed=procedural,
                all_other271_context_words_unchanged=fixed,all_source_boundary_context_words_unchanged=boundary,
                topology=topology,exact_before_signed_volume_mm3=rational(baseline["volume"]),
                exact_final_signed_volume_mm3=rational(volume),exact_signed_volume_equals_own_before=volume==baseline["volume"],
                minimum_final_signed_determinant_mm3=rational(min(Fraction(int(row["exact_native_ordered_determinant_mm3"]["numerator"]),
                    int(row["exact_native_ordered_determinant_mm3"]["denominator"])) for row in rows)),
                volume_margin_acceptance="Each original ordered determinant strictly positive; no added margin/tolerance.",
                local_quality_witness=bool(quality and procedural),
                failed_quality_cell_tags=[row["tetrahedron_tag"] for row in rows if not row["exact_point1_gate_passed"]])
        cell_dispositions+=len(rows);outcomes.append(outcome)
    FREE=()
    need(len(outcomes)==19 and cell_dispositions==916,"All19 tuples and916 cell dispositions must be retained")
    verify_records(held["input_records"])
    need(record(ACTUAL)["sha256"]==actual_sha256 and actual["worker"]==record(Path(__file__))
        and actual["held_preparation"]==record(HELD) and held["tuple_list"]==record(TUPLES),"Actual/source/held/tuples changed")
    for name in ("independent_source_review","root_source_admission","synthetic_guard_result"):
        need(record(ROOT/actual[name]["path"])==actual[name],"Direct admission metadata changed")
    result=dict(schema="962-current24-saved-analytic-apex-component-candidates/v1",
        status="complete_saved_candidate_diagnostic_only",source=record(Path(__file__)),
        held_preparation=record(HELD),own_actual=record(ACTUAL),tuple_list=record(TUPLES),
        input_records=held["input_records"],intake=intake,protection=protection,
        complete24_face_proposals=proposal_rows,complete19_tuple_results=outcomes,
        complete499_before_cell_rows=[row for component in sorted(baselines) for row in baselines[component]["exact_rows"]],
        tuple_count=19,complete_cell_disposition_count=916,exact_quality_evaluation_count=quality_evaluations,
        all916_quality_evaluations_completed=quality_evaluations==916,
        construction_refusal_count=sum(row["status"]!="constructed_binary64_proposal_only" for row in proposal_rows),
        exact_local_witness_tuple_IDs=[row["tuple_ID"] for row in outcomes if row["local_quality_witness"]],
        no_tuple_dropped_or_automatically_selected=True,no_cross_face_averaging_or_search=True,
        failed_tuples_imply_infeasibility=False,geometry_export_or_mesh_write_count=0,native_call_count=0,optimizer_call_count=0,
        source_BIN_identity=None,explicit_exterior_facet_membership=None,
        all_bound_metadata_unchanged=True,raw_MSH_BIN_or_runtime_body_access=False,
        saved_mesh_not_opened_or_modified_by_worker=True,original24_mesh_refusal_preserved=True,
        local_witness_is_not_embedding_or_global_mesh_acceptance=True,qualification=QUALIFICATION)
    encoded=(json.dumps(result,indent=2,allow_nan=False)+"\n").encode()
    need(len(encoded)<=33554432,"Inherited32MiB result limit; no truncation")
    OUTPUT.mkdir()
    with (OUTPUT/"candidate-diagnostic.json").open("xb") as stream:stream.write(encoded)
    print(json.dumps(dict(status=result["status"],tuples=19,cell_dispositions=916,
        quality_evaluations=quality_evaluations,construction_refusals=result["construction_refusal_count"],
        local_witness_tuples=len(result["exact_local_witness_tuple_IDs"]))))
    return 2 if result["construction_refusal_count"] else 0


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--actual",type=Path,required=True);parser.add_argument("--actual-sha256",required=True)
    args=parser.parse_args()
    try:sys.exit(run(args.actual,args.actual_sha256))
    except (ValueError,KeyError,TypeError,OSError) as error:
        print("Refused saved-only analytic-apex diagnostic: "+str(error),file=sys.stderr);sys.exit(2)
