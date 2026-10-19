"""Three existing heights only; exact encoded-point coverage, no AM or mesh write."""
import ast
from fractions import Fraction as Q
import hashlib,io,json,math,resource,signal,struct,time,zipfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def extract(path,names,namespace):
    tree=ast.parse(Path(path).read_text())
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name in names]
    if {n.name for n in nodes}!=set(names):raise ValueError('Exact frozen functions absent')
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),namespace)

def cell_proof(segment):
    rounded=[tuple(float(q)for q in point)for point in segment]
    if rounded[0]!=rounded[1]or segment[0]==segment[1]:raise ValueError('Only a nonzero rational segment collapsed to one finite point is considered')
    point=rounded[0];cells=[]
    for axis,value in enumerate(point):
        previous,following=math.nextafter(value,-math.inf),math.nextafter(value,math.inf)
        if not all(math.isfinite(x)for x in [previous,value,following]):raise ValueError('Nonfinite rounding-cell neighbours')
        lo,hi=(Q(previous)+Q(value))/2,(Q(value)+Q(following))/2
        even=struct.unpack('>Q',struct.pack('>d',value))[0]&1==0
        def inside(q):return (lo<q<hi)or(even and q in (lo,hi))
        if not all(inside(p[axis])for p in segment):raise ValueError('Endpoint is outside the exact nearest-even cell')
        cells.append(dict(axis=axis,lower=str(lo),upper=str(hi),both_ties_included=even))
    return dict(point=list(point),point_hex=[v.hex()for v in point],cells=cells,
        entire_segment_in_convex_rounding_cell=True,
        scope='Pointwise rounding of this collapsed segment only. Other encoded segments mean straight joins of rounded endpoints, not pointwise images.')

def covered(point,candidates,owner,contains):
    point=tuple(Q(float(v))for v in point)
    result=[]
    for face,group,raw in candidates:
        segment=tuple(tuple(Q(float(v))for v in p)for p in raw)
        if group==owner and segment[0]!=segment[1]and contains(segment,point):result.append(face)
    return result

def fixtures(contains):
    p=(Q(1),Q(2));delta=Q(1,2**60);tiny=[(p[0]+delta,p[1]),(p[0]+2*delta,p[1]+delta)]
    proof=cell_proof(tiny);line=((Q(0),Q(2)),(Q(2),Q(2)));rows=[]
    for name,candidates,expected in [
        ('same_owner_interior',[(1,'a',line)],True),
        ('same_owner_endpoint',[(1,'a',(p,(Q(2),Q(2))))],True),
        ('different_owner_refused',[(1,'b',line)],False),
        ('zero_vector_refused',[(1,'a',(p,p))],False),
        ('point_not_covered_refused',[(1,'a',((Q(0),Q(3)),(Q(2),Q(3))))],False),
        ('nonzero_exact_offset_refused',[(1,'a',((Q(0),Q(2)+Q(1,2**51)),(Q(2),Q(2)+Q(1,2**51))))],False)]:
        observed=bool(covered(proof['point'],candidates,'a',contains))
        if observed!=expected:raise ValueError('Fixture differs: '+name)
        rows.append(dict(name=name,expected=expected,observed=observed))
    even=(Q(math.nextafter(1.,-math.inf))+Q(1))/2
    cell_proof([(even,Q(2)),(Q(1),Q(2))]);rows.append(dict(name='even_tie_and_asymmetric_binade_cell',passed=True))
    cell_proof([(Q(-1,2**1075),Q(0)),(Q(1,2**1075),Q(0))]);rows.append(dict(name='geometric_signed_zero_cell',passed=True))
    try:cell_proof([(Q(1),Q(2)),(Q(2),Q(2))])
    except ValueError:rows.append(dict(name='noncollapsed_segment_refused',passed=True))
    else:raise ValueError('A noncollapsed segment was accepted')
    return rows

