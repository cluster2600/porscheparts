"""Prepared original000 ledger-event coverage diagnostic; no AM or export."""
import argparse,ast,bisect,fractions,hashlib,importlib.util,io,json,math,resource,signal,struct,sys,time,zipfile
from collections import Counter
from fractions import Fraction as Q
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
MATH_SHA='2c5650aec59d0407b9d45e2c81cc3392d08a884d8c0ea75031a558acbf968044'
SURFACE_SHA='c351989c2191382d51aec2d8941d08ec1ccaaba30197bdc6121dd92e351bba6b'
FIELDS={'id','kind','face_range','order','type'}
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,value):
    with path.open('x')as stream:json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')
def load_math(plan):
    path=ROOT/plan['tested_math']
    if sha(path)!=MATH_SHA:raise ValueError('The owner13 proof helpers changed')
    spec=importlib.util.spec_from_file_location('_frozen_owner13_math',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def triangle_index(source,owner,triangles):
    """Source-IEEE vertex bounds also bound rounded convex combinations."""
    rows=[]
    for face,triangle in triangles:
        if (len(triangle)!=3 or any(len(p)!=3 for p in triangle)or
                any(type(v)is not Q or not math.isfinite(float(v))or Q(float(v))!=v for p in triangle for v in p)):
            raise ValueError('Finite source IEEE triangle coordinates as Fractions are required')
        low=tuple(min(p[k]for p in triangle)for k in range(3))
        high=tuple(max(p[k]for p in triangle)for k in range(3))
        rows.append((low[0],face,triangle,low,high))
    rows.sort(key=lambda row:(row[0],row[1]))
    return dict(source=source,owner=owner,lows=[row[0]for row in rows],rows=rows)


def layer_cache(source,layer,height):return dict(source=source,layer=layer,height=height,cuts={})


def covering_witness(point,height,index,section_identity,cache,clip,contains,math_module,statistics):
    source,owner,layer=section_identity
    if (index['source']!=source or index['owner']!=owner or cache['source']!=source
            or cache['layer']!=layer or cache['height']!=height):
        raise ValueError('The source/owner/layer identity differs')
    point=tuple(Q(float(v))for v in point)
    if len(point)!=2:raise ValueError('A2D encoded point is required')
    candidates=[];limit=bisect.bisect_right(index['lows'],point[0])
    for _,face,triangle,low,high in index['rows'][:limit]:
        if not(low[2]<=height<=high[2]and all(low[k]<=point[k]<=high[k]for k in range(2))):continue
        statistics['bbox_candidates']+=1
        if face not in cache['cuts']:
            cache['cuts'][face]=clip(triangle,height);statistics['candidate_clip_calls']+=1
        cut=cache['cuts'][face]
        if cut is None:continue
        encoded=tuple(tuple(Q(float(v))for v in p)for p in cut)
        if encoded[0]!=encoded[1]:candidates.append((face,section_identity,encoded))
    witness=math_module.point_witness(point,math_module.vector_index(candidates),section_identity,contains)
    if witness is not None:
        witness['owner']=owner
        witness['section_identity']=dict(source_npz_sha256=source,owner_id=owner,layer=layer,z_exact=str(height))
        witness['original_rational_cut']=[[str(v)for v in p]for p in cache['cuts'][witness['face_id']]]
    return witness


def exact_record(value):
    if set(value)!={'numerator','denominator','nearest_float'}or type(value['nearest_float'])is not float:
        raise ValueError('The pinned rational ledger record has another shape')
    result=Q(int(value['numerator']),int(value['denominator']))
    if float(result).hex()!=value['nearest_float'].hex():raise ValueError('The ledger nearest float differs')
    return result


def verify(plan_path,expected,ready=False):
    if sha(plan_path)!=expected:raise ValueError('The prepared ledger diagnostic plan changed')
    plan=json.loads(Path(plan_path).read_text())
    if (plan['schema']!='original000-ledger-covered-encoded-points-diagnostic-1'or plan['owners']!=337
            or plan['faces']!=171694 or plan['declared_layers']!=1034 or plan['expected_collapsed_events']!=17384
            or plan['workers']!=0 or plan['source_npz_sha256']!=SURFACE_SHA):
        raise ValueError('Only original000/337owners/1034planes/17384events is prepared')
    if ready and(not plan['launch_ready']or plan['resources']is None):raise ValueError('The general diagnostic has no approved resource budget yet')
    if plan['resources']is not None:
        r=plan['resources']
        if r!=dict(parent_wall_seconds=600,cleanup_seconds=[10,10],inner_alarm_seconds=570,inner_CPU_seconds=550,threads=1,nice=10):
            raise ValueError('The prepared resource budget differs')
    for name,h in plan['files_sha256'].items():
        if sha(ROOT/name)!=h:raise ValueError('Frozen ledger diagnostic source/input changed: '+name)
    if (Path(sys.executable).resolve()!=Path(plan['execution_python'])or sha(sys.executable)!=plan['execution_python_sha256']
            or sys.version!=plan['execution_python_version']or sha(fractions.__file__)!=plan['stdlib_fraction_source_sha256']):
        raise ValueError('The prepared stdlib Python/Fraction runtime differs')
    checkpoint=json.loads((ROOT/plan['checkpoint']).read_text())
    if (checkpoint['runtime_before']!=checkpoint['runtime_after']or not checkpoint['runtime_unchanged']
            or hashlib.sha256(json.dumps(checkpoint['runtime_before'],sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()!=plan['source_C22_sha256']
            or checkpoint['files_sha256']['support.npz']!=SURFACE_SHA):raise ValueError('The original geometry/runtime binding differs')
    owners=json.loads((ROOT/plan['owner_index']).read_text());traces=json.loads((ROOT/plan['owner_traces']).read_text())
    owner_receipt=json.loads((ROOT/plan['owner_receipt']).read_text())
    if (owners['schema']!='exact-original-region-owner-index-1'or owners['source_index']!=0 or owners['faces']!=171694
            or owners['surface_sha256']!=SURFACE_SHA or owners['checkpoint_sha256']!=sha(ROOT/plan['checkpoint'])
            or owners['metadata_sha256']!=checkpoint['files_sha256']['geometry-assessment.json']
            or owner_receipt['status']!='streamed_exact_owner_index_completed_no_AM'or not owner_receipt['files_unchanged']
            or owner_receipt['output_sha256']!=sha(ROOT/plan['owner_index'])):raise ValueError('The original owner index is not bound')
    if (traces['schema']!='exact-original-region-owner-contact-traces-1'or traces['source_index']!=0 or traces['faces']!=171694
            or traces['surface_sha256']!=SURFACE_SHA or traces['checkpoint_sha256']!=owners['checkpoint_sha256']
            or traces['metadata_sha256']!=owners['metadata_sha256']or not traces['original_scan_attributes_unchanged']
            or traces['original_owner_index_sha256']!=sha(ROOT/plan['owner_index'])
            or [{k:g[k]for k in FIELDS}for g in traces['groups']]!=owners['groups']):raise ValueError('The912c/d0e owner projections differ')
    math_module=load_math(plan);base=math_module.load_base(plan);ns={'FIELDS':FIELDS}
    base.extract(ROOT/plan['owner_extractor'],['validate_groups'],ns);ns['validate_groups'](owners['groups'])
    census=json.loads((ROOT/plan['census_receipt']).read_text());worker=json.loads((ROOT/plan['census_worker_receipt']).read_text())
    if (census['status']!='diagnostic_calendar_completed_no_global_admission'or not census['declared_layers']==census['completed_layers']==1034
            or census['collapsed_cuts']!=17384 or census['source_sha256']!=sha(ROOT/plan['census_collector'])
            or not all(census[k]is True for k in ['runtime_unchanged','files_unchanged','worker_group_closed'])
            or census['plan_sha256']!=sha(ROOT/plan['census_plan'])or any(census[k]!=v for k,v in worker.items())
            or (ROOT/plan['census_runtime_before']).read_bytes()!=(ROOT/plan['census_runtime_after']).read_bytes()):
        raise ValueError('The original census is not terminal/complete/unchanged')
    for name,h in census['files_sha256'].items():
        if sha((ROOT/plan['census_receipt']).parent/name)!=h:raise ValueError('A terminal census payload differs')
    old=json.loads((ROOT/plan['census_plan']).read_text())
    if old['surface']!=plan['surface']or old['files_sha256'][plan['surface']]!=SURFACE_SHA or old['heights_mm']!=[(i+.5)*.06 for i in range(1034)]:
        raise ValueError('The original census geometry/calendar differs')
    summary=json.loads((ROOT/plan['census_summary']).read_text())
    if summary['layers']!=1034 or summary['collapsed_events']!=17384 or not summary['inputs_unchanged']or not summary['exact_calendar_unchanged']:
        raise ValueError('The original17384-event summary differs')
    output=ROOT/plan['output_directory']
    if output.exists()or any(q.is_symlink()for q in [output,*output.parents]):raise ValueError('Diagnostic output must be fresh without symlinks')
    return plan,owners,census,summary


def execute(plan_path,expected):
    began=time.monotonic();cpu_before=time.process_time();plan,owners,census,summary=verify(plan_path,expected,ready=True)
    math_module=load_math(plan);base=math_module.load_base(plan);r=plan['resources']
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Inner ledger diagnostic deadline')));signal.alarm(r['inner_alarm_seconds'])
    resource.setrlimit(resource.RLIMIT_CPU,(r['inner_CPU_seconds'],r['inner_CPU_seconds']+1))
    output=ROOT/plan['output_directory'];output.mkdir()
    report=dict(status='starting_no_admission',plan_sha256=expected,inputs_before=plan['files_sha256'],workers=0,AM_imported=False,
        source_npz_sha256=SURFACE_SHA,source_C22_sha256=plan['source_C22_sha256'],owners=337,declared_layers=1034,completed_layers=0,
        collapsed_events=0,expected_collapsed_events=17384,all_ledger_collapsed_points_covered=False,
        all_noncollapsed_Q_cuts_recomputed=False,global_admission=False,graph_recomputed=False,contacts_recomputed=False,mesh_or_vectors_written=False)
    statistics=dict(event_clip_calls=0,candidate_clip_calls=0,bbox_candidates=0,indexed_owners=0)
    try:
        ns=dict(ast=ast,io=io,zipfile=zipfile,struct=struct,hashlib=hashlib,Path=Path,Q=Q)
        base.extract(ROOT/plan['reader'],['retained_arrays'],ns)
        base.extract(ROOT/plan['clip'],['canonical','clip_triangle','orient','contains_point'],ns)
        arrays=ns['retained_arrays'](ROOT/plan['surface']);vertices,faces,order,types=[arrays[n][0]for n in ['vertices','faces','order','type']]
        if len(faces)!=171694 or len(order)!=len(faces)or len(types)!=len(faces):raise ValueError('The original surface sizes differ')
        groups={g['id']:g for g in owners['groups']};indices={};points={};counts=Counter();owner_counts=Counter();totals=Counter()
        def triangle(face):
            result=[]
            for i in faces[face]:
                if type(i)is not int or not 0<=i<len(vertices):raise ValueError('An original face index is invalid')
                if i not in points:points[i]=tuple(Q(v)for v in vertices[i])
                result.append(points[i])
            return tuple(result)
        for group in owners['groups']:
            for face in range(*group['face_range']):
                if order[face]!=group['order']or types[face]!=group['type']:raise ValueError('An original owner scan attribute differs')
        with (ROOT/plan['ledger']).open()as ledger,(output/'layers.jsonl').open('x')as progress:
            for layer,line in enumerate(ledger):
                row=json.loads(line);height=Q((layer+.5)*.06)
                if (layer>=1034 or row['layer']!=layer or row['faces']!=171694 or Q(row['z_mm'])!=height
                        or exact_record(row['plane_z_fraction'])!=height
                        or sum(row[k]for k in ['bound_culled_faces','no_segment','noncollapsed_cuts'])+len(row['collapsed_cuts'])!=171694):
                    raise ValueError('The sealed ledger chronology/calendar/face accounting differs')
                cache=layer_cache(SURFACE_SHA,layer,height);proofs=[];seen=set();refused=False
                for event in row['collapsed_cuts']:
                    face=event['face_id'];owner=event['owner'];group=groups.get(owner['id'])
                    if (group!=owner or not group['face_range'][0]<=face<group['face_range'][1]or face in seen or faces[face]!=event['vertex_ids']):
                        raise ValueError('A ledger event has another original face/owner')
                    seen.add(face);cut=ns['clip_triangle'](triangle(face),height);statistics['event_clip_calls']+=1
                    original=tuple(tuple(exact_record(v)for v in p)for p in event['exact_cut_xy_mm'])
                    if cut!=original:raise ValueError('A ledger collapsed cut differs from its exact original triangle')
                    encoded=[[float(v).hex()for v in p]for p in cut]
                    if encoded!=[[v.hex()for v in p]for p in event['encoded_cut_xy_mm']]:raise ValueError('Ledger endpoint encoding differs')
                    cell=base.cell_proof(cut);cache['cuts'][face]=cut
                    if owner['id']not in indices:
                        indices[owner['id']]=triangle_index(SURFACE_SHA,owner['id'],[(i,triangle(i))for i in range(*group['face_range'])])
                        statistics['indexed_owners']+=1
                    identity=(SURFACE_SHA,owner['id'],layer)
                    witness=covering_witness(cell['point'],height,indices[owner['id']],identity,cache,ns['clip_triangle'],ns['contains_point'],math_module,statistics)
                    proofs.append(dict(source_npz_sha256=SURFACE_SHA,owner=owner['id'],owner_face_range=group['face_range'],layer=layer,face_id=face,
                        original_rational_cut=[[str(v)for v in p]for p in cut],rounding_cell=cell,
                        nonzero_same_owner_witness=witness,entire_encoded_point_covered=witness is not None))
                    counts[face]+=1;owner_counts[owner['id']]+=1
                    if witness is None:refused=True
                result=dict(layer=layer,z_exact=str(height),sealed_ledger_events=len(proofs),proofs=proofs,passed=not refused,
                    all_raw_Q_unchanged=True,all_noncollapsed_Q_cuts_recomputed=False,
                    diagnostic_scope='Every sealed collapsed event is re-clipped; only source-bbox candidates are clipped for witnesses. No Q-cut set is modified or exported.')
                progress.write(json.dumps(result,separators=(',',':'),allow_nan=False)+'\n');progress.flush()
                report['completed_layers']=layer+1;report['collapsed_events']+=len(proofs)
                for key in ['bound_culled_faces','no_segment','noncollapsed_cuts']:totals[key]+=row[key]
                if refused:raise ValueError('An original collapsed encoded point is uncovered at layer '+str(layer))
        expected_faces={r['face_id']:r['collapsed_events']for r in summary['faces']}
        expected_owners={r['owner']['id']:r['collapsed_events']for r in summary['per_owner']}
        if (report['completed_layers']!=1034 or report['collapsed_events']!=17384 or dict(counts)!=expected_faces
                or dict(owner_counts)!=expected_owners or any(totals[k]!=census[k]for k in totals)):
            raise ValueError('Re-clipped original event/owner/face totals differ from the completed census')
        report.update(status='all_original17384_ledger_collapsed_points_covered_no_admission',all_ledger_collapsed_points_covered=True,
            collapsed_events_by_face=dict(counts),owner_statistics=[dict(owner=g['id'],face_range=g['face_range'],collapsed_events=owner_counts[g['id']])for g in owners['groups']],
            sealed_noncollapsed_face_accounting=dict(totals))
    except BaseException as error:report.update(status='refused_or_incomplete_no_admission',error=dict(type=type(error).__name__,message=str(error)))
    finally:
        after={name:sha(ROOT/name)for name in plan['files_sha256']}
        runtime_ok=sha(sys.executable)==plan['execution_python_sha256']and sha(fractions.__file__)==plan['stdlib_fraction_source_sha256']
        report.update(inputs_after=after,inputs_unchanged=after==plan['files_sha256'],stdlib_runtime_unchanged=runtime_ok,statistics=statistics,
            elapsed_seconds=time.monotonic()-began,CPU_seconds=time.process_time()-cpu_before,maxRSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            maxRSS_unit='bytes on this macOS host')
        if not report['inputs_unchanged']or not runtime_ok or sha(plan_path)!=expected:report['status']='integrity_refused_no_admission'
        report['output_files_sha256']={p.name:sha(p)for p in output.iterdir()if p.is_file()}
        write(output/'assessment.json',report);signal.alarm(0)
    print(json.dumps({k:report[k]for k in ['status','completed_layers','collapsed_events','elapsed_seconds']}))
    return 0 if report['status']=='all_original17384_ledger_collapsed_points_covered_no_admission'else 1


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('--plan-sha256',required=True);p.add_argument('--preflight',action='store_true');a=p.parse_args()
    if a.preflight:verify(a.plan,a.plan_sha256);print('Original ledger/337-owner/source/runtime bindings verified; no general diagnostic or AM executed')
    else:raise SystemExit(execute(a.plan,a.plan_sha256))
