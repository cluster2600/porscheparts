from pathlib import Path
import hashlib,importlib.util,json,subprocess,time,struct
import numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent;RUNTIME=ROOT/'work/962-engineering/cgal-quality-patch-runtime-001';IMAGE='sha256:57c6b17ed0bd093a61a3d3cecb7563e912caeb3832fd59e8cec2d4d9d4d1e2f8'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();contract=json.loads((OUT/'frozen-contract.json').read_text())
assert sha(RUNTIME/'quality-patch')=='9310411d93e63c51b0e763d72e25403b1bc355c938b5018b9359afda075547c1'
for n,h in contract['source_sha256'].items():assert sha(ROOT/n)==h
spec=importlib.util.spec_from_file_location('objective_guard',ROOT/'twins/962-cylinder-head-f0/source/audit_quality_patch.py');checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)
def read(path):
 data=path.read_bytes();assert data[:8]==b'962SURF1';nv,nf=struct.unpack_from('<QQ',data,8);assert len(data)==24+24*(nv+nf)
 return np.frombuffer(data,dtype='<f8',count=3*nv,offset=24).reshape(-1,3),np.frombuffer(data,dtype='<u8',count=3*nf,offset=24+24*nv).reshape(-1,3)
def metric(p,f):
 xyz=p[f];u=xyz[:,1]-xyz[:,0];v=xyz[:,2]-xyz[:,0];c=np.cross(u,v);d=lambda x:np.einsum('ij,ij->i',x,x);q=2*np.sqrt(3)*np.sqrt(d(c))/(d(u)+d(v)+d(v-u));assert np.isfinite(q).all()
 return dict(triangles=len(f),below_necessary_bound=int((q<2/29).sum()),minimum_triangle_SICN=float(q.min()))
def canonical(f):
 return np.asarray([min(tuple(int(x) for x in np.roll(row,i)) for i in range(3)) for row in f],dtype=np.uint64)
def execute(label,source,result):
 name='962-quality-fixture-'+label;argv=['docker','run','--name',name,'--network','none','--read-only','--cpus','2','--memory','536870912','--memory-swap','536870912','--mount',f'type=bind,src={RUNTIME/"quality-patch"},dst=/quality-patch,readonly','--mount',f'type=bind,src={source},dst=/input.bin,readonly','--mount',f'type=bind,src={OUT},dst=/out','--entrypoint','/quality-patch',IMAGE,'/input.bin','/out/'+result]
 t=time.monotonic();process=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 try:stdout,stderr=process.communicate(timeout=60);deadline=False
 except subprocess.TimeoutExpired:
  subprocess.run(['docker','kill',name],capture_output=True,timeout=10);stdout,stderr=process.communicate(timeout=10);deadline=True
 state=subprocess.run(['docker','inspect',name,'--format','{{json .State}}'],capture_output=True,text=True,timeout=10)
 receipt={'argv':argv,'returncode':process.returncode,'stdout':stdout,'stderr':stderr,'deadline_seconds':60,'deadline_exceeded':deadline,'wall_seconds':time.monotonic()-t,'container_state':json.loads(state.stdout) if state.returncode==0 else state.stderr,'binary_sha256':sha(RUNTIME/'quality-patch'),'contract_sha256':sha(OUT/'frozen-contract.json'),'fixture_input_sha256':sha(source),'executed_controller_sha256':sha(Path(__file__))}
 with (OUT/(label+'-execution.json')).open('x') as stream:json.dump(receipt,stream,indent=2);stream.write('\n')
 cleanup=subprocess.run(['docker','rm',name],capture_output=True,text=True,timeout=10)
 with (OUT/(label+'-cleanup.json')).open('x') as stream:json.dump({'returncode':cleanup.returncode,'stdout':cleanup.stdout,'stderr':cleanup.stderr},stream,indent=2)
 return receipt
results={}
for label in ['movable-sliver','constrained-thin-box']:
 source=OUT/(label+'.bin');assert sha(source)==contract['fixtures'][label]['input_sha256'];expected=contract['fixtures'][label]['expected'];receipt=execute(label,source,label+'-result');target=OUT/(label+'-result');native=json.loads((target/'report.json').read_text());guard=checker.assess_native_report(native);p,f=read(source);q,g=read(target/'proposed-surface.bin');before,after=metric(p,f),metric(q,g)
 assert receipt['returncode']==expected['returncode'] and not receipt['deadline_exceeded'] and not receipt['container_state']['OOMKilled']
 assert before['below_necessary_bound']==expected['before_bad'] and after['below_necessary_bound']==expected['after_bad']
 assert checker.require_quality_objective(before,after)==guard['quality_objective_passed']==expected['candidate_written']
 assert (target/'quality-candidate.bin').exists()==expected['candidate_written'] and p.shape==q.shape and f.shape==g.shape
 fixed=(p[:,0]==-76)|(p[:,0]==76);assert np.array_equal(p[fixed],q[fixed]);assert np.array_equal(p.min(axis=0),q.min(axis=0)) and np.array_equal(p.max(axis=0),q.max(axis=0))
 if label=='movable-sliver':
  assert fixed.sum()==8 and q[8,2]==76 and -76<q[8,0]<76 and -76<q[8,1]<76
  assert np.array_equal(canonical(f[[0,1,*range(6,14)]]),canonical(g[[0,1,*range(6,14)]]))
  assert all(np.all(q[row,2]==76) for row in g[2:6])
 else:assert fixed.all() and np.array_equal(p,q) and np.array_equal(canonical(f),canonical(g))
 assert sha(source)==contract['fixtures'][label]['input_sha256']
 results[label]={'passed':True,'native_returncode':receipt['returncode'],'before_independent_numpy':before,'after_independent_numpy':after,'objective_guard':guard,'fixed_clip_points_exact':True,'bounds_exact':True,'input_unchanged':True,'report_sha256':sha(target/'report.json'),'execution_sha256':sha(OUT/(label+'-execution.json')),'output_files_sha256':{p.name:sha(p) for p in target.iterdir() if p.is_file()}}
# A second request at an existing result directory must stop before any remeshing/write.
label='existing-output-refusal';target=OUT/'constrained-thin-box-result';before={p.name:sha(p) for p in target.iterdir() if p.is_file()};receipt=execute(label,OUT/'constrained-thin-box.bin',target.name)
assert receipt['returncode']==2 and 'Output directory must be new' in receipt['stderr'];assert {p.name:sha(p) for p in target.iterdir() if p.is_file()}==before
results[label]={'passed':True,'native_returncode':2,'all_existing_result_bytes_preserved':True,'execution_sha256':sha(OUT/(label+'-execution.json'))}
r={'status':'native_synthetic_fixtures_passed_head_execution_on_hold','scope':'Known synthetic sliver improvement, fixed-anchor stagnation rollback and existing-output refusal only; no head geometry was passed to the helper.','frozen_contract_sha256':sha(OUT/'frozen-contract.json'),'binary_sha256':sha(RUNTIME/'quality-patch'),'controller_sha256':sha(Path(__file__)),'numpy_version':np.__version__,'results':results,'qualification':{'solver_admission_established':False,'complete_semantic_constraint_map':False,'engineering_accepted':False,'manufacturing_authorized':False}}
with (OUT/'fixture-assessment.json').open('x') as stream:json.dump(r,stream,indent=2);stream.write('\n')
print(json.dumps(r,indent=2))