def main():
    start=time.monotonic();signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('60s budget')));signal.alarm(60)
    resource.setrlimit(resource.RLIMIT_CPU,(50,51))
    base=ROOT/'work/carrier-process-20261017/source000-remaining-skin13-diagnostic-001'
    plan=json.loads((base/'plan.json').read_text());original=json.loads((base/'output-001/assessment.json').read_text())
    roles=['reader','surface','metadata','terminal_assessment','combined','clip']
    paths=[ROOT/plan[k]for k in roles]+[ROOT/'parts/993-eng-carrier-0001/source/process-scanpath-audit-20261016/exact_zero_face_coverage.py',base/'output-001/assessment.json',base/'plan.json',Path(__file__)]
    before={str(p):sha(p)for p in paths}
    for role in roles:
        if sha(ROOT/plan[role])!=plan['files_sha256'][plan[role]]:raise ValueError('Frozen input/source differs')
    zero=paths[6]
    if sha(zero)!='910151f42cd028e780619bb3e863d6fec2672331e753ffd9b26b6220f8f5fec3':raise ValueError('Frozen coverage helper differs')
    if original['inputs_sha256_before']!=original['inputs_sha256_after']or original['retained_operations']!=203:raise ValueError('Original diagnostic is not the frozen terminal state')
    ns=dict(ast=ast,io=io,zipfile=zipfile,struct=struct,hashlib=hashlib,Path=Path,Q=Q)
    extract(ROOT/plan['reader'],['retained_arrays'],ns)
    extract(ROOT/plan['clip'],['canonical','clip_triangle','orient','contains_point'],ns)
    extract(zero,['union_intervals'],ns)
    arrays=ns['retained_arrays'](ROOT/plan['surface']);vertices,faces,orders,types=[arrays[n][0]for n in ['vertices','faces','order','type']]
    original_faces=[row[:]for row in faces]
    terminal=json.loads((ROOT/plan['terminal_assessment']).read_text())
    for operation in terminal['operations']:
        if [faces[i]for i in operation['face_ids']]!=operation['expected_before']:raise ValueError('Current operation rows differ')
        for step in operation['steps']:
            for i,row in zip(step['face_pair'],step['new_triangles']):faces[i]=row[:]
    # rows_sha is a pure serializer; load it without executing the inventory.
    extract(ROOT/plan['combined'],['rows_sha'],ns)
    if ns['rows_sha'](faces)!=terminal['hypothetical_final_faces_array_sha256']:raise ValueError('The current203-operation face array differs')
    metadata=json.loads((ROOT/plan['metadata']).read_text())
    group=next(g for g in metadata['peripheral_skin']['support_surface_face_groups']if g['id']=='skin-13-0');lo,hi=group['face_range']
    cache={}
    def vertex(i):
        if i not in cache:cache[i]=tuple(Q(v)for v in vertices[i])
        return cache[i]
    results=[]
    for state_name,current in [('original_c351',original_faces),('hypothetical203_not_admitted',faces)]:
      for layer in [0,118,469]:
        height=Q((layer+.5)*.06);cuts=[];targets=[]
        for face in range(lo,hi):
            if orders[face]!=group['order']or types[face]!=group['type']:raise ValueError('Owner attributes differ')
            cut=ns['clip_triangle']([vertex(i)for i in current[face]],height)
            if cut is None:continue
            encoded=tuple(tuple(Q(float(v))for v in point)for point in cut)
            if encoded[0]!=encoded[1]:cuts.append((face,group['id'],encoded))
            elif face in (170702,170703):targets.append((face,cut))
        rows=[]
        for face,cut in targets:
            proof=cell_proof(cut);witnesses=covered(proof['point'],cuts,group['id'],ns['contains_point'])
            union=ns['union_intervals']([(Q(0),Q(1))for _ in witnesses])
            rows.append(dict(face=face,rational_cut=list(map(lambda p:list(map(str,p)),cut)),rounding_cell=proof,
                encoded_point_exactly_covered_by_same_owner_nonzero_vector=bool(witnesses),
                covering_face_ids=witnesses,encoded_target_parameter_union=[[str(a),str(b)]for a,b in union],
                entire_encoded_target_covered=union==[[Q(0),Q(1)]]))
        if not rows:raise ValueError('The selected height has no actual collapsed target')
        results.append(dict(state=state_name,layer=layer,z_mm=float(height),same_owner_nonzero_encoded_vectors=len(cuts),targets=rows))
    after={str(p):sha(p)for p in paths}
    if before!=after:raise ValueError('Original sources or inputs changed')
    tests=fixtures(ns['contains_point']);output=HERE/'assessment.json'
    if output.exists():raise FileExistsError('Preserve unique diagnostic')
    report=dict(status='three_existing_heights_encoded_point_coverage_diagnostic_only',owner=group['id'],
        original_diagnostic_sha256=sha(base/'output-001/assessment.json'),current203_operation_faces_sha256=terminal['hypothetical_final_faces_array_sha256'],
        results=results,all_sampled_collapsed_points_covered=all(row['entire_encoded_target_covered']for r in results for row in r['targets']),
        fixtures=tests,source_and_input_sha256_before=before,source_and_input_sha256_after=after,inputs_unchanged=True,
        AM_imported=False,workers=0,geometry_modified=False,hooks_modified=False,global_admission=False,
        no_all1034_claim=True,elapsed_seconds=time.monotonic()-start)
    output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');signal.alarm(0)
    print(json.dumps(dict(status=report['status'],sampled_state_heights=len(results),all_sampled_points_covered=report['all_sampled_collapsed_points_covered'],fixtures=len(tests),seconds=report['elapsed_seconds'])))

if __name__=='__main__':main()
