"""Exact reviewed Figure33 metadata arming; no graphics imports or execution."""
from pathlib import Path
import copy,hashlib,importlib.util,json,os
H=Path(__file__).resolve().parent;R=H.parents[1]
def sha(q):return hashlib.sha256(q.read_bytes()).hexdigest()
def read(q):return json.loads(q.read_bytes())
def enc(v):return(json.dumps(v,indent=2,allow_nan=False)+'\n').encode()
def write(q,v):
 with q.open('xb')as f:f.write(enc(v));f.flush();os.fsync(f.fileno())
go=H/'root-review-GO-001.json';G=sha(go);assert G=='e9ef45af34aba19583331b0cef1fe001ba1e31ba94262ba9d2659ad23d0b0251';p0=read(H/'pending-plan.json');l0=read(H/'pending-launch.json');c0=read(H/'pending-command.json');p=copy.deepcopy(p0);l=copy.deepcopy(l0);c=copy.deepcopy(c0);g=str(go.relative_to(R));assert not(H/'render-001').exists()and not(H/'execution-001').exists()
p['launch_ready']=True;p['root_GO_sha256']=G;p['files_sha256'][g]=G;P=hashlib.sha256(enc(p)).hexdigest();l['launch_ready']=True;l['root_GO_sha256']=G;l['command'][4]=str(H/'plan.json');l['command'][5]=P;old=str((H/'pending-plan.json').relative_to(R));new=str((H/'plan.json').relative_to(R));l['inputs_sha256']={new if k==old else k:P if k==old else v for k,v in l['inputs_sha256'].items()};l['inputs_sha256'][g]=G;L=hashlib.sha256(enc(l)).hexdigest();c['launch_ready']=True;c['argv'][4]=str(H/'launch.json');c['argv'][6]=L
bp=copy.deepcopy(p);bp['launch_ready']=p0['launch_ready'];bp['root_GO_sha256']=p0['root_GO_sha256'];del bp['files_sha256'][g];bl=copy.deepcopy(l);bl['launch_ready']=l0['launch_ready'];bl['root_GO_sha256']=l0['root_GO_sha256'];bl['command'][4]=l0['command'][4];bl['command'][5]=l0['command'][5];del bl['inputs_sha256'][g];bl['inputs_sha256']={old if k==new else k:l0['inputs_sha256'][old]if k==new else v for k,v in bl['inputs_sha256'].items()};bc=copy.deepcopy(c);bc['launch_ready']=c0['launch_ready'];bc['argv'][4]=c0['argv'][4];bc['argv'][6]=c0['argv'][6]
for v,o,n in [(bp,p0,'pending-plan.json'),(bl,l0,'pending-launch.json'),(bc,c0,'pending-command.json')]:assert v==o and enc(v)==(H/n).read_bytes()
sup='work/carrier-process-20261017/source010-exposure-preflight-003/supervise.py';assert l['source_sha256'][sup]==sha(R/sup)
for n,v in [('plan.json',p),('launch.json',l),('command.json',c)]:write(H/n,v)
spec=importlib.util.spec_from_file_location('_Figure33_current_source_only',H/'figure.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.verify(H/'plan.json',P,True)
merged={}
for d in [l['inputs_sha256'],l['source_sha256']]:
 for n,v in d.items():assert n not in merged or merged[n]==v;merged[n]=v
assert all(m.sha(R/n)==v for n,v in merged.items())
a=dict(schema='Figure33-exact3-control-arming-1',root_GO_sha256=G,pending_sha256={n:sha(H/n)for n in ['pending-plan.json','pending-launch.json','pending-command.json']},armed_sha256={n:sha(H/n)for n in ['plan.json','launch.json','command.json']},whole3_pending_objects_and_original_stored_bytes_inverses=True,only_ARMING_whitelist_changed=True,canonical_supervisor_source_key_verified=True,current_plan_pins=len(p['files_sha256']),current_merged_launch_pins=len(merged),all_current_whole_source_field_runtime_hashes_equal=True,scientific_imports=False,argv=c['argv'])
write(H/'arming-assessment.json',a);print(json.dumps(a))
