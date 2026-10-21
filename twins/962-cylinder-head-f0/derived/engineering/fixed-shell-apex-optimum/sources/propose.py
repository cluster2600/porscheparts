"""HELD deterministic two-apex JSON proposal; no native application or mesh write."""
from pathlib import Path
from fractions import Fraction
import hashlib,json,math,struct,sys,time

ROOT=Path(__file__).resolve().parents[3]
ARRAYS='work/962-engineering/fixed-shell-netgen-apex1435493-001/arrays.json'
WORKER='work/962-engineering/fixed-shell-netgen-apex1435493-001/fixture-report.json'
SHELL='work/962-engineering/direct-sicn-apex1435493-cavity-study-001/local-shell-input-001.json'
INPUTS={ARRAYS:'ace411a27a13332129f515ac456ab453cbede0920fe115bdb82057092e665e5f',
 WORKER:'8529a8f8421dd989ae243b2a06b132b8a2952e9847aa31d34adb74289a16e6c7',
 SHELL:'a6f15db60967807b057e357b8f159fa510c4a8cf6e3cb44c4327323c070398c8'}
TARGETS={198:[29,4,5,6],204:[28,7,9,8]}
QUALIFICATION=dict(native_application_authorized=False,head_execution_authorized=False,stitching_authorized=False,
 engineering_accepted=False,physics_qualified=False,manufacturing_authorized=False)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

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


def optimal_apex(coordinates,free):
    if type(free) is not int or not 0<=free<4:raise ValueError('One original local apex position required')
    old_det,_=exact_quality(coordinates)
    if old_det<=0:raise ValueError('Positive original native-order determinant required')
    p=[[Fraction.from_float(float(x)) for x in row] for row in coordinates]
    fixed=[row for i,row in enumerate(p) if i!=free]
    centre=[sum(row[k] for row in fixed)/3 for k in range(3)]
    normal=cross(subtract(fixed[1],fixed[0]),subtract(fixed[2],fixed[0]));C=dot(normal,normal)
    side=dot(normal,subtract(p[free],centre))
    if C<=0 or side!=(-1)**(3-free)*old_det:raise ValueError('Nondegenerate fixed face and exact old-side association required')
    T=Fraction(4,3)*C;height=math.sqrt(2./3.)*math.sqrt(math.sqrt(float(T)));length=math.sqrt(float(C))
    direction=1 if side>0 else -1
    xyz=[float(centre[k])+direction*height*float(normal[k])/length for k in range(3)]
    if any(not math.isfinite(v) for v in xyz):raise ValueError('Finite rounded proposal coordinates required')
    return xyz,dict(exact_fixed_face_certificate=certificate([[float(v) for v in row] for row in fixed]),
        exact_T_mm4=rational(T),exact_face_centroid_mm=[rational(v) for v in centre],
        old_side_sign=direction,physical_height_mm_approximate=height,
        formula='centroid + old_side * sqrt(2/3)*T^(1/4) * unit_face_normal',
        real_isolated_optimum_not_a_rounded_or_joint_quality_certificate=True)


def replace_selected(points,proposed):
    if set(proposed)!={28,29} or not set(proposed)<=set(points):raise ValueError('Only both fixed selected tags28 and29 may be proposed')
    result={tag:list(xyz) for tag,xyz in points.items()}
    for tag,xyz in proposed.items():
        if len(xyz)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in xyz):raise ValueError('Finite selected coordinate row required')
        result[tag]=[float(v) for v in xyz]
    if any(struct.pack('<3d',*result[t])!=struct.pack('<3d',*points[t]) for t in points if t not in proposed):
        raise ValueError('Every unselected coordinate bit, including27/all16shell nodes, must remain exact')
    return result


def require_input_bindings(pins):
    if any(pins.get(path)!=digest for path,digest in INPUTS.items()):raise ValueError('Exact single saved-state input pins required')


def typed_state(a):
    return (struct.pack('<'+'Q'*len(a['node_tags']),*a['node_tags']),
        struct.pack('<'+'d'*(3*len(a['coordinates_mm'])),*[v for row in a['coordinates_mm'] for v in row]),
        struct.pack('<'+'Q'*len(a['tetra_tags']),*a['tetra_tags']),
        struct.pack('<'+'Q'*(4*len(a['tetra_node_tags'])),*[v for row in a['tetra_node_tags'] for v in row]),
        *[struct.pack('<'+'d'*len(a['native_qualities'][name]),*a['native_qualities'][name]) for name in ['SICN','Jacobian','native_volume_mm3']],
        struct.pack('<'+'d'*len(a['independent_signed_volume_mm3']),*a['independent_signed_volume_mm3']))


