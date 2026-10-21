"""One source/metadata-only annotation revision of the executed001 current field figure."""
import ast,copy,hashlib,importlib.util,json,subprocess,sys,time
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1];O=H.with_name('carrier-corner-slide-combined-FEA-figure-preparation-001')
def read(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rel(p):return str(Path(p).relative_to(R))
def write(p,d):
 with p.open('x')as f:json.dump(d,f,indent=2,allow_nan=False);f.write('\n')
def enc(d):return(json.dumps(d,indent=2,allow_nan=False)+'\n').encode()
def main():
 began=time.monotonic();packet=read(O/'source-packet.json');assert sha(O/'source-packet.json')=='392a9635d2ce2fdae1dac170d82be2dfe44f2f61313c5cbc9a02188b0889f2a8'
 prior={name:row['sha256']for name,row in packet['files'].items()}
 owner=read(O/'terminal-collection-001.json');assert sha(O/'terminal-collection-001.json')=='d760f2c629aa8c3a948cc070d96ff301baf1a8ce56027980934cc197f4cff912'
 for name,row in owner['all11_whole_outputs'].items():prior[rel(O/name)]=row['sha256']
 for q in [O/'terminal-collection-001.json',O/'actual-visual-review-001.json',O/'source-packet.json']:prior[rel(q)]=sha(q)
 for name,digest in prior.items():assert sha(R/name)==digest,name
 write(H/'prior001-byte-preservation.json',dict(original_source_packet_sha256=sha(O/'source-packet.json'),original_numeric_owner_sha256=sha(O/'terminal-collection-001.json'),original_visual_receipt_sha256=sha(O/'actual-visual-review-001.json'),all_source_and_actual_exports_sha256=prior,all_original_bytes_current_equal=True))
 p0,l0,c0=[read(O/name)for name in ['pending-plan.json','pending-launch.json','pending-command.json']];p=copy.deepcopy(p0);p.update(root_GO=str(H/'root-review-GO-001.json'),output_directory=rel(H/'render-001'),execution_directory=rel(H/'execution-001'))
 p['files_sha256'].update(prior)
 for q in H.iterdir():
  if q.is_file():p['files_sha256'][rel(q)]=sha(q)
 write(H/'pending-plan.json',p)
 l=copy.deepcopy(l0);l.update(root_GO=p['root_GO'],output_directory=p['output_directory'],execution_directory=p['execution_directory']);l['command'][2]=str(H/'figure.py');l['command'][4]=str(H/'pending-plan.json');l['command'][5]=sha(H/'pending-plan.json');l['command'][6]=str(H/'render-001')
 l['source_sha256']={rel(H/'figure.py')if n==rel(O/'figure.py')else n:sha(H/'figure.py')if n==rel(O/'figure.py')else v for n,v in l['source_sha256'].items()};l['inputs_sha256'].update(p['files_sha256']);l['inputs_sha256'][rel(H/'pending-plan.json')]=sha(H/'pending-plan.json')
 write(H/'pending-launch.json',l);c=copy.deepcopy(c0);c['argv'][4]=str(H/'pending-launch.json');c['argv'][6]=sha(H/'pending-launch.json');write(H/'pending-command.json',c)
 inverse=[]
 for name,old,new in [('pending-plan.json',p0,p),('pending-launch.json',l0,l),('pending-command.json',c0,c)]:
  changed={k:dict(before=old[k],after=new[k])for k in old if old[k]!=new[k]};added={k:v for k,v in new.items()if k not in old};back=copy.deepcopy(new)
  for k,row in changed.items():back[k]=row['before']
  for k in added:del back[k]
  assert back==old and enc(back)==(O/name).read_bytes();inverse.append(dict(name=name,original_sha256=sha(O/name),derived_sha256=sha(H/name),changed=changed,added=added,whole_old_pending_object_and_stored_byte_inverse=True))
 write(H/'control-derivation.json',dict(controls=inverse,original_math_resources_runtime_and_field_inputs_unchanged=True))
 spec=importlib.util.spec_from_file_location('_annotation_source_metadata',H/'figure.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.verify(H/'pending-plan.json',sha(H/'pending-plan.json'))
 t=subprocess.run(['/Library/Frameworks/Python.framework/Versions/3.10/bin/python3.10','-I','-B',str(H/'selfcheck.py')],capture_output=True,text=True,timeout=30)
 for kind,text in [('stdout',t.stdout),('stderr',t.stderr)]:
  with(H/('selfcheck.'+kind+'.log')).open('x')as f:f.write(text)
 assert t.returncode==0,t.stderr
 pins={**l['inputs_sha256'],**l['source_sha256']};assert all(sha(R/n)==v for n,v in pins.items())
 write(H/'preflight.json',dict(status='SOURCE_ONLY_single_annotation_change_and_all_current_bytes_PASS',fixtures=12,fixture_returncode=0,case_pins=len(p['files_sha256']),merged_launch_pins=len(pins),whole_one_renderer_inverse=True,whole_three_original_control_inverses=True,all_original001_bytes_preserved=True,render_or_PDF_marker=False,elapsed_seconds=time.monotonic()-began))
 result=dict(schema='current24af-combined-field-annotation-only-SOURCE002-1',status='SOURCE_ONLY_frozen_unarmed',source_sha256=sha(H/'figure.py'),actual_FEA_ROOT_sha256=p['root_review_sha256'],prior_numeric_owner_sha256=sha(O/'terminal-collection-001.json'),prior_exports_preserved=True,fixtures=12,case_pins=len(p['files_sha256']),merged_launch_pins=len(pins),pending_plan_sha256=sha(H/'pending-plan.json'),pending_launch_sha256=sha(H/'pending-launch.json'),pending_command_sha256=sha(H/'pending-command.json'),files={rel(q):dict(bytes=q.stat().st_size,sha256=sha(q))for q in sorted(H.iterdir())if q.is_file()},render_or_native=False)
 write(H/'source-packet.json',result);print(json.dumps({k:v for k,v in result.items()if k!='files'}))
if __name__=='__main__':main()
