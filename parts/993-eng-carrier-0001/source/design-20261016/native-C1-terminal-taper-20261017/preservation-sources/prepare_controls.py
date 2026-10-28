"""Seal pending pack controls; stat large members only, never pack or replay."""
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1];OLD=H.with_name('carrier-C1-terminal-taper-delivery-preparation-001');SUP=R/'work/carrier-process-20261017/source010-exposure-preflight-003/supervise.py'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(1024**2),b''):h.update(b)
 return h.hexdigest()
def rel(p):return str(p.relative_to(R))
def write(p,v):
 with p.open('x')as f:json.dump(v,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
start=time.monotonic();v=json.loads((OLD/'inventory-proposal.json').read_text());assert len(v['members'])==495 and sum(x['bytes']for x in v['members'].values())==598766939
copies={n:rel(H/n)for n in ['README.md','restore.py','replay_analysis.py','selfcheck.py','source-derivation.json','runtime-provenance.json']}
for q in sorted((H/'sources').iterdir()):copies['sources/'+q.name]=rel(q)
for q in sorted((H/'dependencies').iterdir()):copies['dependencies/'+q.name]=rel(q)
for n in ['package.py','pack_owned.py','prepare_controls.py']:copies['preservation-sources/'+n]=rel(H/n)
copies['preservation-sources/inventory-proposal.json']=rel(OLD/'inventory-proposal.json');copies['preservation-sources/commands-proposal.json']=rel(OLD/'commands-proposal.json')
files={rel(q):sha(q)for q in sorted(H.rglob('*'))if q.is_file()};files.update({rel(q):sha(q)for q in [OLD/'inventory-proposal.json',OLD/'dependencies.json',OLD/'commands-proposal.json',SUP]})
for row in v['stages']:
 for key,keysha in [('ROOT','ROOT_sha256'),('terminal','terminal_sha256')]:
  q=R/row[key];assert q.stat().st_size<8*1024**2 and sha(q)==row[keysha];files[row[key]]=row[keysha]
for key,digest in [(v['FEA_ROOT']['path'],v['FEA_ROOT']['sha256']),(v['FEA_ROOT']['owner_terminal'],v['FEA_ROOT']['owner_terminal_sha256'])]:assert sha(R/key)==digest;files[key]=digest
for name,row in json.loads((H/'source-derivation.json').read_text()).items():
 q=R/row['reference'];assert sha(q)==row.get('reference_sha256',row['source_sha256']);files[row['reference']]=sha(q)
minimum=3*100000000+64*1024**2
p=dict(schema='closed-new-taper-three-archive-pack-control-1',status='SOURCE_ONLY_NOT_ARMED',launch_ready=False,root_GO=None,root_GO_sha256=None,bounds=dict(outer=200,inner=180,CPU=[150,151],threads=1,workers=0),files_sha256=files,inventory=rel(OLD/'inventory-proposal.json'),manifest_template=rel(H/'manifest-template.json'),destination=rel(H/'capsule-001'),actual_pack_plan=rel(H/'actual-pack-plan.json'),capsule_files=copies,package_source_sha256=sha(H/'package.py'),minimum_free_bytes=minimum,actual_archives=None,actual_manifest_sha256=None,native_runs=0,restore_runs=0,analysis_replays=0,automatic_retry=False)
write(H/'pending-pack-plan.json',p)
l=dict(schema='owned-local-diagnostic-launch-plan-1',status='SOURCE_ONLY_NOT_ARMED',launch_ready=False,root_GO=None,root_GO_sha256=None,command=[sys.executable,'-I','-B',str(H/'pack_owned.py'),'pack',str(H/'pack-plan.json'),None],cwd=str(R),output_directory=p['destination'],execution_directory=rel(H/'pack-execution-001'),source_sha256={rel(SUP):sha(SUP),rel(H/'pack_owned.py'):sha(H/'pack_owned.py')},inputs_sha256=dict(files,**{rel(H/'pending-pack-plan.json'):sha(H/'pending-pack-plan.json')}),section_workers=1,maximum_pending_layers=2,actual_workers=0,total_wall_budget_seconds=200,cleanup_grace_seconds=[10,10]);write(H/'pending-pack-launch.json',l)
write(H/'pending-pack-command.json',dict(status='NOT_ARMED',launch_ready=False,argv_template=[sys.executable,'-I','-B',str(SUP),str(H/'pack-launch.json'),'--plan-sha256',None],actual_launch_sha256=None,parent_nice_modified=False))
write(H/'future-verify-replay.json',dict(status='SOURCE_ONLY_no_actual_manifest_or_GO',manifest_sha256=None,stored_verify=dict(scientific_imports=False,all_member_bytes=True,outer_seconds=180,child_alarm=None,argv_template=['python3','-I','-B','restore.py','verify','--manifest-sha256',None]),analysis_replay=dict(scientific_imports='pinned_numpy_only',one_fresh_restoration=True,whole_report_objects=4,whole_serialized_report_byte_equalities=4,native_CAD_Gmsh_CCX_calls=0,outer_seconds=180,inner_seconds=150,CPU=[140,141],threads=1,workers=0,cwd='/',nice=10,numpy_site='work/part-workflow/runtimes/cad-base/lib/python3.10/site-packages',interpreter='work/part-workflow/runtimes/geometry-standalone/bin/python',minimum_free_bytes=598766939+72*1024**2,argv_template=['<pinned-python>','-I','-B','replay_analysis.py','<fresh-output>','--manifest-sha256',None,'--numpy-site','<pinned-numpy-site>']),native_reproduction=dict(authorized=False,commands_retained_in='preservation-sources/commands-proposal.json',requires_fresh_output_container_rebinding=True,old_paths_immutable=True)))
r=subprocess.run([sys.executable,'-I','-B',str(H/'pack_owned.py'),'preflight',str(H/'pending-pack-plan.json'),sha(H/'pending-pack-plan.json')],cwd=R,text=True,capture_output=True,timeout=30);(H/'preflight.stdout.log').write_text(r.stdout);(H/'preflight.stderr.log').write_text(r.stderr);assert r.returncode==0,r.stderr
write(H/'preflight-assessment.json',dict(status='actual_source_only_preflight_PASS_no_large_body_reads',actual_returncode=r.returncode,pending_plan_sha256=sha(H/'pending-pack-plan.json'),pending_launch_sha256=sha(H/'pending-pack-launch.json'),stdout_sha256=sha(H/'preflight.stdout.log'),stderr_sha256=sha(H/'preflight.stderr.log'),small_pins=len(files),members_statted_only=495,large_members_freshly_hashed=False,packing_executed=False,restoration_executed=False,analysis_executed=False,elapsed_seconds=time.monotonic()-start))
write(H/'preparation-assessment.json',dict(status='SOURCE_ONLY_standalone_taper_capsule_utilities_and_unarmed_pack_controls',actual_stdlib_tests=18,actual_stdlib_tests_RC=0,actual_stdlib_tests_chunk='48f0f1',source_files_sha256={rel(q):sha(q)for q in [H/'pack_owned.py',H/'package.py',H/'restore.py',H/'replay_analysis.py',H/'selfcheck.py',H/'source-derivation.json',H/'manifest-template.json',H/'runtime-provenance.json',H/'README.md']},preflight_sha256=sha(H/'preflight-assessment.json'),pending_plan_sha256=sha(H/'pending-pack-plan.json'),pending_launch_sha256=sha(H/'pending-pack-launch.json'),members=495,raw_bytes=598766939,archive_bytes_SHA_unknown=True,standalone_no_old_C1_H2_restore=True,output_paths_absent=not(H/'capsule-001').exists()and not(H/'pack-execution-001').exists(),no_parts_publication=True))
print(json.dumps({n:sha(H/n)for n in ['pack_owned.py','restore.py','replay_analysis.py','selfcheck.py','README.md','manifest-template.json','pending-pack-plan.json','pending-pack-launch.json','pending-pack-command.json','preflight-assessment.json','preparation-assessment.json']}))
