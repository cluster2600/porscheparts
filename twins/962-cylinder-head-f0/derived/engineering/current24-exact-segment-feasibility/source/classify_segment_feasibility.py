"""HELD exact real feasibility of all nineteen saved current-to-apex segments; no word construction."""
import argparse
import gzip
import io
from fractions import Fraction
import hashlib
from itertools import product, combinations
import json
import os
from functools import cmp_to_key
import math
from pathlib import Path
import struct
import sys

ROOT=Path(__file__).resolve().parents[3]
PREP=Path(__file__).resolve().parent
HELD=PREP/"held-preparation.json"
TUPLES=ROOT/"work/962-engineering/head-star-current24-analytic-apex-prep-001/component-tuples.json"
ACTUAL=ROOT/"work/962-engineering/head-star-current24-exact-segment-feasibility-execution-prep-003/actual-contract.json"
OUTPUT=ROOT/"work/962-engineering/head-star-current24-exact-segment-feasibility-002"
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

ROOT_LIBRARY_BASE=ROOT/"work/962-engineering/head-star-current24-segment-runtime-001/venv/lib/python3.12/site-packages"

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

def root_library():
    """Lazy import only after the separate fixed actual/intake gate."""
    import sympy as sp
    import mpmath as mp
    import sympy.external.gmpy as ground
    import sympy.core.cache as cache
    need(sp.__version__=="1.14.0" and mp.__version__=="1.3.0","Exact declared package versions")
    need(os.environ.get("SYMPY_GROUND_TYPES")=="python" and os.environ.get("SYMPY_USE_CACHE")=="no",
        "Selected exact Python backend and disabled cache environment")
    need(ground.GROUND_TYPES=="python" and ground.HAS_GMPY==0 and cache.USE_CACHE=="no",
        "Actual backend/cache must match the selected controls")
    expected={"sympy":ROOT_LIBRARY_BASE/"sympy/__init__.py",
        "mpmath":ROOT_LIBRARY_BASE/"mpmath/__init__.py",
        "ground":ROOT_LIBRARY_BASE/"sympy/external/gmpy.py",
        "cache":ROOT_LIBRARY_BASE/"sympy/core/cache.py"}
    modules={"sympy":sp,"mpmath":mp,"ground":ground,"cache":cache}
    actual_paths={key:str(Path(module.__file__).resolve())for key,module in modules.items()}
    need(actual_paths=={key:str(path)for key,path in expected.items()},"Exact selected module origins")
    return sp,dict(sympy_version=sp.__version__,mpmath_version=mp.__version__,
        ground_types=ground.GROUND_TYPES,cache=cache.USE_CACHE,module_paths=actual_paths,
        Python_executable=str(Path(sys.executable)),root_arithmetic_domain="QQ",
        float_evalf_same_root_or_approximate_roots_used=False)

def qvalue(value):
    return Fraction(int(value.p), int(value.q))

