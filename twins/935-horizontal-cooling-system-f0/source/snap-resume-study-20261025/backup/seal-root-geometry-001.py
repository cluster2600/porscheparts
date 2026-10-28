"""Seal the finished Mac geometry experiments; raw CFD case is archived separately."""
import hashlib
import json
from pathlib import Path
import tarfile

root = Path(__file__).resolve().parents[5]
phase = root/'work/935-snap-resume-20261025'
out = root/'work/935-snap-resume-archive-20261025'
out.mkdir(mode=0o700, exist_ok=True)
sha = lambda p: hashlib.file_digest(Path(p).open('rb'), 'sha256').hexdigest()
proof = json.loads((phase/'field-root-audit-002/native-intersection-assessment.json').read_text())
assert proof['full_surface_self_intersections_passed'] and proof['input_unchanged']
assert json.loads((phase/'field-root-repair-002/execution.json').read_text())['zero_closing_reproduces_original_STL_bytes']
paths = sorted(f for f in phase.rglob('*') if f.is_file())
assert not any(f.is_symlink() for f in phase.rglob('*'))
rows = [dict(name=str(f.relative_to(phase)), bytes=f.stat().st_size, sha256=sha(f)) for f in paths]
assert sum(r['bytes'] for r in rows) < 8*1024**3
archive = out/'root-geometry-checkpoint-001.tar.gz'; manifest = out/'root-geometry-manifest-001.json'
receipt = out/'root-geometry-receipt-001.json'
assert not any(p.exists() for p in [archive, manifest, receipt])
with manifest.open('x') as stream:
    json.dump(dict(entries=rows, CFD_case_excluded=True, geometry_jobs_finished=True,
                   scale_verified=False, CFD_accepted=False, manufacturing_authorized=False), stream, indent=2)
with tarfile.open(archive, 'x:gz', compresslevel=1) as stream:
    for f in paths: stream.add(f, arcname='root-geometry/'+str(f.relative_to(phase)), recursive=False)
    stream.add(manifest, arcname=manifest.name, recursive=False)
with tarfile.open(archive, 'r:gz') as stream:
    assert len(stream.getmembers()) == len(rows)+1
    for f, row in zip(paths, rows):
        member = stream.getmember('root-geometry/'+row['name'])
        assert member.isfile() and member.size == row['bytes']
        assert hashlib.file_digest(stream.extractfile(member), 'sha256').hexdigest() == row['sha256'] == sha(f)
    assert stream.extractfile(manifest.name).read() == manifest.read_bytes()
record = dict(source_sha256=sha(__file__), archive_sha256=sha(archive), archive_bytes=archive.stat().st_size,
              manifest_sha256=sha(manifest), payloads=len(rows), all_members_verified=True,
              all_archived_inputs_unchanged=True, CFD_case_excluded=True, new_paid_instance_created=False,
              scale_verified=False, CFD_accepted=False, manufacturing_authorized=False)
with receipt.open('x') as stream: json.dump(record, stream, indent=2)
print(json.dumps(record), flush=True)
