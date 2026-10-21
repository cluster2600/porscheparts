"""Verify/restore the three fixed archives, following the native64 capsule pattern."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import zipfile

HERE = Path(__file__).resolve().parent


def require(ok, message):
    if not ok: raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b''): h.update(data)
    return h.hexdigest()


def relative(value):
    p = PurePosixPath(value)
    require(bool(value) and bool(p.parts) and not p.is_absolute()
            and not any(v in ('', '.', '..') for v in p.parts) and p.as_posix() == value,
            'Only exact relative capsule paths are allowed')
    return Path(*p.parts)


def manifest(expected):
    require(sha(HERE / 'manifest.json') == expected, 'Reviewed manifest changed')
    report = json.loads((HERE / 'manifest.json').read_text())
    require(report['schema'] == 'actual-C1-BREP-native-capsule-1', 'Different capsule schema')
    require(set(report['archives']) == {'c1-native-common.zip', 'c1-native-rigid.zip', 'c1-native-spring.zip'}, 'Three fixed archives required')
    require(all(not (HERE / relative(p)).is_symlink() and sha(HERE / p) == h
                for p, h in report['files_sha256'].items()), 'Capsule utility/source differs')
    seen = set()
    for name, row in report['archives'].items():
        path = HERE / relative(name)
        require(not path.is_symlink() and path.stat().st_size == row['bytes'] < 100000000
                and sha(path) == row['sha256'], 'Archive identity or strict size bound differs')
        for member in row['members']:
            relative(member); require(member not in seen, 'Duplicate destination across archives'); seen.add(member)
    return report


def transfer(name, row, destination=None):
    with zipfile.ZipFile(HERE / name) as archive:
        infos = archive.infolist()
        require([i.filename for i in infos] == sorted(row['members']), 'Archive inventory/order differs')
        for info in infos:
            item = row['members'][info.filename]
            require(info.file_size == item['bytes'] and not info.is_dir()
                    and stat.S_ISREG(info.external_attr >> 16)
                    and info.date_time == (1980, 1, 1, 0, 0, 0)
                    and info.compress_type == zipfile.ZIP_DEFLATED, 'Archive member metadata differs')
            target = destination / relative(info.filename) if destination is not None else None
            if target is not None: target.parent.mkdir(parents=True, exist_ok=True)
            out = target.open('xb') if target is not None else None
            digest = hashlib.sha256(); size = 0
            try:
                with archive.open(info) as stream:
                    for data in iter(lambda: stream.read(1024 * 1024), b''):
                        size += len(data); require(size <= item['bytes'], 'Expanded member too large')
                        digest.update(data)
                        if out is not None: out.write(data)
            finally:
                if out is not None: out.close()
            require(size == item['bytes'] and digest.hexdigest() == item['sha256'], 'Decompressed original differs')


def verify(expected):
    report = manifest(expected)
    for name, row in report['archives'].items(): transfer(name, row)
    if (HERE / 'archive.json').is_file():
        inventory = json.loads((HERE / 'archive.json').read_text())['files_sha256']
        actual = {str(p.relative_to(HERE)) for p in HERE.rglob('*') if p.is_file() and p.name != 'archive.json'}
        require(actual == set(inventory) and all(sha(HERE / p) == h for p, h in inventory.items()),
                'Final durable inventory differs')
    manifest(expected)
    return report


def restore(output, expected):
    output = Path(output).absolute()
    require(not output.exists() and not output.is_symlink() and not any(p.is_symlink() for p in output.parents),
            'A fresh restoration root without symlinks is required')
    report = manifest(expected); output.mkdir()
    for name, row in report['archives'].items(): transfer(name, row, output)
    manifest(expected)
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('mode', choices=['verify', 'restore'])
    p.add_argument('output', nargs='?', type=Path); p.add_argument('--manifest-sha256', required=True)
    a = p.parse_args()
    if (a.mode == 'restore') != (a.output is not None): p.error('Only restore requires a fresh output')
    report = restore(a.output, a.manifest_sha256) if a.mode == 'restore' else verify(a.manifest_sha256)
    print(json.dumps(dict(status='all_archived_original_bytes_verified', archives=len(report['archives']),
                         files=sum(len(r['members']) for r in report['archives'].values()), new_solver_run=False)))