def poly_data(poly):
    coefficients=[qvalue(x) for x in poly.all_coeffs()]
    denominator=math.lcm(*(x.denominator for x in coefficients))
    integers=[int(x*denominator) for x in coefficients]
    content=math.gcd(*integers) or 1
    return dict(degree=None if poly.is_zero else int(poly.degree()),
        rational_coefficients_descending=[rational(x) for x in coefficients],
        positive_denominator_lcm=str(denominator),positive_content_divisor=str(content),
        primitive_integer_coefficients_descending=[str(x//content) for x in integers])

def polynomial_cell(start,end,sp):
    """Exact dyadic endpoints; at most two vertices move, all with the same t."""
    need(len(start)==len(end)==4 and all(len(p)==3 and
        all(type(x)in(int,float)and math.isfinite(x)for x in p)for p in start+end),
        "Exactly four finite endpoint triples")
    t=sp.Symbol("t")
    zero=sp.Poly(0,t,domain="QQ")
    def scalar(x,y):
        a=Fraction.from_float(float(x));b=Fraction.from_float(float(y))
        return sp.Poly([sp.Rational((b-a).numerator,(b-a).denominator),
            sp.Rational(a.numerator,a.denominator)],t,domain="QQ")
    p=[[scalar(x,y) for x,y in zip(a,b)] for a,b in zip(start,end)]
    def sub(a,b):return [x-y for x,y in zip(a,b)]
    def pdot(a,b):return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]
    def pcross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
    a,b,c=[sub(row,p[0]) for row in p[1:]]
    det=pdot(a,pcross(b,c))
    edges=zero
    for i,j in combinations(range(4),2):
        e=sub(p[j],p[i]);edges+=pdot(e,e)
    faces=zero
    for i,j,k in combinations(range(4),3):
        normal=pcross(sub(p[j],p[i]),sub(p[k],p[i]))
        faces+=pdot(normal,normal)
    quality=(det*det).mul_ground(3600)-edges*faces
    moved=sum(any(struct.pack("<d",float(x))!=struct.pack("<d",float(y)) for x,y in zip(a,b))
        for a,b in zip(start,end))
    need(moved<=2,"Only zero/one/two moving vertices per cell")
    degree=lambda f:-1 if f.is_zero else int(f.degree())
    if moved:
        valid=(degree(det)<=moved and degree(edges)<=2
            and degree(faces)<=min(2*moved,4) and degree(quality)<=min(2+2*moved,6))
    else:valid=all(degree(f)<=0 for f in (det,edges,faces,quality))
    need(valid,"Declared affine-path degree bounds")
    # Existing kernel remains authoritative; these two endpoint identities are exact.
    for parameter,coordinates in ((0,start),(1,end)):
        original_det,original_q2=exact_quality(coordinates)
        d=qvalue(det.eval(parameter));s=qvalue(edges.eval(parameter));f=qvalue(faces.eval(parameter))
        q2=36*d*d/(s*f) if s*f>0 else None
        need(d==original_det and q2==original_q2,"Metric identity versus unchanged endpoint exact kernel")
    return det,edges,faces,quality

def refine_isolator(root):
    """One exact root-count step, not a candidate/precision search or width cutoff."""
    if root["a"]==root["b"]:return
    f=root["poly"];a,b=root["a"],root["b"];m=(a+b)/2
    sp=root["sp"];qq=lambda x:sp.Rational(x.numerator,x.denominator)
    if f.eval(qq(m))==0:
        root["a"]=root["b"]=m
    elif int(f.count_roots(qq(a),qq(m)))==1:
        root["b"]=m
    else:
        need(int(f.count_roots(qq(m),qq(b)))==1,"One root must remain in the other exact half")
        root["a"]=m

def compare_roots(left,right):
    if left["a"]==left["b"] and right["a"]==right["b"]:
        return (left["a"]>right["a"])-(left["a"]<right["a"])
    if left.get("factor_key") is not None and left.get("factor_key")==right.get("factor_key"):
        return (left["root_index"]>right["root_index"])-(left["root_index"]<right["root_index"])
    # All nonrational nodes come from monic irreducible QQ factors.
    if left.get("poly") is not None and right.get("poly") is not None:
        need(left["poly"].gcd(right["poly"]).degree()==0,
            "Distinct canonical irreducible factors must have no shared root")
    while True:
        if left["b"]<=right["a"]:return -1
        if right["b"]<=left["a"]:return 1
        if left["a"]==left["b"] and right.get("poly") is not None:
            sp=right["sp"];q=left["a"]
            if right["poly"].eval(sp.Rational(q.numerator,q.denominator))==0:return 0
        if right["a"]==right["b"] and left.get("poly") is not None:
            sp=left["sp"];q=right["a"]
            if left["poly"].eval(sp.Rational(q.numerator,q.denominator))==0:return 0
        refine_isolator(left);refine_isolator(right)

def rational_node(value):
    return dict(a=Fraction(value),b=Fraction(value),factor_key=None,root_index=None,
        poly=None,owners={},factor_refs=[])

def root_snapshot(root):
    return dict(exact_rational=rational(root["a"]) if root["a"]==root["b"] else None,
        isolating_interval=[rational(root["a"]),rational(root["b"])],
        algebraic_factor_references=root["factor_refs"],
        constraint_multiplicities={str(k):v for k,v in sorted(root["owners"].items())})

def simplest_sample(left,right,left_closed,right_closed):
    """First Stern-Brocot fraction in the interval minimizes denominator, then numerator."""
    def inside(q):
        node=rational_node(q);a=compare_roots(node,left);b=compare_roots(node,right)
        return (a>0 or a==0 and left_closed) and (b<0 or b==0 and right_closed)
    for q in (Fraction(0),Fraction(1)):
        if inside(q):return q
    ln,ld,rn,rd=0,1,1,1
    while True:
        q=Fraction(ln+rn,ld+rd)
        if inside(q):return q
        comparison=compare_roots(rational_node(q),left)
        if comparison<0 or comparison==0 and not left_closed:
            ln,ld=q.numerator,q.denominator
        else:
            rn,rd=q.numerator,q.denominator

def sign_decomposition(constraints,sp):
    """Complete [0,1] signs of original D/P polynomials, never an approximate root solve."""
    need(constraints and len(constraints)<=998,"Finite complete one-component constraint list")
    need(all(x["kind"]in("D","P")and(x["poly"].is_zero or
        x["poly"].degree()<=(2 if x["kind"]=="D"else 6))for x in constraints),"Only declared degree bounds")
    factor_table={};all_roots=[];polynomial_rows=[]
    qq=lambda x:sp.Rational(x.numerator,x.denominator)
    for index,item in enumerate(constraints):
        poly=item["poly"]
        row=dict(constraint_ID=index,cell_tag=item["cell_tag"],kind=item["kind"],
            relation="strictly_positive" if item["kind"]=="D" else "nonnegative",
            polynomial=poly_data(poly),constant_or_zero=poly.is_zero or poly.degree()==0,factorization=[])
        if not poly.is_zero and poly.degree()>0:
            content,factors=poly.factor_list()
            rebuilt=sp.Poly(content,*poly.gens,domain="QQ")
            for factor,multiplicity in factors:rebuilt*=factor**multiplicity
            need(rebuilt==poly,"Exact irreducible factor reconstruction required")
            row["factorization_content"]=rational(qvalue(content))
            for factor,multiplicity in factors:
                monic=factor.monic()
                key=tuple((int(x.p),int(x.q)) for x in monic.all_coeffs())
                if key not in factor_table:
                    identifier="factor-%04d"%(len(factor_table)+1)
                    intervals=monic.intervals()
                    need(len(intervals)==int(monic.count_roots()),"Complete real-root count")
                    roots=[]
                    for root_index,((a,b),count) in enumerate(intervals):
                        a,b=qvalue(a),qvalue(b)
                        need(count==1 and a<=b,"Irreducible QQ factors have simple isolated real roots")
                        need(int(monic.count_roots(qq(a),qq(b)))==1,"One isolated real root")
                        need((a==b and monic.eval(qq(a))==0)
                            or(a<b and monic.eval(qq(a))!=0 and monic.eval(qq(b))!=0),
                            "Point root or strict non-root interval endpoints")
                        need(not roots or roots[-1]["b"]<=a,"Globally ordered disjoint factor isolators")
                        root=dict(a=a,b=b,poly=monic,sp=sp,factor_key=key,root_index=root_index,
                            owners={},factor_refs=[dict(factor_ID=identifier,real_root_index=root_index)])
                        roots.append(root);all_roots.append(root)
                    factor_table[key]=dict(factor_ID=identifier,poly=monic,roots=roots)
                entry=factor_table[key]
                row["factorization"].append(dict(factor_ID=entry["factor_ID"],
                    raw_factor=poly_data(factor),multiplicity=int(multiplicity)))
                for root in entry["roots"]:
                    root["owners"][index]=root["owners"].get(index,0)+int(multiplicity)
        polynomial_rows.append(row)
    zero,one=rational_node(0),rational_node(1)
    selected=[root for root in all_roots if compare_roots(root,zero)>=0 and compare_roots(root,one)<=0]
    ordered=sorted([zero,one]+selected,key=cmp_to_key(compare_roots))
    boundaries=[]
    for root in ordered:
        if boundaries and compare_roots(boundaries[-1],root)==0:
            for key,value in root["owners"].items():
                need(key not in boundaries[-1]["owners"],"No repeated owning root association")
                boundaries[-1]["owners"][key]=value
            boundaries[-1]["factor_refs"]+=root["factor_refs"]
        else:boundaries.append(root)
    need(len(boundaries)>=2 and compare_roots(boundaries[0],zero)==0
        and compare_roots(boundaries[-1],one)==0,"Complete [0,1] boundary coverage")
    interval_rows=[]
    for i,(left,right) in enumerate(zip(boundaries,boundaries[1:])):
        need(compare_roots(left,right)<0,"Strictly ordered distinct boundaries")
        while left["b"]>=right["a"]:
            refine_isolator(left);refine_isolator(right)
        sample=(left["b"]+right["a"])/2
        signs=[]
        for item in constraints:
            value=qvalue(item["poly"].eval(qq(sample)))
            signs.append((value>0)-(value<0))
        interval_rows.append(dict(kind="open_interval",left_boundary=i,right_boundary=i+1,
            sign_sample=rational(sample),signs=signs))
    atoms=[]
    for i,root in enumerate(boundaries):
        if root["a"]==root["b"]:
            signs=[]
            for item in constraints:
                value=qvalue(item["poly"].eval(qq(root["a"])))
                signs.append((value>0)-(value<0))
        else:
            need(0<i<len(boundaries)-1,"Only nonrational interior roots")
            signs=[]
            for k,item in enumerate(constraints):
                l=interval_rows[i-1]["signs"][k];r=interval_rows[i]["signs"][k]
                if item["poly"].is_zero:signs.append(0)
                elif k in root["owners"]:
                    need(l!=0 and r==l*((-1)**root["owners"][k]),"Exact multiplicity crossing signs")
                    signs.append(0)
                else:
                    need(l==r and l!=0,"Unowned constraint has same nonzero sign across root")
                    signs.append(l)
        atoms.append(dict(kind="point",boundary=i,signs=signs))
        if i<len(interval_rows):atoms.append(interval_rows[i])
    for i,atom in enumerate(atoms):
        failed=[k for k,(item,s) in enumerate(zip(constraints,atom["signs"]))
            if not(s>0 if item["kind"]=="D" else s>=0)]
        atom.update(atom_ID=i,feasible=not failed,blocking_constraint_IDs=failed)
    components=[];active=None
    for atom in atoms:
        if atom["feasible"]:
            if active is None:
                active=dict(atom_IDs=[],left_boundary=atom.get("boundary",atom.get("left_boundary")),
                    left_closed=atom["kind"]=="point")
            active["atom_IDs"].append(atom["atom_ID"])
            active["right_boundary"]=atom.get("boundary",atom.get("right_boundary"))
            active["right_closed"]=atom["kind"]=="point"
        elif active is not None:components.append(active);active=None
    if active is not None:components.append(active)
    for i,component in enumerate(components):
        left=boundaries[component["left_boundary"]];right=boundaries[component["right_boundary"]]
        if compare_roots(left,right)==0:
            sample=dict(kind="exact_singleton",algebraic_point=root_snapshot(left))
        else:
            value=simplest_sample(left,right,component["left_closed"],component["right_closed"])
            sample=dict(kind="minimum_denominator_then_numerator_rational",value=rational(value))
        component.update(component_index=i,canonical_exact_sample=sample,
            correctly_rounded_binary64_proposal=None,
            word_construction_status="UNSUPPORTED_NOT_ATTEMPTED_NO_VERIFIED_CORRECT_ROUNDER",
            actual_word_recheck=None,binary64_existence_claim=False)
    factor_rows=[]
    for entry in factor_table.values():
        f=entry["poly"];factor_rows.append(dict(factor_ID=entry["factor_ID"],monic_polynomial=poly_data(f),
            sturm_chain=[poly_data(p) for p in f.sturm()],
            total_real_roots=int(f.count_roots()),
            all_real_isolators=[dict(real_root_index=x["root_index"],**root_snapshot(x),
                root_count_in_saved_interval=int(f.count_roots(qq(x["a"]),qq(x["b"]))))for x in entry["roots"]]))
    return dict(constraints=polynomial_rows,irreducible_factors=factor_rows,
        ordered_boundaries=[root_snapshot(x) for x in boundaries],complete_sign_atoms=atoms,
        connected_feasible_components=components,real_path_classification_complete=True,
        real_path_feasible=bool(components),all_cell_constraint_associations_retained=True,
        binary64_word_construction_supported=False,binary64_completeness=False)

def recheck_word_proposal(points,cells,scope,word_rows):
    """Separate exact validator only; no rounder and no caller in the real-path diagnostic."""
    global FREE
    tags=scope["movable_node_tags"];xyz=coordinate_rows(word_rows,tags);final=dict(points)
    for tag,row in zip(tags,xyz):final[tag]=row
    local={t:cells[t] for t in scope["full_tetrahedron_tags"]}
    before,before_volume=exact_rows(points,local);after,after_volume=exact_rows(final,local)
    topology_before=topology_diagnostic(local,None)
    topology_after=topology_diagnostic(local,topology_before["oriented_boundary_faces"])
    previous=FREE;FREE=tuple(tags)
    try:fixed=fixed_bits(points,final)
    finally:FREE=previous
    boundary=all(struct.pack("<3d",*points[t])==struct.pack("<3d",*final[t])for t in points if t<=BOUNDARY)
    passed=(all(row["exact_point1_gate_passed"]for row in after)and fixed and boundary
        and topology_after["exact_frozen_oriented_boundary"]is True
        and topology_after["nonmanifold_faces"]==0 and topology_after["same_oriented_internal_faces"]==0
        and before_volume==after_volume)
    return dict(actual_word_gate_passed=bool(passed),complete_before_rows=before,complete_after_rows=after,
        exact_before_signed_volume_mm3=rational(before_volume),exact_after_signed_volume_mm3=rational(after_volume),
        own_volume_equal=before_volume==after_volume,other_context_words_fixed=fixed,
        boundary_words_fixed=boundary,topology=topology_after,embedding_or_global_acceptance=False)

def endpoint_intake(endpoint,acceptance,points,cells,scopes,tuples,held):
    need(acceptance["decision"]=="ACCEPT_COMPLETE_FINITE_DIAGNOSTIC_ONLY_REJECT_ALL19_TUPLES"
        and acceptance["report"]==held["endpoint_result"]
        and acceptance["finite_accounting"]["independent_exact_rows"]==1415
        and acceptance["finite_accounting"]["quality_failed_tuples"]==19
        and acceptance["finite_accounting"]["negative_dispositions"]==42,
        "Accepted complete endpoint diagnostic, with every failure retained")
    for name in ("independent_result_review","independent_arithmetic_bindings","owner_review","owner_closure"):
        need(acceptance[name]==held["input_records"][acceptance[name]["path"]],
            "Accepted endpoint evidence association changed")
    need(endpoint["schema"]=="962-current24-saved-analytic-apex-component-candidates/v1"
        and endpoint["source"]==held["endpoint_source"] and endpoint["held_preparation"]==held["endpoint_held"]
        and endpoint["tuple_list"]==held["tuple_list"]
        and endpoint["tuple_count"]==19 and endpoint["complete_cell_disposition_count"]==916
        and endpoint["exact_quality_evaluation_count"]==916 and endpoint["all916_quality_evaluations_completed"]is True
        and endpoint["construction_refusal_count"]==0 and endpoint["exact_local_witness_tuple_IDs"]==[]
        and endpoint["original24_mesh_refusal_preserved"]is True,
        "Complete rejected endpoint family required")
    need(endpoint["input_records"]==strict_json(ROOT/held["endpoint_held"]["path"])["input_records"],
        "Endpoint inherited28 input map changed")
    for value in endpoint["qualification"].values():need(value is False,"Endpoint qualification retained false")
    baselines=endpoint["complete499_before_cell_rows"]
    need(len(baselines)==499 and len({x["tetrahedron_tag"]for x in baselines})==499,
        "Complete499 baseline associations")
    baseline={x["tetrahedron_tag"]:x for x in baselines}
    proposals=endpoint["complete24_face_proposals"]
    need(len(proposals)==24 and len({x["target_tetrahedron_tag"]for x in proposals})==24,
        "Complete24 endpoint face associations")
    by_target={x["target_tetrahedron_tag"]:x for x in proposals}
    out=[]
    need(len(endpoint["complete19_tuple_results"])==len(tuples)==19,"Complete19 endpoint tuple order")
    for descriptor,row in zip(tuples,endpoint["complete19_tuple_results"]):
        need({key:row[key]for key in descriptor}==descriptor and row["status"]=="rejected_tuple_retained"
            and row["all_component_exact_quality_gate"]is False and row["procedural_checks_passed"]is True
            and row["exact_signed_volume_equals_own_before"]is True,
            "Every tuple endpoint/procedural result and quality failure retained")
        chosen=row["selected_proposal_associations"]
        expected=descriptor["seed_choices"]
        need([(x["seed_node_tag"],x["target_tetrahedron_tag"])for x in chosen]==
            [(x["seed_node_tag"],x["target_tetrahedron_tag"])for x in expected],
            "Exact selected endpoint associations")
        final=dict(points)
        for q in chosen:
            p=by_target[q["target_tetrahedron_tag"]]
            need(q["status"]==p["status"]=="constructed_binary64_proposal_only"
                and q["seed_node_tag"]==p["seed_node_tag"]
                and q["coordinates_mm"]==p["coordinates_mm"] and q["binary64_hex"]==p["binary64_hex"],
                "Saved proposal/tuple word association")
            coords=coordinate_rows([dict(node_tag=q["seed_node_tag"],
                coordinates_mm=q["coordinates_mm"],binary64_hex=q["binary64_hex"])],[q["seed_node_tag"]])[0]
            final[q["seed_node_tag"]]=coords
        need([x["tetrahedron_tag"]for x in row["complete_cell_rows"]]==descriptor["full_tetrahedron_tags"],
            "Full endpoint cell order")
        out.append(dict(descriptor=descriptor,endpoints=final,
            baseline_rows=baseline,endpoint_rows={x["tetrahedron_tag"]:x for x in row["complete_cell_rows"]}))
    return out

def checked_endpoint_fraction(polyD,polyS,polyT,parameter,saved):
    d=qvalue(polyD.eval(parameter));s=qvalue(polyS.eval(parameter));f=qvalue(polyT.eval(parameter))
    q2=36*d*d/(s*f) if s*f>0 else None
    if parameter==0:need(d>0,"Every original current component determinant must remain positive")
    need(rational(d)==saved["exact_native_ordered_determinant_mm3"]
        and (None if q2 is None else rational(q2))==saved["exact_SICN_squared"]
        and saved["positive_orientation"]is(d>0)
        and saved["exact_point1_gate_passed"]is(d>0 and q2 is not None and q2>=Fraction(1,100)),
        "Polynomial endpoint agrees with every original exact row and failure")

def verify_lossless_gzip_bytes(compressed,manifest):
    """Bounded streaming byte identity only; never decode or validate scientific JSON."""
    need(type(compressed)is bytes and len(compressed)<=33554432,"Compressed input exceeds unchanged disk budget")
    logical=manifest["logical_payload"];stored=manifest["compressed_payload"]
    need(type(logical["bytes"])is int and 0<logical["bytes"]<=2147483648,
        "Declared inflation exceeds existing2GiB capacity ceiling")
    need(type(stored["bytes"])is int and stored["bytes"]==len(compressed)
        and stored["sha256"]==hashlib.sha256(compressed).hexdigest(),"Compressed byte identity")
    need(compressed[:10]==b"\x1f\x8b\x08\x00\x00\x00\x00\x00\x02\xff",
        "Fixed gzip header: no filename/extra/time fields; level9")
    count=0;digest=hashlib.sha256()
    with gzip.GzipFile(fileobj=io.BytesIO(compressed),mode="rb")as stream:
        while True:
            block=stream.read1(min(io.DEFAULT_BUFFER_SIZE,logical["bytes"]-count+1))
            if not block:break
            count+=len(block)
            need(count<=logical["bytes"] and count<=2147483648,"Declared bounded inflation exceeded")
            digest.update(block)
    need(count==logical["bytes"]and digest.hexdigest()==logical["sha256"],
        "Complete uncompressed byte count and SHA256; EOF/CRC required")
    return dict(bytes=count,sha256=digest.hexdigest(),complete_EOF_and_CRC=True)

def lossless_gzip_certificate(encoded,result):
    """Lossless storage of the identical complete JSON byte stream; no row projection."""
    need(type(encoded)is bytes and 0<len(encoded)<=2147483648,
        "Logical payload exceeds existing2GiB capacity ceiling")
    buffer=io.BytesIO()
    with gzip.GzipFile(filename="",mode="wb",compresslevel=9,fileobj=buffer,mtime=0)as stream:
        stream.write(encoded)
    compressed=buffer.getvalue()
    manifest=dict(schema="962-current24-complete-exact-segment-lossless-gzip-manifest/v1",
        status="complete_logical_certificate_stored_losslessly_scientific_review_pending",
        logical_schema=result["schema"],logical_status=result["status"],
        logical_payload=dict(filename="real-segment-feasibility.json",encoding="UTF-8",
            JSON_indent=2,JSON_allow_nan=False,trailing_newline=True,
            bytes=len(encoded),sha256=hashlib.sha256(encoded).hexdigest()),
        compressed_payload=dict(filename="real-segment-feasibility.json.gz",
            bytes=len(compressed),sha256=hashlib.sha256(compressed).hexdigest()),
        gzip_parameters=dict(mtime=0,filename="",compresslevel=9),
        source=result["source"],held_preparation=result["held_preparation"],own_actual=result["own_actual"],
        tuple_list=result["tuple_list"],segment_count=result["segment_count"],
        complete_cell_dispositions=result["complete_cell_dispositions"],
        complete_constraint_associations=result["complete_constraint_associations"],
        all_logical_coefficients_roots_factors_signs_intervals_witnesses_retained=True,
        binary64_word_proposal_count=0,binary64_word_construction_supported=False,
        scientific_result_accepted=False,qualification=result["qualification"],
        reader_capacity_ceiling_bytes=2147483648,
        reader_capacity_scope="Streaming count/hash ceiling only; not a JSON memory-fit, peak RSS or completion guarantee.")
    verify_lossless_gzip_bytes(compressed,manifest)
    manifest_bytes=(json.dumps(manifest,indent=2,allow_nan=False)+"\n").encode()
    return compressed,manifest_bytes

def run(actual_path,actual_sha256):
    need(actual_path.resolve()==ACTUAL,"Exact future segment actual path")
    need(isinstance(actual_sha256,str) and len(actual_sha256)==64
        and all(c in"0123456789abcdef"for c in actual_sha256),"External actual digest")
    need(record(ACTUAL)["sha256"]==actual_sha256,"Actual changed")
    actual=strict_json(ACTUAL);held=strict_json(HELD)
    need(actual["schema"]=="962-current24-exact-segment-real-feasibility-execution-authority/v1"
        and actual["saved_only_segment_feasibility_diagnostic_authorized"]is True
        and type(actual["execution_count"])is int and actual["execution_count"]==1,
        "Separate one-shot root authority required")
    for name in QUALIFICATION:need(actual[name]is False,"Forbidden authority:"+name)
    need(actual["binary64_word_construction_authorized"]is False,"No verified correct-rounding implementation")
    need(actual["worker"]==record(Path(__file__))==held["source"]
        and actual["held_preparation"]==record(HELD) and held["tuple_list"]==record(TUPLES),
        "Exact source/held/tuple identity")
    need(actual["input_records"]==held["input_records"],"Complete finite input map")
    for key in ("independent_source_review","root_source_admission","synthetic_guard_result","selected_root_runtime"):
        need(isinstance(actual[key],dict)and record(ROOT/actual[key]["path"])==actual[key],
            "Direct separately admitted metadata:"+key)
    verify_records(held["input_records"])
    need(not OUTPUT.exists()and not OUTPUT.is_symlink(),"Fresh fixed complete output")
    report=strict_json(ROOT/REPORT_REL);parent=strict_json(ROOT/PARENT_REL);closed=strict_json(ROOT/CLOSED_REL)
    faces,intake=current_faces(report,parent,closed,held)
    points,cells,scopes,tuples,protection=component_bindings(report,faces,strict_json(ROOT/FACE_REL),
        strict_json(ROOT/FACE_ROOT_REL),strict_json(ROOT/MANIFEST_REL),strict_json(ROOT/SELECTED_REL),
        strict_json(TUPLES),held)
    endpoint=strict_json(ROOT/held["endpoint_result"]["path"])
    acceptance=strict_json(ROOT/held["endpoint_root_acceptance"]["path"])
    family=endpoint_intake(endpoint,acceptance,points,cells,scopes,tuples,held)
    runtime=strict_json(ROOT/actual["selected_root_runtime"]["path"])
    need(runtime["sympy_version"]=="1.14.0"and runtime["exact_public_API_synthetic_probe_passed"]is True,
        "Separate pinned selected runtime and exact public API fixture result required")
    sp,library_observations=root_library()
    outcomes=[];dispositions=0;by_id={x["component_ID"]:x for x in scopes}
    for case in family:
        descriptor=case["descriptor"];scope=by_id[descriptor["component_ID"]]
        local={t:cells[t]for t in descriptor["full_tetrahedron_tags"]}
        topology=topology_diagnostic(local,None)
        need(topology["nonmanifold_faces"]==0 and topology["same_oriented_internal_faces"]==0
            and not(set(scope["movable_node_tags"])&{n for f in topology["oriented_boundary_faces"]for n in f}),
            "Complete fixed oriented local boundary")
        need(all(struct.pack("<3d",*points[n])==struct.pack("<3d",*case["endpoints"][n])
            for n in points if n not in scope["movable_node_tags"]),"All non-seed context words fixed")
        constraints=[];cell_rows=[];volume=None
        for tag,conn in sorted(local.items()):
            d,s,f,p=polynomial_cell([points[n]for n in conn],[case["endpoints"][n]for n in conn],sp)
            checked_endpoint_fraction(d,s,f,0,case["baseline_rows"][tag])
            checked_endpoint_fraction(d,s,f,1,case["endpoint_rows"][tag])
            volume=d if volume is None else volume+d
            di=len(constraints);constraints.append(dict(cell_tag=tag,kind="D",poly=d))
            pi=len(constraints);constraints.append(dict(cell_tag=tag,kind="P",poly=p))
            cell_rows.append(dict(tetrahedron_tag=tag,ordered_node_tags=conn,
                original_vertices_mm=[points[n]for n in conn],endpoint_vertices_mm=[case["endpoints"][n]for n in conn],
                D=poly_data(d),S=poly_data(s),T=poly_data(f),P=poly_data(p),
                D_constraint_ID=di,P_constraint_ID=pi))
        need(volume is not None and volume==sp.Poly(volume.eval(0),*volume.gens,domain="QQ"),
            "Own complete signed-volume polynomial is exactly constant")
        decomposition=sign_decomposition(constraints,sp)
        outcomes.append(dict(descriptor,complete_cell_polynomials=cell_rows,
            complete_constraint_count=len(constraints),own_summed_determinant_polynomial=poly_data(volume),
            own_signed_volume_polynomial_constant=True,fixed_oriented_boundary=topology,
            real_feasibility=decomposition,word_construction_status="UNSUPPORTED_NOT_ATTEMPTED",
            rounded_word_proposals=[],word_rechecks=[],candidate_or_geometry_application=False))
        dispositions+=len(cell_rows)
    need(len(outcomes)==19 and dispositions==916,"Every19 segment/916 cell association completed")
    verify_records(held["input_records"])
    need(record(ACTUAL)["sha256"]==actual_sha256 and record(Path(__file__))==held["source"]
        and record(HELD)==actual["held_preparation"]and record(TUPLES)==held["tuple_list"],
        "Source/actual/held/tuple identities unchanged")
    for key in ("independent_source_review","root_source_admission","synthetic_guard_result","selected_root_runtime"):
        need(record(ROOT/actual[key]["path"])==actual[key],"Direct metadata changed")
    result=dict(schema="962-current24-complete-exact-segment-real-feasibility/v1",
        status="complete_exact_real_feasibility_on19_saved_segments_only",
        source=record(Path(__file__)),held_preparation=record(HELD),own_actual=record(ACTUAL),
        endpoint_result=held["endpoint_result"],endpoint_root_acceptance=held["endpoint_root_acceptance"],
        tuple_list=record(TUPLES),input_records=held["input_records"],
        selected_root_library_observations=library_observations,
        intake=intake,protection=protection,complete19_segments=outcomes,
        segment_count=19,complete_cell_dispositions=916,complete_constraint_associations=1832,
        all475_good_24poor_33shared_in_complete499_scope=True,
        original_endpoint_failures_preserved=True,original24_whole_mesh_refusal_preserved=True,
        every_sign_range_and_singleton_retained=True,correct_binary64_rounding_supported=False,
        binary64_word_proposal_count=0,binary64_existence_or_completeness=False,
        global_infeasibility_proved=False,source_BIN_identity=None,explicit_exterior_facet_membership=None,
        raw_MSH_BIN_body_access=False,native_call_count=0,optimizer_call_count=0,geometry_write_count=0,
        quality_or_root_runtime_bound_promised=False,qualification=QUALIFICATION)
    encoded=(json.dumps(result,indent=2,allow_nan=False)+"\n").encode()
    compressed,manifest_bytes=lossless_gzip_certificate(encoded,result)
    summary=dict(status=result["status"],segments=19,cell_dispositions=916,
        complete_real_feasibility=True,word_proposals=0)
    summary_bytes=(json.dumps(summary)+"\n").encode()
    need(len(compressed)+len(manifest_bytes)+len(summary_bytes)<=33554432,
        "Complete compressed certificate/manifest/stdout exceed unchanged output budget; refuse without truncation")
    OUTPUT.mkdir()
    with(OUTPUT/"real-segment-feasibility.json.gz").open("xb")as stream:stream.write(compressed)
    with(OUTPUT/"manifest.json").open("xb")as stream:stream.write(manifest_bytes)
    print(json.dumps(summary))
    return 0


if __name__=="__main__":
    parser=argparse.ArgumentParser(description="Held exact19-segment saved-only feasibility diagnostic")
    parser.add_argument("--actual",type=Path,required=True);parser.add_argument("--actual-sha256",required=True)
    args=parser.parse_args()
    try:sys.exit(run(args.actual,args.actual_sha256))
    except(ValueError,KeyError,TypeError,NotImplementedError)as error:
        print(type(error).__name__+": "+str(error),file=sys.stderr);sys.exit(2)
