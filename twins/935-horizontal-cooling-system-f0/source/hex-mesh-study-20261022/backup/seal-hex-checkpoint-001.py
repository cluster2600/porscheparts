"""Preserve the stopped serial mesh and qualified MPI controls; exclude the active resume."""
import hashlib,json,tarfile
from pathlib import Path
p=Path('/home/lolman/935-local-relocation-20261022');out=Path('/home/lolman/935-local-relocation-archive-20261022');sha=lambda p:hashlib.file_digest(Path(p).open('rb'),'sha256').hexdigest()
assert json.loads((p/'hex-native-001/execution.json').read_text())['stop_reason']=='wall_time_limit'
assert json.loads((p/'parallel-cube-001/geometry-readback.json').read_text())['native_full_quality_passed']
paths=[]
for name in ['hex-template-001','hex-native-001','mpi-probe-001','parallel-cube-001']:
 paths += [f for f in (p/name).rglob('*') if f.is_file()]
for name in ['prepare-hex-template-001.py','run-hex-native-001.py','probe-rootless-mpi-001.py','qualify-parallel-mesh-001.py','prepare-parallel-snap-001.py','run-parallel-snap-001.py','parallel-snap-001/preparation.json','parallel-snap-001/log.decomposePar']:
 paths.append(p/name)
paths.sort();assert not any(f.is_symlink() for f in paths)
rows=[{'name':str(f.relative_to(p)),'bytes':f.stat().st_size,'sha256':sha(f)} for f in paths];assert sum(r['bytes'] for r in rows)<4*1024**3
archive=out/'hex-serial-checkpoint-001.tar.gz';manifest=out/'hex-serial-manifest.json';receipt=out/'hex-serial-receipt.json';assert not any(f.exists() for f in [archive,manifest,receipt])
with manifest.open('x') as s:json.dump({'entries':rows,'parent_science_archive_sha256':'14423ec77b9d34ec83a1823e8185ed6821b57ffaab7797308efea238d31c6a64','parallel_resume_outputs_excluded':True,'archived_serial_and_control_jobs_finished':True,'CFD_accepted':False,'manufacturing_authorized':False},s,indent=2)
with tarfile.open(archive,'x:gz',compresslevel=1) as s:
 for f in paths:s.add(f,arcname='hex-checkpoint/'+str(f.relative_to(p)),recursive=False)
 s.add(manifest,arcname=manifest.name,recursive=False)
with tarfile.open(archive,'r:gz') as s:
 assert len(s.getmembers())==len(rows)+1
 for f,row in zip(paths,rows):
  member=s.getmember('hex-checkpoint/'+row['name']);assert member.isfile() and member.size==row['bytes'] and hashlib.file_digest(s.extractfile(member),'sha256').hexdigest()==row['sha256'] and sha(f)==row['sha256']
 assert s.extractfile(manifest.name).read()==manifest.read_bytes()
r={'archive_sha256':sha(archive),'archive_bytes':archive.stat().st_size,'manifest_sha256':sha(manifest),'payloads':len(rows),'all_members_verified':True,'all_archived_inputs_unchanged':True,'parallel_resume_outputs_excluded':True,'new_paid_instance_created':False,'CFD_accepted':False,'manufacturing_authorized':False}
with receipt.open('x') as s:json.dump(r,s,indent=2)
print(json.dumps(r),flush=True)