def before_state(worker,arrays,shell):
    a=arrays['saved_reopen'];r=worker['saved_reopen']
    if (worker.get('status')!='completed_specific_cavity_Netgen_only' or worker.get('fixture_procedural_checks_passed') is not True
        or worker.get('actual_SICN_gate_passed') is not False or worker.get('saved_mesh_identity_exact') is not True
        or worker.get('bound_inputs_unchanged') is not True or worker.get('full_tiny_arrays_sha256')!=INPUTS[ARRAYS]
        or (r['nodes'],r['tetrahedra'],r['referenced_interior_nodes'],r['unreferenced_nodes'])!=(19,39,3,0)
        or a['node_tags']!=list(range(1,17))+[27,28,29] or len(a['coordinates_mm'])!=19
        or len(a['tetra_tags'])!=39 or a['tetra_tags']!=sorted(set(a['tetra_tags']))
        or len(a['tetra_node_tags'])!=39 or any(len(t)!=4 or len(set(t))!=4 or not set(t)<=set(a['node_tags']) for t in a['tetra_node_tags'])
        or any(len(a['native_qualities'][name])!=39 for name in ['SICN','Jacobian','native_volume_mm3'])
        or len(a['independent_signed_volume_mm3'])!=39 or typed_state(a)!=typed_state(arrays['after'])):
        raise ValueError('Exact complete current19node/39cell saved-after state required')
    state=typed_state(a)
    for key,value in zip(['sorted_node_tags_sha256','sorted_coordinates_sha256','tetra_tags_sha256','tagged_tetra_connectivity_sha256'],state[:4]):
        if hashlib.sha256(value).hexdigest()!=r[key]:raise ValueError('Fresh typed arrays differ from native saved report')
    if worker['after']!=r:raise ValueError('Full saved/after reports differ')
    points=dict(zip(a['node_tags'],a['coordinates_mm']));cells=dict(zip(a['tetra_tags'],a['tetra_node_tags']))
    if set(v for row in cells.values() for v in row)!=set(points):raise ValueError('Unreferenced nodes prohibited')
    if any(cells.get(tag)!=row for tag,row in TARGETS.items()):raise ValueError('Exact two poor-cell ordered tags required')
    if sorted(t for t,q in zip(a['tetra_tags'],a['native_qualities']['SICN']) if q<.1)!=[198,204]:raise ValueError('Exactly the two current native poor cells required')
    if any(not math.isfinite(v) for row in points.values() for v in row):raise ValueError('Finite source coordinates required')
    for row in shell['vertex_rows']:
        if struct.pack('<3d',*points[row['local_node_tag']]).hex()!=row['binary64_little_endian_bytes_hex']:raise ValueError('All16 frozen shell bits required')
    return points,cells,a


def topology_diagnostic(cells,shell):
    def canonical(face):
        face=tuple(face);i=face.index(min(face));return face[i:]+face[:i]
    incidence={}
    for row in cells.values():
        for corners in [(0,2,1),(0,1,3),(1,2,3),(2,0,3)]:
            face=tuple(row[i] for i in corners);incidence.setdefault(tuple(sorted(face)),[]).append(face)
    exterior=[rows[0] for rows in incidence.values() if len(rows)==1]
    return dict(boundary_faces=len(exterior),internal_face_pairs=sum(len(rows)==2 for rows in incidence.values()),
        nonmanifold_faces=sum(len(rows)>2 for rows in incidence.values()),
        same_oriented_internal_faces=sum(len(rows)==2 and canonical(rows[0])!=canonical(rows[1][::-1]) for rows in incidence.values()),
        exact28_oriented_shell_faces=sorted(canonical(face) for face in exterior)==sorted(canonical(row['local_node_tags']) for row in shell['oriented_triangle_rows']),
        unchanged_all39_ordered_connectivity=True,geometric_overlap_or_intersection_checked=False)


