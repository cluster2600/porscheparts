from pathlib import Path
import hashlib,json,tarfile
root=Path.cwd()
names=['mesh-V2-short-edge-resolution','cfd-V2-short-edge-resolution-run2','mesh-R0-common-h7','cfd-R0-common-h7','mesh-R0-common-h5p6','cfd-R0-common-h5p6','mesh-R0-common-h5p6-repair1','cfd-R0-common-h5p6-repair1','mesh-V2-common-h5p6-repair1','cfd-V2-common-h5p6-repair1','manufacturing-analytic-benchmark','R0-fine-diagnosis']
names+=['cfd-'+v+'-fine-150steps-phase'+str(t) for v in ['R0','V2'] for t in [150,300,450,600]]
names+=json.load(open('manufacturing-case-list.json'))
names+=['mesh-V2-h4p5','mesh-V2-h3p6','cfd-V2-fine-continuation750','cfd-R0-fine-pressure015-750','cfd-V2-fine-pressure015-900']
files=[]
for name in names:
 p=root/name
 if not p.is_dir():raise FileNotFoundError(name)
 files += [f for f in p.rglob('*') if f.is_file() and not f.is_symlink() and not any(q.startswith('processor') for q in f.relative_to(p).parts)]
files += [f for pattern in ['receipt.*.json','log.R0-*','log.V2-*','log.manufacturing-*','*refinement*.json','*fine*summary.json','*balance*.json','*manufacturing-native.*','manufacturing*.json'] for f in root.glob(pattern) if f.is_file()]
source_names=['build_analytical_mesh.py','build_analytical_system.py','prepare_analytical_cfd.py','run_bounded_task.py','summarize_reference_flow.py','run_parallel_pilot.sh','run_existing_grid_sensitivity.py','run_matched_cfd.py','gate-local.sh','analyze_flow_balance.py','analyze_flow_balance_v2.py','complete_flow_checks.py','verify_native_benchmark.py','build_manufacturing_scenarios.py','run_manufacturing_cases.py','prepare_engineering_sensitivities.py','summarize_engineering_sensitivities.py','compare_manufacturing.py','export_manufacturing_bundle.py','unit-eigenstrain.inp']
files += [root/n for n in source_names]
files += [root/'continue_admitted_mesh_flow.py',root/'run_v2_mechanics.py',root/'build_analytical_mesh_original.py',root/'summarize_analytical_fem.py']
for folder in ['private-R0-v3','private-V5','private-V2']:
 files += [root/folder/n for n in ['rotor.step','parameters.json']]
files=sorted(set(files));sha=lambda f:hashlib.file_digest(f.open('rb'),'sha256').hexdigest()
manifest={str(f.relative_to(root)):{'bytes':f.stat().st_size,'sha256':sha(f)} for f in files}
out=root/'continuation-native-evidence.tar.gz'
if out.exists():raise FileExistsError('Preserve existing archive')
with tarfile.open(out,'w:gz',compresslevel=3) as tar:
 for f in files:tar.add(f,arcname=str(f.relative_to(root)),recursive=False)
with tarfile.open(out,'r:gz') as tar:
 count=0
 for member in tar:
  stream=tar.extractfile(member)
  if not member.isfile() or member.name not in manifest or member.size!=manifest[member.name]['bytes'] or hashlib.file_digest(stream,'sha256').hexdigest()!=manifest[member.name]['sha256']:raise ValueError('Archive member verification failed')
  count+=1
if count!=len(manifest):raise ValueError('Archive member count mismatch')
record={'status':'all_archive_members_hashed_and_verified','archive_bytes':out.stat().st_size,'archive_sha256':sha(out),'all_members_verified':True,'raw_scan_included':False,'processor_replica_fields_excluded':True,'authoritative_reconstructed_fields_included':True,'members':manifest}
(root/'continuation-native-evidence-manifest.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k!='members'}));print('members',count)
