"""HELD exact current one-free/three-shell support screen; no mesh or coordinate change."""
from pathlib import Path
from fractions import Fraction
from itertools import combinations
from math import isqrt
import hashlib,json,math,struct,sys,time

ROOT=Path(__file__).resolve().parents[3]
ARRAYS='work/962-engineering/fixed-shell-netgen-apex1435493-001/arrays.json'
WORKER='work/962-engineering/fixed-shell-netgen-apex1435493-001/fixture-report.json'
SHELL='work/962-engineering/direct-sicn-apex1435493-cavity-study-001/local-shell-input-001.json'
INPUTS={ARRAYS:'ace411a27a13332129f515ac456ab453cbede0920fe115bdb82057092e665e5f',
 WORKER:'8529a8f8421dd989ae243b2a06b132b8a2952e9847aa31d34adb74289a16e6c7',
 SHELL:'a6f15db60967807b057e357b8f159fa510c4a8cf6e3cb44c4327323c070398c8'}
TARGETS={198:[29,4,5,6],204:[28,7,9,8]}
FREE=(27,28,29)
FIXED=set(range(1,17))
BITS=2*53
PLANNED_OUTPUT='work/962-engineering/fixed-shell-current-triples-001'
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

def sqrt_interval(x):
    """Exact rational endpoints, fixed106-bit fractional resolution; not a geometry grid."""
    if type(x) is not Fraction or x<0:
        raise ValueError('Nonnegative exact Fraction required')
    scale=1<<BITS
    integer=isqrt((x.numerator<<(2*BITS))//x.denominator)
    lo=Fraction(integer,scale)
    hi=lo if lo*lo==x else Fraction(integer+1,scale)
    if not (0<=lo<=hi and lo*lo<=x<=hi*hi):
        raise ValueError('Square-root enclosure failed')
    return dict(argument=x,lo=lo,hi=hi)

def outer_radius_squared(S, T):
    """Q>=1/10 implies |p-centroid|^2 < U; U uses the positive root sum."""
    if type(S) is not Fraction or type(T) is not Fraction or S <= 0 or T <= 0 or S*S > 841*T:
        raise ValueError('Positive isolated-face-compatible S,T required')
    return Fraction(2, 3) * (899*T/S - S)

def disjoint(D, U, V):
    """Strict separation of two closed outer balls; no square roots or tolerance."""
    if any(type(x) is not Fraction for x in (D,U,V)) or min(D, U, V) < 0:
        raise ValueError('Nonnegative squared distances/radii required')
    gap = D-U-V
    return gap > 0 and gap*gap > 4*U*V

def enclosing_ball(points,free):
    if (len(points)!=4 or any(len(p)!=3 or any(type(x) is not Fraction for x in p) for p in points)
            or type(free) is not int or free not in range(4)):
        raise ValueError('Four exact native-ordered points and free-corner index required')
    native_det=dot(subtract(points[1],points[0]),cross(subtract(points[2],points[0]),subtract(points[3],points[0])))
    if native_det<=0:raise ValueError('Exact native-ordered determinant must be positive')
    fixed=[points[i] for i in range(4) if i!=free]
    centre=[sum(p[k] for p in fixed)/3 for k in range(3)]
    e,f=subtract(fixed[1],fixed[0]),subtract(fixed[2],fixed[0])
    raw=cross(e,f);C=dot(raw,raw);side=dot(raw,subtract(points[free],centre))
    if C<=0 or side!=(-1)**(3-free)*native_det:
        raise ValueError('Fixed-face native permutation/parity association failed')
    sign=1 if side>0 else -1
    oriented=[sign*x for x in raw]
    S=Fraction(4,3)*(dot(e,e)+dot(f,f)-dot(e,f));T=Fraction(4,3)*C
    A=899*T-S*S;delta=A*A-4*S*S*T;R2=841*T/S-S
    if S<=0 or T<=0 or S*S>841*T or A<=0 or delta<0 or R2<0:
        raise ValueError('Isolated positive-target bound premises failed')
    discriminant=sqrt_interval(delta)
    wminus=max(Fraction(0),(A-discriminant['hi'])/(2*S))
    wplus=(A+discriminant['hi'])/(2*S)
    lower_height=sqrt_interval(Fraction(2,3)*wminus)
    upper_height=sqrt_interval(Fraction(2,3)*wplus)
    hlow,hhi=lower_height['lo'],upper_height['hi']
    cross_norm=sqrt_interval(C)
    if cross_norm['hi']<=0:raise ValueError('Positive cross-norm enclosure required')
    k=(hlow+hhi)/(2*cross_norm['hi'])
    exact_centre=[x+k*n for x,n in zip(centre,oriented)]
    Hlo,Hhi=k*cross_norm['lo'],k*cross_norm['hi']
    m=max(abs(hlow-Hhi),abs(hhi-Hlo))
    U=Fraction(2,3)*R2+m*m
    return dict(native_ordered_determinant_mm3=native_det,raw_cross_dot_original_apex_mm3=side,
        native_free_corner=free,raw_cross_to_positive_target_side_sign=sign,exact_oriented_raw_cross_mm2=oriented,
        exact_fixed_face_centroid_mm=centre,S_mm2=S,T_mm4=T,cross_squared_mm4=C,
        A_mm4=A,discriminant_mm8=delta,sqrt_discriminant=discriminant,
        wminus_lower_mm2=wminus,wplus_upper_mm2=wplus,
        lower_height_sqrt=lower_height,upper_height_sqrt=upper_height,
        hlow_mm=hlow,hhi_mm=hhi,tangent_squared_ideal_upper_mm2=R2,
        cross_norm_sqrt=cross_norm,rational_centre_cross_coefficient=k,
        rational_ball_centre_mm=exact_centre,true_centre_height_lower_mm=Hlo,
        true_centre_height_upper_mm=Hhi,axial_halfextent_upper_mm=m,squared_radius_upper_mm2=U)

def serial(value):
    if type(value) is Fraction:
        return dict(numerator=str(value.numerator),denominator=str(value.denominator))
    if isinstance(value,dict):return {k:serial(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [serial(v) for v in value]
    return value

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


def fixed_support(cells):
    """Complete tag-only selection; native quality never filters support."""
    grouped={tag:[] for tag in FREE};excluded=[]
    for tag,row in sorted(cells.items()):
        if (type(tag) is not int or tag<=0 or len(row)!=4 or len(set(row))!=4
            or any(type(t) is not int or t not in FIXED|set(FREE) for t in row)):
            raise ValueError('Unique ordered source cells with declared local tags required')
        free=[t for t in row if t in FREE]
        if len(free)==1:
            grouped[free[0]].append(tag)
        else:
            excluded.append(dict(tetrahedron_tag=tag,ordered_node_tags=row,
                free_node_tags=free,fixed_shell_node_tags=[t for t in row if t in FIXED],
                reason='multiple_free_nodes_not_fixed_triple' if free else 'no_free_apex'))
    if sum(len(v) for v in grouped.values())+len(excluded)!=len(cells):
        raise ValueError('Complete disjoint source-cell selection required')
    return grouped,excluded


def compare_balls(first,second):
    c,U=first;d,V=second
    D=sum((x-y)**2 for x,y in zip(c,d));gap=D-U-V
    certified=disjoint(D,U,V)
    return dict(exact_centre_distance_squared_mm2=D,exact_gap_D_minus_U_minus_V_mm2=gap,
        exact_gap_squared_minus_4UV_mm4=gap*gap-4*U*V,
        strictly_disjoint_necessary_outer_balls=certified,
        decision='strict_disjointness_certificate' if certified else 'inconclusive')


def screen(points,cells,a):
    grouped,excluded=fixed_support(cells)
    qualities=dict(zip(a['tetra_tags'],a['native_qualities']['SICN']))
    support=[];pairs=[];by_cell={}
    for apex,tags in grouped.items():
        for tag in tags:
            row=cells[tag];free=row.index(apex)
            coordinates=[[Fraction.from_float(float(v)) for v in points[t]] for t in row]
            shifted=enclosing_ball(coordinates,free)
            fixed=[t for t in row if t!=apex]
            proof=certificate([points[t] for t in fixed])
            centre=shifted['exact_fixed_face_centroid_mm']
            S,T=shifted['S_mm2'],shifted['T_mm4']
            U=outer_radius_squared(S,T)
            if (Fraction(int(proof['sum_squared_edge_lengths_mm2']['numerator']),int(proof['sum_squared_edge_lengths_mm2']['denominator']))*Fraction(2,3)!=S
                or Fraction(int(proof['cross_squared_mm4']['numerator']),int(proof['cross_squared_mm4']['denominator']))*Fraction(4,3)!=T):
                raise ValueError('Exact face certificate and necessary-ball invariants differ')
            record=dict(tetrahedron_tag=tag,source_native_ordered_node_tags=row,
                source_coordinates_mm=[points[t] for t in row],
                source_coordinate_binary64_hex=[[float(v).hex() for v in points[t]] for t in row],
                free_apex_tag=apex,native_free_corner=free,
                fixed_shell_node_tags=fixed,source_native_SICN=qualities[tag],
                source_native_good_at_point1=qualities[tag]>=.1,
                exact_fixed_face_certificate=proof,
                centroid_necessary_outer_ball=dict(exact_centre_mm=centre,squared_radius_upper_mm2=U,
                    exact_S_mm2=S,exact_T_mm4=T),
                shifted_necessary_outer_ball=shifted)
            support.append(record);by_cell[tag]=record
        for first,second in combinations(tags,2):
            p,q=by_cell[first],by_cell[second]
            b,c=p['centroid_necessary_outer_ball'],q['centroid_necessary_outer_ball']
            centroid=compare_balls((b['exact_centre_mm'],b['squared_radius_upper_mm2']),
                                   (c['exact_centre_mm'],c['squared_radius_upper_mm2']))
            b,c=p['shifted_necessary_outer_ball'],q['shifted_necessary_outer_ball']
            shifted=compare_balls((b['rational_ball_centre_mm'],b['squared_radius_upper_mm2']),
                                  (c['rational_ball_centre_mm'],c['squared_radius_upper_mm2']))
            certified=centroid['strictly_disjoint_necessary_outer_balls'] or shifted['strictly_disjoint_necessary_outer_balls']
            pairs.append(dict(free_apex_tag=apex,tetrahedron_tags=[first,second],
                centroid_ball_comparison=centroid,shifted_ball_comparison=shifted,
                pair_obstruction_certified=certified,
                decision='strict_disjointness_certificate' if certified else 'inconclusive'))
    if (len(support)!=sum(len(v) for v in grouped.values())
        or len(pairs)!=sum(len(v)*(len(v)-1)//2 for v in grouped.values())):
        raise ValueError('Every selected support row and within-apex pair required')
    return grouped,excluded,support,pairs


def main(contract_path,digest):
    started=time.monotonic();contract_path=Path(contract_path)
    if len(digest)!=64 or sha(contract_path)!=digest:raise ValueError('Exact external actual contract digest required')
    c=json.loads(contract_path.read_text());require_input_bindings(c['input_hashes'])
    if (c.get('schema')!='962-fixed-shell-current-triples-held/v1'
        or c.get('diagnostic_execution_authorized') is not True or c.get('root_and_peer_review_complete') is not True
        or c.get('qualification')!=QUALIFICATION or c.get('free_tags')!=list(FREE)
        or c.get('fixed_tags')!=sorted(FIXED) or c.get('automatic_retry') is not False
        or c.get('native_execution_authorized') is not False or c.get('sicn_gate')!=.1
        or c.get('method')!='all_current_one_free_three_shell_necessary_ball_pairs'):
        raise ValueError('Reviewed current fixed-shell necessary screen only')
    if sha(__file__)!=c['source_sha256'] or sha(Path(sys.executable).resolve())!=c['python_sha256']:
        raise ValueError('Exact source/interpreter binding required')
    for name,value in c['input_hashes'].items():
        if Path(name).is_absolute() or (ROOT/name).is_symlink() or not (ROOT/name).resolve().is_relative_to(ROOT) or sha(ROOT/name)!=value:
            raise ValueError('Before input drift: '+name)
    if c.get('output_directory')!=PLANNED_OUTPUT:raise ValueError('Exact separately authorized output required')
    output=ROOT/PLANNED_OUTPUT
    if output.exists() or output.is_symlink() or output.resolve()!=output:
        raise ValueError('Raw canonical fresh output required before resolution')
    worker=json.loads((ROOT/WORKER).read_text());arrays=json.loads((ROOT/ARRAYS).read_text());shell=json.loads((ROOT/SHELL).read_text())
    points,cells,a=before_state(worker,arrays,shell)
    grouped,excluded,support,pairs=screen(points,cells,a)
    count=sum(p['pair_obstruction_certified'] for p in pairs)
    report=dict(schema='962-current-cavity-fixed-triple-necessary-ball-screen/v1',
        status='fixed_connectivity_pair_obstruction_certified' if count else 'complete_pair_screen_inconclusive',
        contract_sha256=digest,source_sha256=c['source_sha256'],input_hashes=c['input_hashes'],
        source_state='Original immutable Netgen19node/39cell saved_reopen; rejected optimum coordinates are not an input.',
        full_source_nodes=19,full_source_cells=39,fixed_shell_tags=sorted(FIXED),free_tags=list(FREE),
        complete_support_by_apex=[dict(free_apex_tag=t,tetrahedron_tags=tags,selected_cells=len(tags),
            initially_native_good_cells=sum(qualities>=.1 for tag,qualities in zip(a['tetra_tags'],a['native_qualities']['SICN']) if tag in tags))
            for t,tags in grouped.items()],
        selected_cells=len(support),excluded_cells=len(excluded),complete_pair_count=len(pairs),
        certified_disjoint_pair_count=count,support_rows=support,pair_results=pairs,excluded_source_rows=excluded,
        selection='Every cell with exactly one tag27/28/29 and three fixed shell tags1..16, including initially good cells. No quality filter.',
        sqrt_fractional_bits=BITS,precision_scope='Inherited rational root enclosure precision; not a geometry grid or new tolerance.',
        centroid_bound='Q>=.1 implies |p-centroid|^2<U=(2/3)*(899*T/S-S); closed enclosing outer balls use the same inherited exact predicate.',
        shifted_bound='Inherited exact native-corner positive-side height/tangent enclosure with rational centres and inflated squared radii.',
        conclusions='Disjoint necessary outer balls prove only a same-apex pair obstruction under this fixed-shell coordinate/connectivity policy. Every nonseparated/touching comparison is inconclusive, not feasible.',
        cells_with_two_or_three_free_nodes_not_certified=True,all_cell_constraints_jointly_solved=False,
        original_global_boundary_classification_not_inferred=True,coordinates_changed=False,
        native_or_optimizer_calls=0,native_application_or_MSH_write=False,qualification=QUALIFICATION,
        wall_seconds=time.monotonic()-started)
    if any(sha(ROOT/name)!=value for name,value in c['input_hashes'].items()) or sha(contract_path)!=digest:
        raise ValueError('After input/contract drift')
    report['bound_inputs_unchanged']=True
    output.mkdir()
    with (output/'report.json').open('x') as stream:json.dump(serial(report),stream,indent=2,allow_nan=False);stream.write('\n')
    return 0


if __name__=='__main__':
    if len(sys.argv)!=3:raise SystemExit('Usage: screen.py actual-contract.json exact-contract-sha256')
    raise SystemExit(main(sys.argv[1],sys.argv[2]))
