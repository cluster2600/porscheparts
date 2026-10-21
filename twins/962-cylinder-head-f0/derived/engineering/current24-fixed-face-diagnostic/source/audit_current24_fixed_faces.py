"""Held saved-only exact fixed-face screen for all accepted current24 poor cells.

No native API, optimiser, mesh writer, raw mesh/BIN reader or runtime loader.
The loose certificate and coordinate-word helper are copied unchanged.
A separate root actual plus external SHA-256 is required before any input read.
"""
import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

ROOT=Path(__file__).resolve().parents[3]
PREP=Path(__file__).resolve().parent
HELD=PREP/"held-preparation.json"
ACTUAL=ROOT/"work/962-engineering/head-star-current24-fixed-face-obstruction-execution-prep-001/actual-contract.json"
OUTPUT=ROOT/"work/962-engineering/head-star-current24-fixed-face-obstruction-001"
REPORT_REL="work/962-engineering/head-star-current110-pass62-application-001/worker-report.json"
PARENT_REL="work/962-engineering/head-star-current110-pass62-application-root-execution-001/result-peer-acceptance.json"
CLOSED_REL="work/962-engineering/head-star-current110-pass62-application-root-execution-001/closed-result.json"
BOUNDARY=871731
QUALIFICATION=dict(head_PDE_authorized=False,engineering_accepted=False,physics_qualified=False,
    material_qualified=False,process_calibrated=False,manufacturing_authorized=False,
    native_execution_authorized=False,optimizer_execution_authorized=False,remeshing_authorized=False,
    surface_retriangulation_authorized=False,automatic_retry=False,global_infeasibility_proved=False)

def rational(value):
    return dict(numerator=str(value.numerator),denominator=str(value.denominator))

def certificate(coordinates):
    if len(coordinates)!=3 or any(len(row)!=3 for row in coordinates):
        raise ValueError("Exactly three 3D binary64 coordinates required")
    if not all(math.isfinite(float(x)) for row in coordinates for x in row):
        raise ValueError("Finite binary64 coordinates required")
    p=[[Fraction.from_float(float(x)) for x in row] for row in coordinates]
    u=[p[1][k]-p[0][k] for k in range(3)]
    v=[p[2][k]-p[0][k] for k in range(3)]
    cross=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
    cross_squared=sum(x*x for x in cross)
    edge_sum=sum((p[a][k]-p[b][k])**2 for a,b in [(0,1),(1,2),(2,0)] for k in range(3))
    if cross_squared<=0 or edge_sum<=0:
        raise ValueError("Nondegenerate linear triangle required")
    left,right=2700*cross_squared,edge_sum**2
    return dict(arithmetic="Fraction.from_float preserves each input binary64 value exactly; all following operations are rational.",
        cross_squared_mm4=rational(cross_squared),sum_squared_edge_lengths_mm2=rational(edge_sum),
        exact_triangle_SICN_squared=rational(12*cross_squared/right),
        exact_loose_tetra_SICN_squared_upper_bound=rational(27*cross_squared/right),
        inequality_left_2700_cross_squared=rational(left),inequality_right_edge_sum_squared=rational(right),
        exact_strict_inequality_2700_cross_squared_lt_edge_sum_squared=bool(left<right),
        no_positive_linear_tetrahedron_with_this_fixed_face_can_reach_SICN_point1=bool(left<right),
        no_square_root_or_floating_tolerance_used=True)

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


def sharp_comparison(triangle_sicn_squared):
    """Separate sharp test; equality is retained and never called an obstruction."""
    if type(triangle_sicn_squared) is not Fraction or not 0<triangle_sicn_squared<=1:
        raise ValueError("Positive exact physical triangle SICN squared required")
    threshold=Fraction(4,841)
    relation=("strict_obstruction" if triangle_sicn_squared<threshold else
        "equality" if triangle_sicn_squared==threshold else "not_obstructed_by_this_test")
    return dict(exact_threshold_squared=rational(threshold),classification=relation,
        fixed_face_strict_ceiling_below_point1=relation=="strict_obstruction",
        equality_real_apex_ceiling_is_point1=relation=="equality",
        feasible_binary64_apex_or_coupled_solution_established=False,
        exterior_face_membership=None,global_head_infeasibility_established=False)


def fixed_face_certificates(coordinates):
    loose=certificate(coordinates)
    q=loose["exact_triangle_SICN_squared"]
    sharp=sharp_comparison(Fraction(int(q["numerator"]),int(q["denominator"])))
    return dict(preserved_loose_2700_certificate=loose,separate_sharp_4_over_841_test=sharp)


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


