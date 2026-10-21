"""HELD exact pair intersections for one stored39-cell cavity; no native mesh action."""
from fractions import Fraction
from itertools import combinations
from pathlib import Path
import hashlib,json,math,re,struct,sys,time

ROOT=Path(__file__).resolve().parents[3]
OUTPUT='work/962-engineering/fixed-shell-coupled-embedding-001'
DIAGNOSTIC='work/962-engineering/fixed-shell-coupled-sicn-001/diagnostic.json'
ARRAYS='work/962-engineering/fixed-shell-netgen-apex1435493-001/arrays.json'
SHELL='work/962-engineering/direct-sicn-apex1435493-cavity-study-001/local-shell-input-001.json'
INPUTS={DIAGNOSTIC:'e9184514108a194e9f483c5bfb20ffef9d8334cddd01f60806d97b96f84f532a',
 ARRAYS:'ace411a27a13332129f515ac456ab453cbede0920fe115bdb82057092e665e5f',
 SHELL:'a6f15db60967807b057e357b8f159fa510c4a8cf6e3cb44c4327323c070398c8'}
QUALIFICATION=dict(native_application_authorized=False,head_execution_authorized=False,stitching_authorized=False,
 engineering_accepted=False,physics_qualified=False,manufacturing_authorized=False)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

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

def halfspaces(points,nodes):
    p=[points[t] for t in nodes]
    if dot(subtract(p[1],p[0]),cross(subtract(p[2],p[0]),subtract(p[3],p[0])))<=0:
        raise ValueError('Positive nondegenerate native-ordered tetrahedron required')
    planes=[]
    for i in range(4):
        a,b,c=[p[j] for j in range(4) if j!=i]
        n=cross(subtract(b,a),subtract(c,a));d=dot(n,a);side=dot(n,p[i])-d
        if not side:raise ValueError('Nondegenerate face/opposite corner required')
        if side<0:n=[-x for x in n];d=-d
        planes.append((n,d))  # Inside is n dot x >= d, including the closed face.
    return planes

def plane_vertex(planes):
    (a,da),(b,db),(c,dc)=planes
    bc,ca,ab=cross(b,c),cross(c,a),cross(a,b);det=dot(a,bc)
    if not det:return None  # Dependent active planes do not define an ambient vertex.
    return tuple((da*bc[i]+db*ca[i]+dc*ab[i])/det for i in range(3))

def in_shared_hull(point,shared):
    if not shared:return False
    a=shared[0]
    if len(shared)==1:return tuple(point)==tuple(a)
    e=subtract(shared[1],a);v=subtract(point,a)
    if len(shared)==2:
        axis=next(i for i,x in enumerate(e) if x)
        t=v[axis]/e[axis]
        return 0<=t<=1 and all(v[i]==t*e[i] for i in range(3))
    if len(shared)!=3:raise ValueError('Only proper shared simplices are allowed')
    f=subtract(shared[2],a);n=cross(e,f)
    if dot(n,v)!=0:return False
    j,k=next((j,k) for j,k in combinations(range(3),2) if e[j]*f[k]-e[k]*f[j])
    det=e[j]*f[k]-e[k]*f[j]
    u=(v[j]*f[k]-v[k]*f[j])/det;w=(e[j]*v[k]-e[k]*v[j])/det
    return u>=0 and w>=0 and u+w<=1

def pair_check(points,first,second):
    shared=sorted(set(first)&set(second))
    if len(shared)>3:raise ValueError('Distinct cells may not duplicate a tetrahedron node set')
    planes=halfspaces(points,first)+halfspaces(points,second)
    for t in shared:
        if any(dot(n,points[t])<d for n,d in planes):raise ValueError('Shared tagged point left an incident tetrahedron')
    vertices={};independent=0
    for triple in combinations(range(8),3):
        vertex=plane_vertex([planes[i] for i in triple])
        if vertex is None:continue
        independent+=1
        if all(dot(n,vertex)>=d for n,d in planes):vertices.setdefault(vertex,triple)
    if shared and not vertices:raise ValueError('Nonempty bounded shared intersection must have an ambient active vertex')
    illegal=[]
    for vertex,triple in sorted(vertices.items()):
        if not in_shared_hull(vertex,[points[t] for t in shared]):
            illegal.append(dict(point_mm=[rational(x) for x in vertex],active_generating_plane_ids=list(triple),
                all8_inside_slacks=[rational(dot(n,vertex)-d) for n,d in planes]))
    return dict(shared_node_tags=shared,expected_simplex_dimension=len(shared)-1,
        plane_triples_enumerated=56,independent_plane_triples=independent,intersection_vertices=len(vertices),
        illegal_intersection_vertices=len(illegal),all_illegal_rational_witnesses=illegal,
        intersection_equals_tagged_shared_simplex=not illegal)

