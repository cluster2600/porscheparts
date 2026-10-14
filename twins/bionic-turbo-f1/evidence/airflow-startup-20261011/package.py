import hashlib
import json
from pathlib import Path
import tarfile
from datetime import datetime, timezone

root = Path('work/bionic-airflow-20261011')
delivery = Path(__file__).parent
sha = lambda path: hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()
files = []
cases = []
for case in sorted(root.iterdir()):
    if not case.is_dir() or not (case / 'case-manifest.json').exists():
        continue
    manifest = json.loads((case / 'case-manifest.json').read_text())
    proof = json.loads((case / 'cartesian-proof.json').read_text())
    execution = json.loads((case / 'run-cartesian-solve.json').read_text())
    if execution['status'] == 'running':
        selected = [case / name for name in manifest['file_sha256'] | proof['mesh']['mesh_sha256']]
        selected += [case / 'case-manifest.json', case / 'cartesian-proof.json']
        selected += list((case / 'provenance').glob('*'))
        scope = 'immutable_inputs_only_solver_running'
    else:
        selected = [p for p in case.rglob('*') if p.is_file()]
        scope = 'completed_attempt_all_files'
    cases.append({'case': case.name, 'scope': scope, 'execution_status_at_inventory': execution['status']})
    files += sorted(set(selected))
inventory = []
for path in files:
    assert path.resolve().is_relative_to(root.resolve()) and not path.is_symlink()
    inventory.append({'path': str(path.relative_to(root.parent)), 'bytes': path.stat().st_size, 'sha256': sha(path)})
manifest = {'created_at_utc': datetime.now(timezone.utc).isoformat(), 'cases': cases, 'files': inventory,
            'performance_ranking_authorized': False, 'running_solver_outputs_included': False,
            'restore_note': 'Duplicate immutable files use tar hardlinks. Make independent copies before any edit or new calculation.'}
manifest_path = delivery / 'file-manifest.json'
with manifest_path.open('x') as stream:
    json.dump(manifest, stream, indent=2)
archive = delivery / 'airflow-startup.tar.gz'
seen = {}
with tarfile.open(archive, 'x:gz', compresslevel=3) as tar:
    for path, record in zip(files, inventory):
        info = tar.gettarinfo(str(path), arcname=record['path'])
        key = (record['sha256'], record['bytes'])
        if key in seen:
            info.type = tarfile.LNKTYPE
            info.linkname = seen[key]
            info.size = 0
            tar.addfile(info)
        else:
            with path.open('rb') as stream:
                tar.addfile(info, stream)
            seen[key] = record['path']
        if sha(path) != record['sha256']:
            raise ValueError('Source changed while packaging: ' + str(path))
    tar.add(manifest_path, arcname='file-manifest.json')
with tarfile.open(archive, 'r:gz') as tar:
    for record in inventory:
        stream = tar.extractfile(record['path'])
        if hashlib.file_digest(stream, 'sha256').hexdigest() != record['sha256']:
            raise ValueError('Archive member mismatch')
receipt = {'created_at_utc': datetime.now(timezone.utc).isoformat(), 'files': len(files),
           'raw_bytes': sum(r['bytes'] for r in inventory), 'unique_payloads': len(seen),
           'archive_bytes': archive.stat().st_size, 'archive_sha256': sha(archive),
           'manifest_sha256': sha(manifest_path), 'all_archive_members_read_back_and_verified': True,
           'scope': cases, 'performance_ranking_authorized': False}
with (delivery / 'archive-receipt.json').open('x') as stream:
    json.dump(receipt, stream, indent=2)
print(json.dumps(receipt))
