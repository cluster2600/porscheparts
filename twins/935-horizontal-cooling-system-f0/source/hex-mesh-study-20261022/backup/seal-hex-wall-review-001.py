"""Preserve the complete wall exports and diagnostic figure; parent native mesh is separately sealed."""
import hashlib,json,tarfile
from pathlib import Path
p=Path('/home/lolman/935-local-relocation-20261022');out=Path('/home/lolman/935-local-relocation-archive-20261022');sha=lambda p:hashlib.file_digest(Path(p).open('rb'),'sha256').hexdigest()
case=p/'castellation-review-001'
assert json.loads((case/'receipt.json').read_text())['exit']==0
assert json.loads((case/'input-readback-001.json').read_text())['copied_mesh_inputs_exactly_match_parent']
assert json.loads((case/'castellation-visual-receipt-001.json').read_text())['all_boundary_vertices_queried']
paths=[f for f in case.rglob('*') if f.is_file() and f.relative_to(case).parts[0] not in ['constant','system']]
paths.append(p/'prepare-castellation-review-001.py')
paths.sort();assert not any(f.is_symlink() for f in paths)
rows=[{'name':str(f.relative_to(p)),'bytes':f.stat().st_size,'sha256':sha(f)} for f in paths];assert sum(r['bytes'] for r in rows)<4*1024**3
archive=out/'hex-wall-review-checkpoint-001.tar.gz';manifest=out/'hex-wall-review-manifest-001.json';receipt=out/'hex-wall-review-receipt-001.json';assert not any(f.exists() for f in [archive,manifest,receipt])
with manifest.open('x') as s:json.dump({'entries':rows,'parent_serial_archive_sha256':'fb9e6be0eace8d3441d042a84e2cdf0b4ce521b2a25c41490298bdf060f55d6d','parallel_resume_outputs_excluded':True,'archived_export_and_render_jobs_finished':True,'CFD_accepted':False,'manufacturing_authorized':False},s,indent=2)
with tarfile.open(archive,'x:gz',compresslevel=1) as s:
 for f in paths:s.add(f,arcname='hex-wall-review/'+str(f.relative_to(p)),recursive=False)
 s.add(manifest,arcname=manifest.name,recursive=False)
with tarfile.open(archive,'r:gz') as s:
 assert len(s.getmembers())==len(rows)+1
 for f,row in zip(paths,rows):
  member=s.getmember('hex-wall-review/'+row['name']);assert member.isfile() and member.size==row['bytes'] and hashlib.file_digest(s.extractfile(member),'sha256').hexdigest()==row['sha256'] and sha(f)==row['sha256']
 assert s.extractfile(manifest.name).read()==manifest.read_bytes()
r={'archive_sha256':sha(archive),'archive_bytes':archive.stat().st_size,'manifest_sha256':sha(manifest),'payloads':len(rows),'all_members_verified':True,'all_archived_inputs_unchanged':True,'parallel_resume_outputs_excluded':True,'new_paid_instance_created':False,'CFD_accepted':False,'manufacturing_authorized':False}
with receipt.open('x') as s:json.dump(r,s,indent=2)
print(json.dumps(r),flush=True)
