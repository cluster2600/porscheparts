"""Verify/restore the three fixed archives, following the native64 capsule pattern."""
import argparse
import importlib.util
import hashlib
import json
import shutil
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


def dependency(report, base_capsule=None):
    root = Path(base_capsule).absolute() if base_capsule is not None else HERE.parent / 'native-C1-20261017'
    require(root.is_dir() and not any(p.is_symlink() for p in [root, *root.parents]), 'Regular closed C1 dependency required')
    row = report['dependency']
    for name, key in [('manifest.json', 'manifest_sha256'), ('archive.json', 'inventory_sha256'), ('restore.py', 'restore_source_sha256')]:
        require(sha(root / name) == row[key], 'Closed C1 dependency identity differs')
    spec = importlib.util.spec_from_file_location('_unchanged_closed_C1_restore', root / 'restore.py')
    base = importlib.util.module_from_spec(spec); spec.loader.exec_module(base)
    inherited = base.manifest(row['manifest_sha256'])
    actual = {p: item for archive in inherited['archives'].values() for p, item in archive['members'].items()}
    require(actual == row['members'] and len(actual) == 186, 'Exact 186 C1 dependency members required')
    inventory = json.loads((root / 'archive.json').read_text())['files_sha256']
    files = {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file() and p.name != 'archive.json'}
    require(files == set(inventory) and all(not (root / p).is_symlink() and sha(root / p) == h for p, h in inventory.items()),
            'Complete durable C1 dependency inventory differs')
    return root, base


def all_members(report):
    seen = dict(report['dependency']['members'])
    for archive in report['archives'].values():
        for path, item in archive['members'].items():
            require(path not in seen, 'No overwrites or duplicate destination across dependency and H2 archives')
            seen[path] = item
    return seen


def manifest(expected, base_capsule=None):
    require(sha(HERE / 'manifest.json') == expected, 'Reviewed manifest changed')
    report = json.loads((HERE / 'manifest.json').read_text())
    require(report['schema'] == 'actual-C1-h2-dependent-native-capsule-1', 'Different capsule schema')
    require(set(report['archives']) == {'c1-h2-common.zip', 'c1-h2-rigid.zip', 'c1-h2-spring.zip'}, 'Three fixed H2 archives required')
    require(all(not (HERE / relative(p)).is_symlink() and sha(HERE / p) == h
                for p, h in report['files_sha256'].items()), 'Capsule utility/source differs')
    dependency(report, base_capsule)
    all_members(report)
    for name, row in report['archives'].items():
        path = HERE / relative(name)
        require(not path.is_symlink() and path.stat().st_size == row['bytes'] < 100000000
                and sha(path) == row['sha256'], 'Archive identity or strict size bound differs')
        for member in row['members']: relative(member)
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


def verify(expected, base_capsule=None):
    report = manifest(expected, base_capsule)
    _, base = dependency(report, base_capsule); base.verify(report['dependency']['manifest_sha256'])
    for name, row in report['archives'].items(): transfer(name, row)
    if (HERE / 'archive.json').is_file():
        inventory = json.loads((HERE / 'archive.json').read_text())['files_sha256']
        actual = {str(p.relative_to(HERE)) for p in HERE.rglob('*') if p.is_file() and p.name != 'archive.json'}
        require(actual == set(inventory) and all(sha(HERE / p) == h for p, h in inventory.items()),
                'Final durable inventory differs')
    manifest(expected, base_capsule)
    return report


def restore(output, expected, base_capsule=None):
    output = Path(output).absolute()
    require(not output.exists() and not output.is_symlink() and not any(p.is_symlink() for p in output.parents),
            'A fresh restoration root without symlinks is required')
    report = manifest(expected, base_capsule)
    _, base = dependency(report, base_capsule)
    require(shutil.disk_usage(output.parent).free >= sum(row['bytes'] for row in all_members(report).values()),
            'Insufficient free space for the exact inherited and new raw payloads')
    base.restore(output, report['dependency']['manifest_sha256'])
    for name, row in report['archives'].items(): transfer(name, row, output)
    manifest(expected, base_capsule)
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('mode', choices=['verify', 'restore'])
    p.add_argument('output', nargs='?', type=Path); p.add_argument('--manifest-sha256', required=True)
    p.add_argument('--base-capsule', type=Path)
    a = p.parse_args()
    if (a.mode == 'restore') != (a.output is not None): p.error('Only restore requires a fresh output')
    report = restore(a.output, a.manifest_sha256, a.base_capsule) if a.mode == 'restore' else verify(a.manifest_sha256, a.base_capsule)
    print(json.dumps(dict(status='all_archived_original_bytes_verified', archives=len(report['archives']),
                         files=len(all_members(report)), inherited_C1_members=186, new_solver_run=False)))
