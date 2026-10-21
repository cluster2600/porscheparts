"""HELD source proposal: finite saved-context interior2<->3 cavity screen.

No entry point, file IO, mesh writer, actual contract, execution authority or
application policy. Functions below are UNRUN on real or synthetic inputs.
Local exact passes never establish global/interface eligibility.
"""
from fractions import Fraction
import hashlib
from itertools import combinations
import math
import struct

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


def enumerate_associations(context):
    """All distinct saved face/edge associations touching at least one poor cell.

    A pattern is provisional until full ownership and exact geometry are checked.
    Missing owners are never supplied. No subset of a larger observed edge star
    is tried. Maximum associations24*(4+6)=240, independent of coordinates.
    """
    cells=context["cells"];poor=context["poor"];seeds=context["seeds"]
    result=[]
    for size,kind,wanted in [(3,"2_to_3",2),(2,"3_to_2",3)]:
        owners={}
        for tag,conn in sorted(cells.items()):
            for simplex in combinations(sorted(conn),size):owners.setdefault(simplex,[]).append(tag)
        for simplex,tags in sorted(owners.items()):
            if not poor.intersection(tags):continue
            union=set().union(*(set(cells[t]) for t in tags))
            proposed=[];triangle=[];apices=[]
            pattern=len(tags)==wanted and len(union)==5
            if kind=="2_to_3" and pattern:
                triangle=list(simplex);apices=sorted(union-set(simplex))
                pattern=all(len(set(cells[t])-set(simplex))==1 for t in tags)
                proposed=[tuple(apices+list(edge)) for edge in combinations(triangle,2)]
            elif kind=="3_to_2" and pattern:
                apices=list(simplex);triangle=sorted(union-set(simplex))
                pattern={frozenset(cells[t]) for t in tags}=={
                    frozenset(apices+list(edge)) for edge in combinations(triangle,2)}
                proposed=[tuple(triangle+[v]) for v in apices]
            if not pattern:proposed=[]
            new_simplex=tuple(apices if kind=="2_to_3" else triangle) if pattern else ()
            result.append(dict(association_ID=kind+":"+",".join(map(str,simplex)),kind=kind,
                removed_simplex=list(simplex),observed_owner_tags=tags,
                poor_owner_tags=sorted(poor.intersection(tags)),
                complete_removed_simplex_owner_scope=bool(seeds.intersection(simplex)),
                owner_scope_basis="complete saved seed star" if seeds.intersection(simplex)
                    else "outside owners unavailable in saved499 context",
                expected_owner_count=wanted,observed_bistellar_pattern=pattern,
                five_node_tags=sorted(union) if pattern else None,
                triangle=triangle if pattern else None,apices=apices if pattern else None,
                replacement_unoriented_cells=[list(c) for c in proposed],
                introduced_simplex=list(new_simplex),
                complete_introduced_simplex_owner_scope=bool(seeds.intersection(new_simplex))))
    need(len(result)<=240,"Complete finite poor-feature association bound exceeded")
    need({p for a in result for p in a["poor_owner_tags"]}==poor,"All24 poor memberships required")
    return result


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


