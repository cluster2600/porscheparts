"""UNRUN exact outer-ball certificate for one saved shared-apex pair; no mesh/native calls."""
from fractions import Fraction
from math import isqrt
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT/'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-shared-fixed-triples-exact-pair-001'
BITS = 2*53
APEX = 1435493
CELLS = (28946957,31225364)
FIXED = 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-fixed-triples-001/readback-report.json'
FIRST = 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-full-stars-001/readback-report.json'
REFINEMENT = 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-shared-fixed-triples-refinement-assessment-001/report.json'
PINS = {
    FIXED:'d65f86d5d1cabd3e2013a127c1cd9713a232cb1d1bd7817d459f84949d1e1c14',
    FIRST:'5946ffbd9f2f127306673d967b583b11d8906793e2079971bc0430d65ae65f88',
    REFINEMENT:'8c8c47f329c1a92c72c8edc40980519ba9d98bcac80f291438541b23d914819b',
    'work/962-engineering/shared-apex-necessary-ball-math-peer-001/review.json':'36f789c022226fbcff28463a9534ac485487d269b6a1f7e8d1fec062a21f5b59',
    'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-shared-fixed-triples-ball-screen-prep-001/check_balls.py':'4e6d677e11ccaa6b8a9a66b3e59b764e7e4575bb6b467bdc3dd8e5a689d22007',
    'work/962-engineering/direct-sicn-sparse-head-proposer-prep-003/sparse_head.py':'4558a2d6c66284c7436f5b4f6684fa6a6455a60e9fd0e4c76aec7bb3962dc0d0',
    'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-fixed-triples-prep-001/reader.py':'aa62597659177cd40fa7f8e5aca840d9fed46856f09bd93c957200c98cbfbc82',
    'twins/962-cylinder-head-f0/source/gmsh_sicn_reference.json':'28cf35720fa94611a17b219b60b2ead8c1153f6ae346e581d32fd1efe08f112d',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def main():
    if OUT.exists():raise FileExistsError('Fresh exact-pair output required')
    for path,digest in PINS.items():
        if (ROOT/path).is_symlink() or sha(ROOT/path)!=digest:raise ValueError('Frozen input changed: '+path)
    fixed=json.loads((ROOT/FIXED).read_text());first=json.loads((ROOT/FIRST).read_text())
    refinement=json.loads((ROOT/REFINEMENT).read_text())
    if any(r.get('status')!='direct_saved_file_readback_completed' or r.get('bound_inputs_unchanged') is not True for r in [fixed,first]):
        raise ValueError('Completed unchanged saved-row inputs required')
    if fixed['single_optimized_worker_proof']!=first['single_optimized_worker_proof']:
        raise ValueError('Same original native baseline required')
    if any(fixed[k]!=first[k] for k in ('sorted_node_tags_sha256','sorted_coordinates_sha256',
            'sorted_tetra_tags_sha256','tagged_tetra_connectivity_sha256')):
        raise ValueError('All four baseline tagged-array identities must match')
    census=first['complete_seed_star_census']
    nodes={r['node_tag']:r for r in census['unique_incident_nodes']}
    cells={r['tetrahedron_tag']:r for r in census['complete_incident_tetrahedra']}
    selected={r['tetrahedron_tag']:r for r in fixed['fixed_boundary_triple_ceiling_analysis']['rows'] if r['tetrahedron_tag'] in CELLS}
    if set(selected)!=set(CELLS) or APEX not in census['movable_node_tags']:
        raise ValueError('Exact selected two cells and common movable apex required')
    balls=[]
    for tag in CELLS:
        row=selected[tag];cell=cells[tag];tags=row['full_source_tetrahedron_node_tags'];free=row['interior_apex_local_position']
        if (row['interior_apex_node_tag']!=APEX or tags!=cell['node_tags'] or tags[free]!=APEX
                or row['native_array_index']!=cell['native_array_index']
                or float(row['native_SICN']).hex()!=float(cell['initial_native_SICN']).hex() or not 0<row['native_SICN']<.1
                or sum(t<=871731 for t in tags)!=3 or [i for i,t in enumerate(tags) if t<=871731]!=row['fixed_node_local_positions']):
            raise ValueError('Native ordered cell/apex/boundary/source-quality association failed')
        coordinates=[]
        for t in tags:
            node=nodes[t];xyz=node['coordinates_mm']
            if ([float(x).hex() for x in xyz]!=node['binary64_hex'] or node['source_boundary_tag']!=(t<=871731)):
                raise ValueError('Exact source-coordinate bits and boundary-tag classification required')
            coordinates.append([Fraction.from_float(float(x)) for x in xyz])
        ids=row['fixed_node_local_positions']
        if ([tags[i] for i in ids]!=row['fixed_triple_node_tags']
                or [[float(x).hex() for x in coordinates[i]] for i in ids]!=row['fixed_triple_binary64_hex']
                or [[float(x) for x in coordinates[i]] for i in ids]!=row['fixed_triple_coordinates_mm']):
            raise ValueError('Saved fixed-triple coordinate/native-corner association failed')
        balls.append(dict(tetrahedron_tag=tag,source_native_node_tags=tags,
            source_coordinate_binary64_hex=[nodes[t]['binary64_hex'] for t in tags],
            source_fixed_triple_coordinate_bits_sha256=row['fixed_triple_coordinate_bits_sha256'],
            **enclosing_ball(coordinates,free)))
    U,V=[b['squared_radius_upper_mm2'] for b in balls]
    D=sum((x-y)**2 for x,y in zip(balls[0]['rational_ball_centre_mm'],balls[1]['rational_ball_centre_mm']))
    gap=D-U-V;certified=disjoint(D,U,V)
    selection=[r for r in refinement['all55_FLOAT_pair_margins'] if r['interior_apex_node_tag']==APEX and tuple(r['tetrahedron_tags'])==CELLS]
    if len(selection)!=1:raise ValueError('Exact prior FLOAT selection identity required')
    report=dict(schema='962-exact-one-shared-apex-shifted-ball-certificate/v1',
        status='strict_common_apex_obstruction_certified' if certified else 'inconclusive_no_obstruction_certificate',
        source_sha256=sha(Path(__file__)),input_hashes=PINS,apex_tag=APEX,tetrahedron_tags=CELLS,
        sqrt_fractional_bits=BITS,precision_scope='Numerical rational enclosure precision, not a geometry grid',
        balls=balls,exact_centre_distance_squared_mm2=D,exact_gap_D_minus_U_minus_V_mm2=gap,
        exact_gap_squared_minus_4UV_mm4=gap*gap-4*U*V,strict_disjoint_outer_balls=certified,
        FLOAT_selection_informative_only=selection[0],FLOAT_values_used_in_certificate=False,
        premise='Signed native-order determinants positive; same source apex and frozen three-boundary-node coordinates. Exact root/height/cross enclosures contain necessary Q>=.1 domains; rational ball centres and inflated squared radii contain both domains.',
        conclusion_scope='If certified, no common apex can make these two linear cells reach real-arithmetic signed SICN>=.1 with this fixed connectivity and coordinate policy. No native floating-rounding, repair, whole-head or physical qualification is granted.',
        touching_or_nonseparation_inconclusive=True,exterior_surface_face_membership_not_inferred=True,
        native_or_optimizer_calls=0,engineering_accepted=False,physics_qualified=False,manufacturing_authorized=False)
    for path,digest in PINS.items():
        if sha(ROOT/path)!=digest:raise ValueError('Input changed during exact check')
    report['bound_inputs_unchanged']=True
    OUT.mkdir()
    with (OUT/'report.json').open('x') as stream:json.dump(serial(report),stream,indent=2,allow_nan=False);stream.write('\n')


if __name__=='__main__':main()
