"""Preserve the terminal parallel mesh attempt and precise-export controls; exclude active outputs."""
import hashlib,json,tarfile
from pathlib import Path
p=Path('/home/lolman/935-local-relocation-20261022');out=Path('/home/lolman/935-local-relocation-archive-20261022');sha=lambda p:hashlib.file_digest(Path(p).open('rb'),'sha256').hexdigest()
assert json.loads((p/'parallel-snap-001/execution.json').read_text())['stop_reason']=='wall_time_limit'
assert json.loads((p/'hex-review-control-001/export-readback.json').read_text())['OBJ_coordinates_exact_native_boundary_subset']
paths=[]
for name in ['parallel-snap-001','hex-review-control-001']:
 paths += [f for f in (p/name).rglob('*') if f.is_file()]
for name in ['prepare-parallel-snap-002.py','run-parallel-snap-002.py','prepare-hex-review-control-001.py','prepare-castellation-review-001.py','parallel-snap-002/preparation.json','parallel-snap-002/log.decomposePar']:
 paths.append(p/name)
paths.sort();assert not any(f.is_symlink() for f in paths)
rows=[{'name':str(f.relative_to(p)),'bytes':f.stat().st_size,'sha256':sha(f)} for f in paths];assert sum(r['bytes'] for r in rows)<4*1024**3
archive=out/'parallel-snap-checkpoint-001.tar.gz';manifest=out/'parallel-snap-manifest-001.json';receipt=out/'parallel-snap-receipt-001.json';assert not any(f.exists() for f in [archive,manifest,receipt])
with manifest.open('x') as s:json.dump({'entries':rows,'parent_serial_archive_sha256':'fb9e6be0eace8d3441d042a84e2cdf0b4ce521b2a25c41490298bdf060f55d6d','parallel_resume_outputs_excluded':True,'archived_parallel_and_control_jobs_finished':True,'CFD_accepted':False,'manufacturing_authorized':False},s,indent=2)
with tarfile.open(archive,'x:gz',compresslevel=1) as s:
 for f in paths:s.add(f,arcname='parallel-checkpoint/'+str(f.relative_to(p)),recursive=False)
 s.add(manifest,arcname=manifest.name,recursive=False)
with tarfile.open(archive,'r:gz') as s:
 assert len(s.getmembers())==len(rows)+1
 for f,row in zip(paths,rows):
  member=s.getmember('parallel-checkpoint/'+row['name']);assert member.isfile() and member.size==row['bytes'] and hashlib.file_digest(s.extractfile(member),'sha256').hexdigest()==row['sha256'] and sha(f)==row['sha256']
 assert s.extractfile(manifest.name).read()==manifest.read_bytes()
r={'archive_sha256':sha(archive),'archive_bytes':archive.stat().st_size,'manifest_sha256':sha(manifest),'payloads':len(rows),'all_members_verified':True,'all_archived_inputs_unchanged':True,'parallel_resume_outputs_excluded':True,'new_paid_instance_created':False,'CFD_accepted':False,'manufacturing_authorized':False}
with receipt.open('x') as s:json.dump(r,s,indent=2)
print(json.dumps(r),flush=True)
