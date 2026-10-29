#!/usr/bin/env python3
"""Fetch the two public, pinned reference packages and verify upstream hashes."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
from concurrent.futures import ThreadPoolExecutor

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DEFAULT_CACHE = ROOT / 'work/simready-reference-assets'


def verify(path, record):
    data = path.read_bytes()
    if len(data) != record['size']:
        raise ValueError(f"Size mismatch: {record['path']}")
    if record['hash_algorithm'] == 'sha256':
        digest = hashlib.sha256(data).hexdigest()
    elif record['hash_algorithm'] == 'git-blob-sha1':
        digest = hashlib.sha1(f'blob {len(data)}\0'.encode() + data).hexdigest()
    else:
        raise ValueError('Unsupported hash algorithm')
    if digest != record['hash']:
        raise ValueError(f"Hash mismatch: {record['path']}")
    return hashlib.sha256(data).hexdigest()


def fetch(cache, lock, record, offline=False):
    relative = PurePosixPath(record['path'])
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('Unsafe package path')
    target = cache / relative
    if not target.exists() and not offline:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + '.download')
        url = (f"https://huggingface.co/datasets/{lock['repository']}/resolve/"
               f"{lock['revision']}/{relative}")
        subprocess.run(['curl', '-q', '--fail', '--silent', '--show-error',
                        '--location', '--retry', '3', '--proto', '=https',
                        '--proto-redir', '=https', '--output', str(temporary), url],
                       check=True)
        verify(temporary, record)
        temporary.replace(target)
    return record['path'], verify(target, record)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=DEFAULT_CACHE)
    parser.add_argument('--offline', action='store_true')
    args = parser.parse_args()
    lock = json.loads((HERE / 'assets.lock.json').read_text())
    records = [f for asset in lock['assets'] for f in asset['files']]
    with ThreadPoolExecutor(max_workers=4) as pool:
        hashes = dict(pool.map(lambda f: fetch(args.cache, lock, f, args.offline), records))
    receipt = {'repository': lock['repository'], 'revision': lock['revision'],
               'file_count': len(records), 'total_bytes': sum(f['size'] for f in records),
               'sha256': hashes}
    args.cache.mkdir(parents=True, exist_ok=True)
    (args.cache / 'download-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(f"Verified {len(records)} files ({receipt['total_bytes']} bytes)")


if __name__ == '__main__':
    main()
