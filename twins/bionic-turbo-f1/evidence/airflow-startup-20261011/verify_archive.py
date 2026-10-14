import hashlib
import json
from pathlib import Path
import tarfile
from datetime import datetime, timezone

root = Path(__file__).parent
manifest = json.loads((root / 'file-manifest.json').read_text())
expected = {row['path']: row for row in manifest['files']}
verified = {}
payloads = 0
with tarfile.open(root / 'airflow-startup.tar.gz', 'r|gz') as tar:
    for member in tar:
        if member.name == 'file-manifest.json':
            assert tar.extractfile(member).read() == (root / 'file-manifest.json').read_bytes()
            continue
        assert member.name in expected and member.name not in verified
        if member.islnk():
            digest, size = verified[member.linkname]
        else:
            assert member.isfile()
            digest = hashlib.file_digest(tar.extractfile(member), 'sha256').hexdigest()
            size = member.size
            payloads += 1
        assert digest == expected[member.name]['sha256'] and size == expected[member.name]['bytes']
        verified[member.name] = digest, size
assert set(verified) == set(expected)
sha = lambda p: hashlib.file_digest(p.open('rb'), 'sha256').hexdigest()
receipt = {'created_at_utc': datetime.now(timezone.utc).isoformat(), 'files': len(expected),
           'raw_bytes': sum(row['bytes'] for row in expected.values()), 'unique_payloads': payloads,
           'archive_bytes': (root / 'airflow-startup.tar.gz').stat().st_size,
           'archive_sha256': sha(root / 'airflow-startup.tar.gz'),
           'manifest_sha256': sha(root / 'file-manifest.json'),
           'verification_method': 'Every unique payload streamed and hashed; every hardlink resolved to a previously verified payload; exact inventory coverage.',
           'verification_source_sha256': sha(Path(__file__)),
           'all_archive_members_verified': True, 'scope': manifest['cases'],
           'performance_ranking_authorized': False}
with (root / 'archive-receipt.json').open('x') as stream:
    json.dump(receipt, stream, indent=2)
print(json.dumps(receipt))