def screen_local_cavity(context,association):
    """One exact fixed-word local screen; no complete eligibility/application."""
    result=dict(association_ID=association["association_ID"],local_result="not_screened",
                complete_flip_eligibility=None,mesh_application_authorized=False,
                global_embedding_or_nonoverlap_proved=False,
                source_exterior_or_BIN_membership=None,
                per_cell_region_and_interface_preservation=None,
                missing_evidence=["per-cell geometric entity/physical region labels",
                    "internal facet/edge classification and interface labels",
                    "source exterior/BIN membership and global embedding"])
    if not association["observed_bistellar_pattern"]:
        result["local_result"]="refused_observed_incidence_not_2_or_3_five_point_pattern"
        return result
    cells=context["cells"];points=context["points"];oldtags=association["observed_owner_tags"]
    old=[cells[t] for t in oldtags];proposed=association["replacement_unoriented_cells"]
    need(not set(oldtags)&context["protected_cells"],"Protected1983 cells cannot be removed")
    snapshot={t:tuple(float(x).hex() for x in p) for t,p in points.items()}
    need(snapshot==context["words"],"Full271 input word identity required")
    new=[];newrows=[];oldrows=[];reasons=[]
    for tag,conn in zip(oldtags,old):
        d,q2=exact_quality([points[t] for t in conn])
        oldrows.append(dict(tetrahedron_tag=tag,ordered_node_tags=list(conn),
            determinant_mm3=rational(d),SICN_squared=None if q2 is None else rational(q2)))
        if d<=0:reasons.append("nonpositive original cavity cell")
    for index,conn in enumerate(proposed,1):
        conn=list(conn);d,q2=exact_quality([points[t] for t in conn])
        if d<0:
            conn[-1],conn[-2]=conn[-2],conn[-1]
            d,q2=exact_quality([points[t] for t in conn])
        passed=d>0 and q2 is not None and q2>=Fraction(1,100)
        new.append(tuple(conn));newrows.append(dict(symbolic_slot=index,ordered_node_tags=conn,
            determinant_mm3=rational(d),SICN_squared=None if q2 is None else rational(q2),
            positive_and_SICN_point1=passed))
        if not passed:reasons.append("replacement quality/orientation failure")
    oldok,ob=oriented_boundary(old);newok,nb=oriented_boundary(new)
    if not oldok or not newok or ob!=nb or len(ob)!=6:
        reasons.append("oriented six-face boundary/internal cancellation mismatch")
    # Six strict supporting triangles certify this convex triangular bipyramid.
    # Their orientation is the outward orientation of the original positive cells.
    support=[];vertices=association["five_node_tags"]
    for face in ob:
        remaining=sorted(set(vertices)-set(face));determinants=[]
        for t in remaining:
            d,_=exact_quality([points[n] for n in face+(t,)])
            determinants.append(d)
        passed=len(remaining)==2 and all(d<0 for d in determinants)
        support.append(dict(oriented_face=list(face),other_node_tags=remaining,
            determinants_mm3=[rational(d) for d in determinants],strict_outward_support=passed))
        if not passed:reasons.append("not a strictly convex five-point cavity")
    oldsum=sum((Fraction(int(r["determinant_mm3"]["numerator"]),int(r["determinant_mm3"]["denominator"])) for r in oldrows),Fraction())
    newsum=sum((Fraction(int(r["determinant_mm3"]["numerator"]),int(r["determinant_mm3"]["denominator"])) for r in newrows),Fraction())
    if oldsum!=newsum:reasons.append("exact signed-volume mismatch")
    keys=[frozenset(c) for c in new]
    if len(keys)!=len(set(keys)):reasons.append("duplicate replacement cells")
    complement={frozenset(c):t for t,c in cells.items() if t not in oldtags}
    duplicate=[dict(symbolic_slot=i+1,existing_tetrahedron_tag=complement[k])
               for i,k in enumerate(keys) if k in complement]
    if duplicate:reasons.append("replacement duplicates observed unchanged cell")
    introduced=set(association["introduced_simplex"])
    outside=[t for t,c in sorted(cells.items()) if introduced.issubset(c) and t not in oldtags]
    if outside:reasons.append("introduced simplex already present in observed complement")
    if not association["complete_removed_simplex_owner_scope"]:
        result["missing_evidence"].append("complete outside owners of removed simplex")
    if not association["complete_introduced_simplex_owner_scope"]:
        result["missing_evidence"].append("global absence of introduced simplex/duplicates")
    need(snapshot=={t:tuple(float(x).hex() for x in p) for t,p in points.items()},
         "No271 coordinate word may change")
    result.update(local_result="failed_exact_local_screen" if reasons else "passed_exact_local_screen_only",
        reasons=sorted(set(reasons)),original_cells=oldrows,replacement_cells=newrows,
        oriented_boundary_original=[list(f) for f in ob],oriented_boundary_replacement=[list(f) for f in nb],
        strict_support_witnesses=support,original_signed_volume_mm3=rational(oldsum/6),
        replacement_signed_volume_mm3=rational(newsum/6),exact_volume_equal=oldsum==newsum,
        observed_duplicate_cells=duplicate,introduced_simplex_observed_outside_owners=outside,
        all271_coordinate_words_unchanged=True,protected1983_removed_cells_disjoint=True,
        all_unremoved_saved_good_shared_and_poor_cells_unchanged_by_construction=True)
    return result


def association_conflicts(associations):
    """Complete pair table for observed overlaps/duplicate proposed4-sets only.

    No compatible subset, combined feasibility or global-conflict proof is made.
    """
    conflicts=[]
    for a,b in combinations(associations,2):
        if not a["observed_bistellar_pattern"] or not b["observed_bistellar_pattern"]:continue
        overlap=sorted(set(a["observed_owner_tags"])&set(b["observed_owner_tags"]))
        common={tuple(sorted(c)) for c in a["replacement_unoriented_cells"]}&{
            tuple(sorted(c)) for c in b["replacement_unoriented_cells"]}
        if overlap or common:
            conflicts.append(dict(association_IDs=[a["association_ID"],b["association_ID"]],
                shared_removed_cell_tags=overlap,duplicate_replacement4sets=[list(c) for c in sorted(common)]))
    return conflicts
