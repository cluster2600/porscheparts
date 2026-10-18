"""One unarmed drawing of closed actual section data; no plotting imports."""
import ast,copy,hashlib,importlib.util,json,sys
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1];W=R/'work/carrier-process-20261017'
OLD=R/'work/carrier-current24af-own-worst-section-figure-preparation-001';SECTION=W/'bounded-webs-first-window-corner-slide-own-worst-peak-section-preparation-002';OBS=W/'bounded-webs-first-window-corner-slide-own-worst-peak-native-preparation-001'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def rel(p):return str(p.relative_to(R))
def enc(v):return(json.dumps(v,indent=2,allow_nan=False)+'\n').encode()
def derive():
 original=(OLD/'render.py').read_text();current=(H/'render.py').read_text();reuse=read(H/'source-reuse.json')
 for name in reuse['literal_helpers']:
  fn=lambda text:ast.get_source_segment(text,next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)and n.name==name));assert fn(original)==fn(current)
 runtime=read(OLD/'pending-plan.json')['runtime_sha256'];basis=read(SECTION/'plan.json');files={n:d for n,d in basis['files_sha256'].items()if '/runtimes/'not in n};files.update(runtime)
 own=[H/n for n in ['render.py','prepare.py','selfcheck.py','README.md','ARMING.md','source-reuse.json','source-changes.json','metadata-source-derivation.json','source001-preservation.json']]
 fixed=[OLD/'render.py',OLD/'pending-plan.json',OLD/'pending-launch-plan.json',OLD/'pending-command.json',SECTION/'root-terminal-review-001.json',SECTION/'terminal-collection-001.json',SECTION/'plan.json',SECTION/'output-001/assessment.json',SECTION/'output-001/own_current24af_worst-section.brep',SECTION/'output-001/own_current24af_worst-section.json',SECTION/'output-001/own_current24af_worst-section-data.json',OBS/'root-terminal-review-001.json',OBS/'terminal-collection-001.json',OBS/'output-001/assessment.json']
 observer_plan=read(OBS/'plan.json');peak=R/observer_plan['peak_files'][observer_plan['case_keys'].index(observer_plan['selected_case'])];files.update({rel(p):sha(p)for p in own+fixed+[peak]})
 preserved=read(H/'source001-preservation.json');prior=read(R/preserved['source001_ROOT']);assert sha(R/preserved['source001_ROOT'])==preserved['source001_ROOT_sha256']=='2f28d18b605b089fe77968fc8a441c212a3b732f62dfbf6a03df06d065945f6e'and prior['ROOT_visual_review_pass']is False and prior['current_publication_allowed']is False
 assert all(sha(R/n)==row['sha256']and(R/n).stat().st_size==row['bytes']for n,row in preserved['originals'].items());files.update(preserved['files_sha256'])
 plan=dict(schema='actual-current24af-own-worst-section-projected-chords-figure-plan-1',launch_ready=False,root_GO=None,root_GO_sha256=None,bounds=dict(outer=180,inner=150,CPU=[140,141],threads=1,workers=0),section_preparation=rel(SECTION),observer_preparation=rel(OBS),section_ROOT_sha256=sha(SECTION/'root-terminal-review-001.json'),observation_ROOT_sha256=sha(OBS/'root-terminal-review-001.json'),candidate_BREP_sha256=basis['BREP_sha256'],global_peak_file=rel(peak),selected_case=observer_plan['selected_case'],projected_reciprocal_pair_count=2,normal_chords_projected_to_YZ=True,section_thickness_claimed=False,new_CAD_or_FEA=False,output_directory=rel(H/'render-001'),execution_directory=rel(H/'execution-001'),files_sha256=files,runtime_sha256=runtime)
 s=importlib.util.spec_from_file_location('_R1_section_draw_metadata',H/'render.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.closed_data(plan)
 sup=W/'source010-exposure-preflight-003/supervise.py';launch=copy.deepcopy(read(OLD/'pending-launch-plan.json'));oldcmd=launch['command'];launch.update(schema='owned_actual_current24af_section_projected_chords_pending_1',launch_ready=False,root_GO=None,root_GO_sha256=None,total_wall_budget_seconds=180,output_directory=plan['output_directory'],execution_directory=plan['execution_directory'],command=[*oldcmd[:4],str(H/'render.py'),'render',str(H/'pending-plan.json'),hashlib.sha256(enc(plan)).hexdigest()],source_sha256={rel(sup):sha(sup),rel(H/'render.py'):sha(H/'render.py')},inputs_sha256={**files,rel(H/'pending-plan.json'):hashlib.sha256(enc(plan)).hexdigest()})
 command=dict(schema='pending_actual_current24af_section_projected_chords_command_1',launch_ready=False,root_GO=None,root_GO_sha256=None,argv=[str(R/'work/part-workflow/runtimes/geometry-standalone/bin/python'),'-I','-B',str(sup),str(H/'pending-launch-plan.json'),'--plan-sha256',hashlib.sha256(enc(launch)).hexdigest()],cwd=str(R),parent_not_niced=True)
 assert all(not(H/n).exists()and not(H/n).is_symlink()for n in ['plan.json','launch-plan.json','command.json','render-001','execution-001'])
 return {'pending-plan.json':plan,'pending-launch-plan.json':launch,'pending-command.json':command}
if __name__=='__main__':
 objects=derive();check=sys.argv[1:]==['--check']
 for n,v in objects.items():
  if check:assert(H/n).read_bytes()==enc(v)
  else:
   with(H/n).open('xb')as f:f.write(enc(v))
 print(json.dumps(dict(status='readonly_all3_controls_byte_equal'if check else'SOURCE_ONLY_actual_current24af_own_worst_section_drawing_unarmed',controls={n:hashlib.sha256(enc(v)).hexdigest()for n,v in objects.items()},casepins=len(objects['pending-plan.json']['files_sha256']),runtimefiles=len(objects['pending-plan.json']['runtime_sha256']))))
