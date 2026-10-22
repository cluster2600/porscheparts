"""Seal the user-stopped case, referencing byte-identical files in the verified parent archive."""
import hashlib,json,tarfile
from pathlib import Path

p=Path('/home/lolman/935-local-relocation-20261022');out=Path('/home/lolman/935-local-relocation-archive-20261022')
sha=lambda p:hashlib.file_digest(Path(p).open('rb'),'sha256').hexdigest()
parent=out/'parallel-snap-checkpoint-001.tar.gz';assert sha(parent)=='1ac2f47c521393ef37571061fe6347a792d61f000a23018478fef147c39a020e'
parent_manifest=out/'parallel-snap-manifest-001.json';assert sha(parent_manifest)=='404e223c52622c2853b06e4e167516cfd87556240cc15bd442cc88bb9761b94c'
known={r['name']:r for r in json.loads(parent_manifest.read_text())['entries']}
pause=json.loads((p/'pause-request-20261022.json').read_text());execution=json.loads((p/'parallel-snap-002/execution.json').read_text())
assert pause['reason']=='user_requested_pause_and_publish_main' and execution['exit']==-15 and execution['parent_checkpoint_unchanged']
assert not any(Path(f'/proc/{pid}').exists() for pid in [1703577,1703579,1703749,1703751,1703754,1703756])
files=sorted([f for f in (p/'parallel-snap-002').rglob('*') if f.is_file()]+[p/'pause-request-20261022.json'])
assert not any(f.is_symlink() for f in files)
rows=[];payloads=[]
for f in files:
 name=str(f.relative_to(p));row={'name':name,'bytes':f.stat().st_size,'sha256':sha(f)}
 key=name.replace('parallel-snap-002/','parallel-snap-001/',1);match=known.get(key)
 if match and match['bytes']==row['bytes'] and match['sha256']==row['sha256']:row.update(storage='parent_archive',parent_name=key)
 else:row['storage']='pause_archive';payloads.append(f)
 rows.append(row)
archive=out/'parallel-snap-pause-checkpoint-001.tar.gz';manifest=out/'parallel-snap-pause-manifest-001.json';receipt=out/'parallel-snap-pause-receipt-001.json'
assert not any(f.exists() for f in [archive,manifest,receipt])
record={'entries':rows,'parent_archive_sha256':sha(parent),'parent_manifest_sha256':sha(parent_manifest),'parent_member_prefix':'parallel-checkpoint/','pause_member_prefix':'pause-checkpoint/','user_requested_pause':True,'owned_mesh_processes_absent':True,'last_written_mesh_stage':'castellated_before_snapping','snapped_mesh_completed':False,'CFD_accepted':False,'manufacturing_authorized':False}
manifest.write_text(json.dumps(record,indent=2)+'\n')
with tarfile.open(archive,'x:gz',compresslevel=1) as t:
 for f in payloads:t.add(f,arcname='pause-checkpoint/'+str(f.relative_to(p)),recursive=False)
 t.add(manifest,arcname=manifest.name,recursive=False)
with tarfile.open(archive,'r:gz') as t:
 assert len(t.getmembers())==len(payloads)+1
 for row in rows:
  if row['storage']=='pause_archive':
   member=t.getmember('pause-checkpoint/'+row['name']);assert member.isfile() and member.size==row['bytes'] and hashlib.file_digest(t.extractfile(member),'sha256').hexdigest()==row['sha256']
  assert sha(p/row['name'])==row['sha256']
 assert t.extractfile(manifest.name).read()==manifest.read_bytes()
r={'source_sha256':sha(__file__),'archive_sha256':sha(archive),'archive_bytes':archive.stat().st_size,'manifest_sha256':sha(manifest),'case_files':len(rows),'new_payloads':len(payloads),'reused_parent_files':len(rows)-len(payloads),'all_members_and_parent_references_verified':True,'user_requested_pause':True,'owned_mesh_processes_absent':True,'CFD_accepted':False,'manufacturing_authorized':False}
receipt.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)
