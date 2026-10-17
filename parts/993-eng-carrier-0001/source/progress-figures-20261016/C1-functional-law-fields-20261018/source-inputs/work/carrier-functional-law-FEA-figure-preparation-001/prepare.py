"""Seal only current closed 07b field bytes/metadata; no arrays or plotting imports."""
from pathlib import Path
import hashlib,json,os,stat
R=Path(__file__).resolve().parents[2];H=Path(__file__).resolve().parent;F=R/'work/carrier-process-20261017/bounded-webs-C1-functional-law-static-preparation-001';O=R/'work/carrier-terminal-taper-FEA-figure-preparation-001';S=R/'work/carrier-process-20261017/source010-exposure-preflight-003/supervise.py'
def sha(p):
 before=p.stat();identity=lambda x:(x.st_dev,x.st_ino,x.st_mode,x.st_size,x.st_mtime_ns,x.st_ctime_ns);assert stat.S_ISREG(before.st_mode)and not p.is_symlink()
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 assert identity(before)==identity(p.stat());return h.hexdigest()
def rel(p):return str(p.relative_to(R))
def write(p,d):
 with p.open('x')as f:json.dump(d,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
review=F/'root-solver-terminal-review-001.json';assert review.stat().st_size<10000;assert sha(review)=='2b8c079b19b1c329ad75cec098dd4c044603701a412691e36cac55e01e94db05';root=json.loads(review.read_bytes());term=F/'solver-terminal-collection.json';assert term.stat().st_size<400000;assert sha(term)=='90ab99de7c502f3bb2c62441a6469466a806f2962a1067173dfb08d5245746a5'==root['owner_terminal_sha256'];owner=json.loads(term.read_bytes());prior=json.loads((O/'pending-plan.json').read_bytes());runtime=prior['runtime_sha256'];assert len(runtime)==219;files=dict(runtime);cases=[];fixture=[];stats={}
for case in ('rigid','spring'):
 folder=F/(case+'-001');assert(folder/'assessment.json').stat().st_size<200000;a=json.loads((folder/'assessment.json').read_text());name=a['case_name'];mesh=folder/'cad/mesh-7'
 row=dict(role=case,case=name,folder=rel(folder),terminal=rel(term),assessment=rel(folder/'assessment.json'),native_receipt=rel(folder/'execution/native-receipt.json'),record=rel(mesh/(name+'.json')),field=rel(mesh/(name+'.npz')),deck=rel(mesh/(name+'.inp')),mesh_inp=rel(mesh/'mesh.inp'),mesh_npz=rel(mesh/'mesh.npz'),mesh_meta=rel(mesh/'mesh.json'),peaks=rel(folder/'global-peaks.json'),energy=rel(folder/'energy-audit.json'),loads=rel(folder/'execution/load-and-supports.json'))
 for k,v in row.items():
  if k not in ('role','case','folder'):
   q=R/v;before=q.stat();assert before.st_size<30*1024**2;files[v]=sha(q);stats[v]=dict(bytes=before.st_size,sha256=files[v])
   if k!='terminal':assert owner['cases'][case]['whole_outputs'][str(q.relative_to(F))]==stats[v]
 cases.append(row);fixture.append(dict(paths=row,docs={k:json.loads((R/row[k]).read_text())for k in ['terminal','assessment','native_receipt','record','peaks','energy','loads']}))
for p in [review,S,H/'figure.py',H/'source-changes.json',H/'figure-from-taper.diff',H/'README.md',H/'prepare.py',O/'figure.py',R/'scripts/render_carrier_fields.py',R/'parts/993-eng-carrier-0001/source/bionic-20261011/simulate.py']:
 files[rel(p)]=sha(p)
fixturepath=H/'data-closed-cases.json';write(fixturepath,dict(cases=fixture,source_files_sha256=files,root_review=root));files[rel(fixturepath)]=sha(fixturepath)
p=dict(schema='actual-current07b-two-coarse-case-fields-plan-1',launch_ready=False,root_GO=str(H/'root-review-GO-001.json'),root_GO_sha256=None,source_root=str(R),actual_workers=0,deformation_amplification=1,root_review=rel(review),root_review_sha256=sha(review),combined_terminal=rel(term),combined_terminal_sha256=sha(term),actual_BREP_sha256='07b354e3716b4e856010e271f7a36aa7f6fe05a4ee4ce36eb0959af84e92409e',cases=cases,display_zoom_XY_mm=prior['display_zoom_XY_mm'],runtime_sha256=runtime,files_sha256=files,literal_functions=prior['literal_functions'],output_directory=rel(H/'render-001'),execution_directory=rel(H/'execution-001'),language='English',candidate_qualified=False,new_complete_function_contract_passed=True,all_original_stock_and_old_candidate_refusals_preserved=True,stress_convergence_established=False,strength_allowable=None,outer_seconds=180,inner_seconds=150,CPU_soft_hard_seconds=[140,141])
write(H/'pending-plan.json',p)
launch=dict(schema='owned_actual_current07b_coarse_field_draw_pending_1',launch_ready=False,root_GO=p['root_GO'],root_GO_sha256=None,command=['/Library/Frameworks/Python.framework/Versions/3.10/bin/python3.10','-B',str(H/'figure.py'),'render',str(H/'pending-plan.json'),sha(H/'pending-plan.json'),str(H/'render-001')],cwd=str(R),output_directory=p['output_directory'],execution_directory=p['execution_directory'],source_sha256={rel(S):sha(S),rel(H/'figure.py'):sha(H/'figure.py')},inputs_sha256=dict(files,**{rel(H/'pending-plan.json'):sha(H/'pending-plan.json')}),section_workers=1,maximum_pending_layers=2,actual_workers=0,total_wall_budget_seconds=180,cleanup_grace_seconds=[10,10])
write(H/'pending-launch.json',launch);write(H/'pending-command.json',dict(launch_ready=False,argv=['/usr/local/bin/python3','-I','-B',str(S),str(H/'pending-launch.json'),'--plan-sha256',sha(H/'pending-launch.json')]))
write(H/'field-sources.json',dict(schema='actual-current07b-figure31-fields-byte-sources-1',ROOT_sha256=sha(review),owner_sha256=sha(term),whole_selected_case_file_bytes=stats,selected_bytes=sum(v['bytes']for v in stats.values()),actual_array_or_DAT_FRD_parse=False,render_executed=False))
print(json.dumps(dict(source_sha256=sha(H/'figure.py'),pending_plan_sha256=sha(H/'pending-plan.json'),pending_launch_sha256=sha(H/'pending-launch.json'),pending_command_sha256=sha(H/'pending-command.json'),fixture_sha256=sha(fixturepath),selected_sources=len(stats),selected_source_bytes=sum(v['bytes']for v in stats.values()),pins=len(files),runtime=len(runtime))))
