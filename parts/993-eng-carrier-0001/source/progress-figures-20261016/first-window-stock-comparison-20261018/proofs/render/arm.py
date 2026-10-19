"""Apply only the three ROOT-approved Figure32 metadata changes; no authoring."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

H=Path(__file__).resolve().parent;R=H.parents[1]
GO='cbfb072c989da2c9fac3fd26ec25a0d2b0ca801668bf4ea3ba4f6e25aa5e55b0'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def enc(x):return(json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()
def write(n,x):
    with(H/n).open('xb')as f:f.write(enc(x))

go_path=H/'root-render-GO-001.json';go_key=str(go_path.relative_to(R));assert sha(go_path)==GO
go=json.loads(go_path.read_text());assert go['status']=='GO_one_owned_Figure32_actual_STL_comparison_render'
assert sha(H/'ARMING.md')==go['arming_contract_sha256']
names=['pending-plan.json','pending-launch-plan.json','pending-command.json']
raw={n:(H/n).read_bytes()for n in names};pending={n:json.loads(raw[n])for n in names}
assert all(sha(H/n)==go['pending_sha256'][n]and enc(pending[n])==raw[n]for n in names)
assert all(not(H/n).exists()for n in ['plan.json','launch-plan.json','command.json','arming-assessment.json','render-001','execution-001'])
p=copy.deepcopy(pending[names[0]]);p.update(launch_ready=True,root_GO=go_key,root_GO_sha256=GO);p['files_sha256'][go_key]=GO
p_sha=hashlib.sha256(enc(p)).hexdigest()
l=copy.deepcopy(pending[names[1]]);l.update(launch_ready=True,root_GO=go_key,root_GO_sha256=GO)
assert l['command'][7:9]==[str(H/'pending-plan.json'),go['pending_sha256']['pending-plan.json']]
l['command'][7:9]=[str(H/'plan.json'),p_sha]
old_key=str((H/'pending-plan.json').relative_to(R));new_key=str((H/'plan.json').relative_to(R))
l['inputs_sha256']={new_key if k==old_key else k:p_sha if k==old_key else v for k,v in l['inputs_sha256'].items()};l['inputs_sha256'][go_key]=GO
l_sha=hashlib.sha256(enc(l)).hexdigest()
c=copy.deepcopy(pending[names[2]]);c.update(launch_ready=True,root_GO=go_key,root_GO_sha256=GO)
assert c['argv'][4]==str(H/'pending-launch-plan.json')and c['argv'][6]==go['pending_sha256']['pending-launch-plan.json']
c['argv'][4]=str(H/'launch-plan.json');c['argv'][6]=l_sha
a=copy.deepcopy(p);a.update(launch_ready=False,root_GO=None,root_GO_sha256=None);a['files_sha256'].pop(go_key)
b=copy.deepcopy(l);b.update(launch_ready=False,root_GO=None,root_GO_sha256=None);b['command'][7:9]=[str(H/'pending-plan.json'),go['pending_sha256']['pending-plan.json']];b['inputs_sha256'].pop(go_key)
b['inputs_sha256']={old_key if k==new_key else k:go['pending_sha256']['pending-plan.json']if k==new_key else v for k,v in b['inputs_sha256'].items()}
d=copy.deepcopy(c);d.update(launch_ready=False,root_GO=None,root_GO_sha256=None);d['argv'][4]=str(H/'pending-launch-plan.json');d['argv'][6]=go['pending_sha256']['pending-launch-plan.json']
assert all(x==pending[n]and enc(x)==raw[n]for n,x in zip(names,[a,b,d]))
for n,x in [('plan.json',p),('launch-plan.json',l),('command.json',c)]:write(n,x)
spec=importlib.util.spec_from_file_location('_armed_Figure32_metadata',H/'figure.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.verify(H/'plan.json',p_sha,rendering=True)
m.fresh(H/'render-001');m.fresh(H/'execution-001')
pins={**l['source_sha256'],**l['inputs_sha256']};assert {n:sha(R/n)for n in pins}==pins
assert all((H/n).read_bytes()==raw[n]for n in names)
result=dict(schema='actual-Figure32-three-control-arming-1',status='ARMED_METADATA_ONLY_NO_RENDER',root_GO_sha256=GO,
    all_three_whole_object_and_stored_byte_inverses=True,pending_preserved=True,all_current_launch_pins_equal=True,
    active_sha256={n:sha(H/n)for n in ['plan.json','launch-plan.json','command.json']},launch_unique_pins=len(pins),render_executed=False)
write('arming-assessment.json',result);print(json.dumps(result))