def candidate(diagnostic,arrays,shell):
    a=arrays['saved_reopen'];rows=diagnostic['complete_proposed_coordinate_rows'];quality=diagnostic['all39_signed_quality_rows']
    if (diagnostic.get('status')!='exact_feasible_point_solver_converged_native_unapproved'
        or diagnostic.get('all39_exact_quality_gate') is not True or diagnostic.get('procedural_checks_passed') is not True
        or diagnostic.get('qualification')!=QUALIFICATION or diagnostic.get('native_application_or_MSH_write') is not False
        or a['node_tags']!=list(range(1,17))+[27,28,29] or len(a['tetra_tags'])!=39
        or a['tetra_tags']!=sorted(set(a['tetra_tags'])) or len(a['tetra_node_tags'])!=39
        or [row['node_tag'] for row in rows]!=a['node_tags']
        or [row['tetrahedron_tag'] for row in quality]!=a['tetra_tags']):
        raise ValueError('One exact feasible19-node39-cell stored diagnostic required')
    points={}
    for row in rows:
        p=row['coordinates_mm']
        if len(p)!=3 or any(type(x) is not float or not math.isfinite(x) for x in p) or row['binary64_hex']!=[x.hex() for x in p]:
            raise ValueError('Complete finite binary64/hex coordinate association required')
        points[row['node_tag']]=tuple(Fraction.from_float(x) for x in p)
    for row in shell['vertex_rows']:
        tag=row['local_node_tag'];p=rows[a['node_tags'].index(tag)]['coordinates_mm']
        if struct.pack('<3d',*p).hex()!=row['binary64_little_endian_bytes_hex']:raise ValueError('Fixed16 shell bits changed')
    cells=dict(zip(a['tetra_tags'],a['tetra_node_tags']))
    if len({tuple(sorted(v)) for v in cells.values()})!=39:raise ValueError('Duplicate tetrahedron node set')
    for row in quality:
        nodes=cells[row['tetrahedron_tag']]
        if len(nodes)!=4 or len(set(nodes))!=4 or not set(nodes)<=set(points) or row['ordered_node_tags']!=nodes:
            raise ValueError('Full unchanged ordered TET4 connectivity required')
        det,q2=exact_quality([rows[a['node_tags'].index(t)]['coordinates_mm'] for t in nodes])
        if (det<=0 or q2 is None or q2<Fraction(1,100)
            or row['exact_native_ordered_determinant_mm3']!=rational(det) or row['exact_SICN_squared']!=rational(q2)):
            raise ValueError('All39 exact positive-quality prerequisites required before pair checks')
    return points,cells

def main(contract_path,digest):
    started=time.monotonic();path=Path(contract_path)
    if not re.fullmatch('[0-9a-f]{64}',digest) or path.is_symlink() or sha(path)!=digest:
        raise ValueError('Exact external actual contract digest required')
    c=json.loads(path.read_text())
    if (c.get('schema')!='962-fixed-shell-coupled-embedding/v1' or c.get('diagnostic_execution_authorized') is not True
        or c.get('root_and_peer_review_complete') is not True or c.get('native_execution_authorized') is not False
        or c.get('qualification')!=QUALIFICATION or c.get('automatic_retry') is not False
        or c.get('method')!='all741_exact_tetra_pair_intersections' or c.get('output_directory')!=OUTPUT
        or c.get('source_sha256')!=sha(__file__) or sha(Path(sys.executable).resolve())!=c.get('python_sha256')):
        raise ValueError('One separately reviewed exact embedding query only')
    pins=c['input_hashes']
    if any(pins.get(k)!=v for k,v in INPUTS.items()):raise ValueError('Exact single candidate/source pins required')
    for name,value in pins.items():
        p=ROOT/name
        if Path(name).is_absolute() or p.is_symlink() or not p.resolve().is_relative_to(ROOT) or sha(p)!=value:
            raise ValueError('Before input drift: '+name)
    out=ROOT/OUTPUT
    if out.exists() or out.is_symlink() or out.resolve()!=out:raise ValueError('Raw canonical fresh output required')
    points,cells=candidate(json.loads((ROOT/DIAGNOSTIC).read_text()),json.loads((ROOT/ARRAYS).read_text()),json.loads((ROOT/SHELL).read_text()))
    pairs=[]
    for first,second in combinations(sorted(cells),2):
        row=pair_check(points,cells[first],cells[second]);row['tetrahedron_tags']=[first,second];pairs.append(row)
    if len(pairs)!=741:raise ValueError('Complete39 choose2 partition required')
    failures=sum(not row['intersection_equals_tagged_shared_simplex'] for row in pairs)
    report=dict(schema='962-fixed-shell-coupled-exact-embedding-result/v1',
        status='complete_exact_pair_intersection_pass' if not failures else 'illegal_tetrahedron_intersections_detected',
        contract_sha256=digest,source_sha256=c['source_sha256'],input_hashes=pins,
        source_diagnostic_sha256=INPUTS[DIAGNOSTIC],nodes=19,tetrahedra=39,complete_unordered_pairs=741,
        plane_triples_enumerated=741*56,pair_failures=failures,pair_results=pairs,
        exact_pairwise_tagged_complex_embedding=failures==0,all39_exact_positive_quality_prerequisite=True,
        arithmetic='Fraction.from_float stored binary64; exact Cramer solves, inequalities and shared-simplex barycentrics; no tolerance or grid.',
        scope='Pairwise intersections of this fixed local cavity only; no head containment, stitch, native apply or physical admission.',
        native_or_optimizer_calls=0,coordinates_changed=False,qualification=QUALIFICATION,wall_seconds=time.monotonic()-started)
    if any(sha(ROOT/k)!=v for k,v in pins.items()) or sha(path)!=digest:raise ValueError('After input/contract drift')
    report['bound_inputs_unchanged']=True;out.mkdir()
    with (out/'report.json').open('x') as f:json.dump(report,f,indent=2,allow_nan=False);f.write('\n')
    return 0 if not failures else 2

if __name__=='__main__':
    if len(sys.argv)!=3:raise SystemExit('Usage: check_embedding.py actual-contract.json exact-contract-sha256')
    raise SystemExit(main(sys.argv[1],sys.argv[2]))