def main(contract_path,digest):
    started=time.monotonic();contract_path=Path(contract_path)
    if len(digest)!=64 or sha(contract_path)!=digest:raise ValueError('Exact external actual contract digest required')
    c=json.loads(contract_path.read_text());require_input_bindings(c['input_hashes'])
    if (c.get('diagnostic_execution_authorized') is not True or c.get('root_and_peer_review_complete') is not True
        or c.get('qualification')!=QUALIFICATION or c.get('selected_tags')!=[28,29]
        or c.get('automatic_retry') is not False or c.get('method')!='one_fixed_face_optimum_per_selected_apex'
        or c.get('native_execution_authorized') is not False or c.get('sicn_gate')!=.1):raise ValueError('Reviewed single stdlib proposal query only')
    if sha(__file__)!=c['source_sha256'] or sha(Path(sys.executable).resolve())!=c['python_sha256']:raise ValueError('Exact source/interpreter binding required')
    for name,value in c['input_hashes'].items():
        if Path(name).is_absolute() or not (ROOT/name).resolve().is_relative_to(ROOT) or sha(ROOT/name)!=value:raise ValueError('Before input drift: '+name)
    if not isinstance(c.get('output_directory'),str):raise ValueError('Actual fresh output required')
    output=(ROOT/c['output_directory']).resolve()
    if output.parent!=ROOT/'work/962-engineering' or output.exists() or output.is_symlink():raise ValueError('Fresh one-query output required')
    worker=json.loads((ROOT/WORKER).read_text());arrays=json.loads((ROOT/ARRAYS).read_text());shell=json.loads((ROOT/SHELL).read_text())
    points,cells,a=before_state(worker,arrays,shell);proposed={};target_rows=[]
    for tag,row in TARGETS.items():
        free=next(i for i,t in enumerate(row) if t>16);node=row[free]
        xyz,proof=optimal_apex([points[t] for t in row],free);proposed[node]=xyz
        target_rows.append(dict(source_tetrahedron_tag=tag,selected_node_tag=node,fixed_face_node_tags=[t for t in row if t!=node],
            coordinates_mm=xyz,binary64_hex=[v.hex() for v in xyz],isolated_formula=proof))
    after=replace_selected(points,proposed);rows=[]
    for tag,row in cells.items():
        det,q2=exact_quality([after[t] for t in row]);passed=det>0 and q2 is not None and q2>=Fraction(1,100)
        approximate=(1 if det>0 else -1 if det<0 else 0)*math.sqrt(float(q2)) if q2 is not None else None
        rows.append(dict(tetrahedron_tag=tag,ordered_node_tags=row,exact_native_ordered_determinant_mm3=rational(det),
            exact_SICN_squared=None if q2 is None else rational(q2),signed_SICN_approximate=approximate,
            positive_orientation=det>0,strict_point1_gate_passed=passed))
    passed=all(row['strict_point1_gate_passed'] for row in rows)
    topology=topology_diagnostic(cells,shell)
    if not topology['exact28_oriented_shell_faces'] or topology['nonmanifold_faces'] or topology['same_oriented_internal_faces']:
        raise ValueError('Frozen complete connectivity/shell incidence changed')
    before_volume=sum((exact_quality([points[t] for t in row])[0]/6 for row in cells.values()),Fraction(0))
    after_volume=sum((Fraction(int(row['exact_native_ordered_determinant_mm3']['numerator']),int(row['exact_native_ordered_determinant_mm3']['denominator']))/6 for row in rows),Fraction(0))
    reference=Fraction(shell['exact_enclosed_volume_mm3']['numerator'],shell['exact_enclosed_volume_mm3']['denominator'])
    if before_volume!=reference or after_volume!=reference:raise ValueError('Exact full signed-volume bookkeeping changed')
    unchanged=all(struct.pack('<3d',*points[t])==struct.pack('<3d',*after[t]) for t in points if t not in [28,29])
    if not unchanged:raise ValueError('Unselected bits changed')
    if any(sha(ROOT/name)!=value for name,value in c['input_hashes'].items()) or sha(contract_path)!=digest:raise ValueError('After input/contract drift')
    report=dict(schema='962-specific-cavity-two-apex-analytic-diagnostic/v1',status='analytic_all39_pass_native_application_unapproved' if passed else 'rejected_analytic_candidate_retained',
        contract_sha256=digest,input_sha256s=c['input_hashes'],single_formula_proposal=True,selected_tags=[28,29],
        full_cells=39,full_nodes=19,all39_analytic_point1_gate_passed=passed,
        positive_poor_cell_tags=[row['tetrahedron_tag'] for row in rows if row['positive_orientation'] and not row['strict_point1_gate_passed']],
        nonpositive_or_undefined_cell_tags=[row['tetrahedron_tag'] for row in rows if not row['positive_orientation'] or row['exact_SICN_squared'] is None],
        targets=target_rows,all39_signed_quality_rows=rows,
        topology_diagnostic=topology,exact_before_signed_volume_mm3=rational(before_volume),exact_proposed_signed_volume_mm3=rational(after_volume),
        complete_proposed_coordinate_rows=[dict(node_tag=t,coordinates_mm=after[t],binary64_hex=[float(v).hex() for v in after[t]]) for t in sorted(after)],
        all_unselected_coordinate_bits_unchanged=unchanged,node27_and_all16_shell_nodes_unchanged=True,
        arithmetic='Exact Fraction Q-squared and determinant over proposed binary64 coordinates; decimal signed Q is approximate, not an interval/native measurement.',
        real_face_optima_do_not_establish_simultaneous_star_feasibility=True,embedding_overlap_or_containment_checked=False,
        native_application_or_MSH_write=False,qualification=QUALIFICATION,all_bound_inputs_unchanged=True,wall_seconds=time.monotonic()-started)
    output.mkdir()
    with (output/'diagnostic.json').open('x') as stream:json.dump(report,stream,indent=2,allow_nan=False);stream.write('\n')
    return 0 if passed else 2


if __name__=='__main__':
    if len(sys.argv)!=3:raise SystemExit('Usage: propose.py actual-contract.json exact-contract-sha256')
    raise SystemExit(main(sys.argv[1],sys.argv[2]))
