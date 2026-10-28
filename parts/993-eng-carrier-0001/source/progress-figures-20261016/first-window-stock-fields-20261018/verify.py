"""Verify this image capsule's exact local bytes; do not import a rendering runtime."""
import hashlib
import json
from pathlib import Path, PurePosixPath

H=Path(__file__).resolve().parent

def verify():
 p=H/'archive.json';a=json.loads(p.read_text());assert a['schema']=='actual-Figure33-stock-mechanical-fields-capsule-1'
 rows=a['files_sha256'];assert set(rows)|{'archive.json'}=={str(q.relative_to(H))for q in H.rglob('*')if q.is_file()}
 total=0
 for name,digest in rows.items():
  n=PurePosixPath(name);assert not n.is_absolute()and n.as_posix()==name and all(s not in('','..','.')for s in n.parts)
  q=H/name;assert not any(x.is_symlink()for x in[q,*q.parents])
  h=hashlib.sha256()
  with q.open('rb')as f:
   for block in iter(lambda:f.read(1024**2),b''):h.update(block);total+=len(block)
  assert h.hexdigest()==digest,name
 return dict(status='exact_local_Figure33_capsule_bytes',payloads=len(rows),bytes=total,native_or_render_replay=False)
if __name__=='__main__':print(json.dumps(verify()))