def run(actual_path,actual_sha256):
    need(actual_path.resolve()==ACTUAL,"Exact future root actual path required")
    need(isinstance(actual_sha256,str) and len(actual_sha256)==64
        and all(c in "0123456789abcdef" for c in actual_sha256),"External actual digest required")
    need(record(ACTUAL)["sha256"]==actual_sha256,"Actual digest changed")
    actual=strict_json(ACTUAL)
    need(actual["schema"]=="962-current24-fixed-face-saved-diagnostic-execution-authority/v1"
        and actual["saved_only_diagnostic_authorized"] is True and actual["execution_count"]==1,
        "Separate one-shot root saved-only diagnostic authority required")
    for name in QUALIFICATION:need(actual[name] is False,"Forbidden authority: "+name)
    need(actual["worker"]==record(Path(__file__)) and actual["held_preparation"]==record(HELD),
        "Actual source/held bindings required")
    held=strict_json(HELD)
    need(held["schema"]=="962-current24-fixed-face-obstruction-source-held/v1"
        and held["source"]==record(Path(__file__)),"Source-held binding changed")
    need(actual["input_records"]==held["input_records"],"Actual must preserve complete held input map")
    for name in ("independent_source_review","root_source_admission","synthetic_guard_result"):
        need(isinstance(actual[name],dict) and record(ROOT/actual[name]["path"])==actual[name],
            "Direct future source review/admission/guard metadata binding required")
    verify_records(held["input_records"])
    report=strict_json(ROOT/REPORT_REL);parent=strict_json(ROOT/PARENT_REL);closed=strict_json(ROOT/CLOSED_REL)
    faces,intake=current_faces(report,parent,closed,held)
    need(not OUTPUT.exists() and not OUTPUT.is_symlink(),"Fresh fixed output directory required")
    results=[];refusals=[]
    for face in faces:
        row=dict(face)
        try:
            row["certificates"]=fixed_face_certificates(face["coordinates_mm"])
            row["status"]="complete_exact_saved_fixed_face_diagnostic_only"
        except ValueError as error:
            row["status"]="refused_invalid_fixed_face_retained";row["error"]=str(error);refusals.append(face["tetrahedron_tag"])
        results.append(row)
    need(len(results)==24,"Complete24 diagnostic or refusal rows required")
    verify_records(held["input_records"])
    need(record(ACTUAL)["sha256"]==actual_sha256 and actual["worker"]==record(Path(__file__))
        and actual["held_preparation"]==record(HELD),"Actual/source/held changed")
    for name in ("independent_source_review","root_source_admission","synthetic_guard_result"):
        need(record(ROOT/actual[name]["path"])==actual[name],"Direct admission metadata changed")
    counts={name:sum(row.get("certificates",{}).get("separate_sharp_4_over_841_test",{}).get("classification")==name
        for row in results) for name in ("strict_obstruction","equality","not_obstructed_by_this_test")}
    result=dict(schema="962-current24-saved-fixed-face-exact-diagnostic/v1",
        status="refused_invalid_fixed_face_rows_preserved" if refusals else "complete_saved_fixed_face_diagnostic_only",
        own_actual=record(ACTUAL),source=record(Path(__file__)),held_preparation=record(HELD),
        input_records=held["input_records"],parent_acceptance=held["input_records"][PARENT_REL],
        accepted_saved_mesh_identity_metadata_only=held["opaque_saved_mesh_identity"],
        intake=intake,complete24_rows=results,sharp_classification_counts=counts,refused_tetrahedron_tags=refusals,
        all24_rows_retained=True,all_bound_metadata_unchanged=True,
        source_BIN_identity=None,source_BIN_or_explicit_exterior_membership=None,
        prior_surface_report_is_historical_necessary_screen_only=True,
        independently_measured_explicit_exterior_facet_membership=False,
        fixed_face_test_nonobstruction_implies_feasibility=False,
        equality_implies_binary64_or_coupled_feasibility=False,
        original24_mesh_quality_refusal_preserved=True,accepted86_improvements_untouched=True,
        native_quality_recomputed=False,optimizer_calls=0,native_calls=0,geometry_writes=0,
        runtime_loaded_or_hashed=False,qualification=QUALIFICATION)
    OUTPUT.mkdir()
    (OUTPUT/"fixed-face-report.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps(dict(status=result["status"],counts=counts,refused=len(refusals))))
    return 2 if refusals else 0


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--actual",type=Path,required=True)
    parser.add_argument("--actual-sha256",required=True)
    args=parser.parse_args()
    try:sys.exit(run(args.actual,args.actual_sha256))
    except (ValueError,KeyError,TypeError,OSError) as error:
        print("Refused saved-only fixed-face diagnostic: "+str(error),file=sys.stderr);sys.exit(2)
