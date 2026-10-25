"""Preserve every finished native case; byte-identical files share one archived payload."""
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

p = Path('/home/lolman/935-snap-resume-20261025')
out = Path('/home/lolman/935-snap-resume-archive-20261025'); out.mkdir(mode=0o700, exist_ok=True)
sha = lambda f: hashlib.file_digest(f, 'sha256').hexdigest()
assert subprocess.run(['pgrep','-x','snappyHexMesh'], stdout=subprocess.DEVNULL).returncode == 1
assert subprocess.run(['pgrep','-x','reconstructPar'], stdout=subprocess.DEVNULL).returncode == 1
assert subprocess.run(['pgrep','-x','checkMesh'], stdout=subprocess.DEVNULL).returncode == 1
assert json.loads((p/'reconstructed-snap-002/execution.json').read_text())['source_unchanged']
paths = sorted(f for f in p.rglob('*') if f.is_file() and f.relative_to(p).parts[0] != 'root-archive-copy-001')
assert not any(f.is_symlink() for f in p.rglob('*') if f.relative_to(p).parts[0] != 'root-archive-copy-001')
rows = []; payloads = {}; canonical = {}
for f in paths:
    with f.open('rb') as stream: digest = sha(stream)
    key = (f.stat().st_size, digest)
    if key not in canonical:
        canonical[key] = 'native-checkpoint/'+str(f.relative_to(p)); payloads[canonical[key]] = f
    rows.append(dict(name=str(f.relative_to(p)),bytes=key[0],sha256=digest,
                     payload_member=canonical[key],mode=f.stat().st_mode & 0o777))
assert sum(f.stat().st_size for f in payloads.values()) < 8*1024**3
archive = out/'native-mesh-checkpoint-001.tar.gz'; manifest = out/'native-mesh-manifest-001.json'
receipt = out/'native-mesh-receipt-001.json'; assert not any(f.exists() for f in [archive,manifest,receipt])
with manifest.open('x') as stream:
    json.dump(dict(entries=rows,unique_payloads=len(payloads),all_jobs_terminal=True,
                   geometry_archive_dependency_sha256='fc7681b5bfab99bc7ffb24aa3feaa3ece966306dccbbbf8a141bfa92cbd770da',
                   duplicate_bytes_referenced_without_dropping_files=True,
                   CFD_accepted=False,manufacturing_authorized=False),stream,indent=2)
with tarfile.open(archive,'x:gz',compresslevel=1) as stream:
    for member,f in payloads.items(): stream.add(f,arcname=member,recursive=False)
    stream.add(manifest,arcname=manifest.name,recursive=False)
with tarfile.open(archive,'r:gz') as stream:
    assert len(stream.getmembers()) == len(payloads)+1
    checked = {}
    for member,f in payloads.items():
        info=stream.getmember(member); assert info.isfile() and info.size == f.stat().st_size
        checked[member] = sha(stream.extractfile(info))
    for row in rows:
        with (p/row['name']).open('rb') as f: assert sha(f) == row['sha256'] == checked[row['payload_member']]
    assert stream.extractfile(manifest.name).read() == manifest.read_bytes()
with archive.open('rb') as f: digest = sha(f)
with manifest.open('rb') as f: manifest_digest = sha(f)
record = dict(source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),archive_sha256=digest,
              archive_bytes=archive.stat().st_size,manifest_sha256=manifest_digest,
              case_files=len(rows),unique_payloads=len(payloads),all_members_and_references_verified=True,
              all_archived_inputs_unchanged=True,new_paid_instance_created=False,
              CFD_accepted=False,manufacturing_authorized=False)
with receipt.open('x') as stream: json.dump(record,stream,indent=2)
print(json.dumps(record),flush=True)
