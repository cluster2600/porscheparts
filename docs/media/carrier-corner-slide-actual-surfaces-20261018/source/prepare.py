"""Derive one unarmed actual-STL drawing; no scientific imports."""
import ast,copy,hashlib,importlib.util,json,sys
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1];B=R/'work/carrier-process-20261017';O=R/'work/carrier-R1-actual-surface-comparison-002'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def enc(v):return(json.dumps(v,indent=2,allow_nan=False)+'\n').encode()
def rel(p):return str(p.relative_to(R))
def derive():
 old=read(O/'plan.json');changes=read(H/'source-changes.json');text=(H/'render.py').read_text()
 for row in reversed(changes['replacements']):
  assert text.count(row['after'])==row['count'];text=text.replace(row['after'],row['before'])
 assert text.encode()==(O/'render.py').read_bytes()
 runtime=old['runtime_sha256'];plan=copy.deepcopy(old)
 body=B/'bounded-webs-first-window-corner-slide-body-inspection-preparation-001'
 gen=B/'bounded-webs-first-window-corner-slide-surface-preparation-002'
 construction=B/'bounded-webs-first-window-corner-slide-preparation-001'
 obs=B/'bounded-webs-first-window-corner-slide-peak-native-preparation-001'
 plan.update(schema='d64-corner-slide-actual-STL-display-plan-1',launch_ready=False,root_GO=None,root_GO_sha256=None,
  STLs=[old['STLs'][0],str(gen/'output-001/surface/carrier-remeshed.stl')],
  STL_sha256=[old['STL_sha256'][0],'b4026f66dc77b8022e82c358553e8e93ce0cbc2ea0fd31da19ac39a9f891a803'],
  triangle_counts=[597720,598372],masses_kg=[1.2747979975709924,1.2759916739532025],
  BREP_sha256=[old['BREP_sha256'][0],'24af058467fd82a9f0c1d391bf947d427dffd311371cf8f73dafa492d204f4fd'],
  body_ROOTs=[old['body_ROOTs'][0],str(body/'root-terminal-review-001.json')],
  new_generation_ROOT=str(gen/'root-terminal-review-001.json'),new_generation_owner=str(gen/'terminal-collection-001.json'),
  new_construction_ROOT=str(construction/'root-terminal-review-001.json'),new_observer_ROOT=str(obs/'root-terminal-review-001.json'),
  section_X_mm=83.39717404347466,detail_YZ_mm=[[-18.,10.],[-12.,17.]],section_reference='prior_R1_coarse_reference_not_new_candidate_stress',
  new_CAD_or_FEA=False,PDF_authored=False)
 own=[H/n for n in ['render.py','prepare.py','selfcheck.py','README.md','ARMING.md','source-changes.json','render-from-R1.diff']]
 fixed=[O/'render.py',O/'plan.json',O/'launch.json',O/'command.json',*[Path(plan[k])for k in ['read_binary_source','section_source','raster_source','new_generation_ROOT','new_generation_owner','new_construction_ROOT','new_observer_ROOT']],*[Path(p)for p in plan['body_ROOTs']],*[Path(p)for p in plan['STLs']]]
 plan['files_sha256']={str(p):sha(p)for p in own+fixed};plan['runtime_sha256']=runtime
 spec=importlib.util.spec_from_file_location('_actual_STL_source_only',H/'render.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.verify(plan,hash_inputs=False)
 sup=B/'source010-exposure-preflight-003/supervise.py';launch=copy.deepcopy(read(O/'launch.json'))
 launch.update(schema='owned_d64_corner_slide_STL_preview_pending_1',launch_ready=False,root_GO=None,root_GO_sha256=None,
  output_directory=rel(H/'output-001'),execution_directory=rel(H/'execution-001'),
  command=[*launch['command'][:-1],str(H/'render.py')],source_sha256={rel(sup):sha(sup),rel(H/'render.py'):sha(H/'render.py')},
  inputs_sha256={**plan['files_sha256'],**runtime,rel(H/'pending-plan.json'):hashlib.sha256(enc(plan)).hexdigest()})
 command=dict(schema='pending_d64_corner_slide_STL_preview_command_1',launch_ready=False,root_GO=None,root_GO_sha256=None,
  argv=[read(O/'command.json')['argv'][0],'-I','-B',str(sup),str(H/'pending-launch-plan.json'),'--plan-sha256',hashlib.sha256(enc(launch)).hexdigest()],cwd=str(R),parent_not_niced=True)
 assert all(not(H/n).exists()and not(H/n).is_symlink()for n in ['plan.json','launch-plan.json','command.json','output-001','execution-001'])
 return {'pending-plan.json':plan,'pending-launch-plan.json':launch,'pending-command.json':command}
if __name__=='__main__':
 objects=derive();check=sys.argv[1:]==['--check']
 for name,value in objects.items():
  if check:assert(H/name).read_bytes()==enc(value)
  else:
   with(H/name).open('xb')as stream:stream.write(enc(value))
 print(json.dumps(dict(status='readonly_three_whole_pending_bytes_equal'if check else'SOURCE_only_unarmed_STL_preview',controls={n:hashlib.sha256(enc(v)).hexdigest()for n,v in objects.items()},source_and_input_pins=len(objects['pending-plan.json']['files_sha256']),external_runtime_pins=len(objects['pending-plan.json']['runtime_sha256']))))
