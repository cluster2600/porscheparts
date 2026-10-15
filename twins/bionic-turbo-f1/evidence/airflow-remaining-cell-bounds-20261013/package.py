import hashlib
import json
from pathlib import Path
import tarfile
from datetime import datetime, timezone

base = Path('work')
delivery = Path(__file__).parent
sha = lambda p: hashlib.file_digest(p.open('rb'), 'sha256').hexdigest()
diagnostic = base / 'bionic-remaining-cell-bounds-20261013'
files = sorted(p for p in diagnostic.rglob('*') if p.is_file() and '__pycache__' not in p.parts and not p.name.startswith('automation-'))
scopes = [{'case': str(diagnostic), 'scope': 'remaining_variable_determinants_ordered_planes_and_volumes_no_admission', 'performance_accepted': False}]
assert files and len(files) == len(set(files))

inventory = [{'path': str(p.relative_to(base)), 'bytes': p.stat().st_size, 'sha256': sha(p)} for p in files]
manifest = {'created_at_utc': datetime.now(timezone.utc).isoformat(), 'cases': scopes, 'files': inventory,
            'performance_ranking_authorized': False,
            'restore_note': 'Tar hardlinks deduplicate identical payloads. Copy independently before modifying.'}
with (delivery / 'file-manifest.json').open('x') as stream:
    json.dump(manifest, stream, indent=2)
archive = delivery / 'remaining-cell-bounds.tar.gz'
seen = {}
with tarfile.open(archive, 'x:gz', compresslevel=3) as tar:
    for path, record in zip(files, inventory):
        assert not path.is_symlink() and path.resolve().is_relative_to(base.resolve())
        info = tar.gettarinfo(str(path), arcname=record['path'])
        key = (record['sha256'], record['bytes'])
        if key in seen:
            info.type, info.linkname, info.size = tarfile.LNKTYPE, seen[key], 0
            tar.addfile(info)
        else:
            with path.open('rb') as stream:
                tar.addfile(info, stream)
            seen[key] = record['path']
        if sha(path) != record['sha256']:
            raise ValueError('Source changed: ' + str(path))
    tar.add(delivery / 'file-manifest.json', arcname='file-manifest.json')
expected = {r['path']: r for r in inventory}
verified = {}
with tarfile.open(archive, 'r|gz') as tar:
    for member in tar:
        if member.name == 'file-manifest.json':
            assert hashlib.file_digest(tar.extractfile(member), 'sha256').hexdigest() == sha(delivery / 'file-manifest.json')
            continue
        if member.islnk():
            digest = verified[member.linkname]
        else:
            digest = hashlib.file_digest(tar.extractfile(member), 'sha256').hexdigest()
        assert digest == expected[member.name]['sha256']
        verified[member.name] = digest
assert set(verified) == set(expected)
receipt = {'files': len(files), 'archive_bytes': archive.stat().st_size, 'archive_sha256': sha(archive),
           'manifest_sha256': sha(delivery / 'file-manifest.json'), 'all_payloads_verified': True,
           'performance_ranking_authorized': False, 'scopes': scopes}
with (delivery / 'archive-receipt.json').open('x') as stream:
    json.dump(receipt, stream, indent=2)
print(json.dumps(receipt))
