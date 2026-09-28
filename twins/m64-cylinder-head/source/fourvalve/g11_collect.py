#!/usr/bin/env python3
"""Collect stopped G11 outputs within the PicoGK transfer allocation, not a release.

Omitted matrices remain fingerprinted, but this archive is NOT directly resumable.
Run only after the producer/telemetry have stopped; changing inputs fail closed.
"""
import argparse
import gzip
import hashlib
import importlib.util
import io
import json
import lzma
import os
from pathlib import Path
import stat
import tarfile

LIMIT = 2_000_000_000 - 10_000_000
# Match the unchanged private extractor's uncompressed and per-file ceilings.
CONTENT_LIMIT = 12 * 1024**3
FILE_LIMIT = 2 * 1024**3
JOB = 'g11-collection'
INVENTORY = 'collection-inventory.json'
OMIT = {'matrix.sti', 'matrix.mas'}
ROOT_FILES = {'input-checksums.txt', 'g11_gpu_job.sh', 'run.log', 'tests.log',
              'preflight.txt', 'ccx-version.txt', 'environment.txt', 'hardware-gpu.csv',
              'hardware-cpu.txt', 'hardware-memory.txt', 'telemetry.csv',
              'gmsh-native-packages.txt', 'bootstrap.log', 'bootstrap-apt.log'}


def digest(stream):
    value = hashlib.sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b''):
        value.update(block)
    return value.hexdigest()


def regular(path, root):
    if path.is_symlink() or not path.resolve().is_relative_to(root):
        raise ValueError('collection path escapes root or is a symlink')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    stream = os.fdopen(fd, 'rb')
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        stream.close()
        raise ValueError('collection requires regular single-link files')
    return stream


def sources(root):
    results = root/'results'
    if results.is_symlink() or not results.is_dir():
        raise ValueError('regular results directory required')
    paths = [root/name for name in ROOT_FILES if (root/name).exists() or (root/name).is_symlink()]
    for folder, directories, files in os.walk(results, followlinks=False):
        if any((Path(folder)/name).is_symlink() for name in directories):
            raise ValueError('result directory symlinks forbidden')
        paths.extend(Path(folder)/name for name in files)
    if len(paths) > 4000:
        raise ValueError('too many collection files')
    return sorted(paths)


def pack(root, archive, max_bytes=LIMIT, xz_preset=None):
    if not 0 < max_bytes <= LIMIT:
        raise ValueError('archive cap exceeds the bounded allocation')
    if xz_preset not in (None, 1, 6, 9):
        raise ValueError('unsupported bounded XZ preset')
    root = root.resolve(strict=True)
    paths = sources(root)
    rows = []
    for path in paths:
        name = path.relative_to(root).as_posix()
        if not name.isascii() or '\\' in name or any(ord(c) < 32 or ord(c) == 127 for c in name):
            raise ValueError('ambiguous collection filename')
        with regular(path, root) as stream:
            before = os.fstat(stream.fileno())
            size = before.st_size
            fingerprint = digest(stream)
            after = os.fstat(stream.fileno())
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                raise ValueError('producer changed a fingerprinted file')
        omitted = name.startswith('results/') and path.name in OMIT
        rows.append(dict(path=name, size_bytes=size, sha256=fingerprint, retained=not omitted,
                         reason='regenerable_matrix_omitted_for_transfer_cap' if omitted else 'retained'))
    inventory = dict(classification='bounded_private_G11_collection_not_manufacturing_release',
                     max_archive_bytes=max_bytes, traffic_reserve_bytes=10_000_000,
                     compression='gzip6' if xz_preset is None else f'xz{xz_preset}_dict256MiB',
                     directly_checkpoint_resumable=False, original_result_hashes_modified=False,
                     limitation='Regenerate omitted matrices from retained matrix.inp with the pinned runtime; original fingerprints must be checked before checkpoint reuse. CUDA residuals cannot be rechecked from this archive alone.',
                     files=rows)
    payload = json.dumps(inventory, indent=2, sort_keys=True).encode()+b'\n'
    retained_sizes = [r['size_bytes'] for r in rows if r['retained']]
    if max(retained_sizes, default=0) > FILE_LIMIT or sum(retained_sizes)+len(payload) > CONTENT_LIMIT:
        raise ValueError('retained data exceeds unchanged safe extractor bounds')
    created = False
    try:
        with archive.open('xb') as output:
            created = True
            os.chmod(archive, 0o600)
            compressed = gzip.GzipFile(fileobj=output, mode='wb', compresslevel=6) if xz_preset is None else lzma.LZMAFile(
                output, 'w', filters=[{'id': lzma.FILTER_LZMA2, 'preset': xz_preset, 'dict_size': 256*1024**2}])
            with compressed, tarfile.open(fileobj=compressed, mode='w:') as handle:
                entry = tarfile.TarInfo(JOB+'/'+INVENTORY)
                entry.size, entry.mode = len(payload), 0o600
                handle.addfile(entry, io.BytesIO(payload))
                for row in sorted(rows, key=lambda r: (str(Path(r['path']).parent), Path(r['path']).suffix, r['path'])):
                    if not row['retained']:
                        continue
                    path = root/row['path']
                    with regular(path, root) as stream:
                        entry = tarfile.TarInfo(JOB+'/'+row['path'])
                        entry.size, entry.mode = row['size_bytes'], 0o600
                        handle.addfile(entry, stream)
                        stream.seek(0)
                        if digest(stream) != row['sha256'] or os.fstat(stream.fileno()).st_size != row['size_bytes']:
                            raise ValueError('producer changed a collected file')
                    if output.tell() > max_bytes:
                        raise ValueError('compressed archive exceeds transfer cap')
        if sources(root) != paths:
            raise ValueError('producer changed the collection file set')
        if archive.stat().st_size > max_bytes:
            raise ValueError('compressed archive exceeds transfer cap')
        with archive.open('rb') as stream:
            fingerprint = digest(stream)
    except BaseException:
        if created:
            archive.unlink()
        raise
    return dict(archive_sha256=fingerprint, archive_bytes=archive.stat().st_size,
                retained_files=sum(r['retained'] for r in rows), omitted_files=sum(not r['retained'] for r in rows),
                directly_checkpoint_resumable=False, transfer_size_preflight_passed=True)


def verify(archive, expected_sha256):
    # Reuse path rules, but stream verification avoids duplicating GB on the Mac.
    helper = Path(__file__).resolve().parents[4]/'deploy/vast/simready/_private_destination.py'
    spec = importlib.util.spec_from_file_location('g11_private_destination', helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if archive.is_symlink() or not 0 < archive.stat().st_size <= LIMIT:
        raise ValueError('invalid archive or transfer cap exceeded')
    with archive.open('rb') as stream:
        if digest(stream) != expected_sha256:
            raise ValueError('archive fingerprint mismatch')
    # Bound hostile headers/decompression before creating any extracted files.
    inventory, retained, names, total = None, {}, set(), 0
    with tarfile.open(archive, 'r|*') as handle:
        for member in handle:
            _, name = module._member_path(member, JOB)
            if (not member.isfile() or not 0 <= member.size <= FILE_LIMIT
                    or name in names or len(names) >= 4001):
                raise ValueError('invalid or duplicate archive member')
            names.add(name)
            total += member.size
            if total > CONTENT_LIMIT:
                raise ValueError('archive content exceeds extraction bound')
            if name == JOB+'/'+INVENTORY:
                if member.size > 2_000_000:
                    raise ValueError('invalid collection inventory')
                inventory = json.load(handle.extractfile(member))
                if (inventory['directly_checkpoint_resumable'] is not False
                        or inventory['original_result_hashes_modified'] is not False
                        or not 0 < inventory['max_archive_bytes'] <= LIMIT
                        or archive.stat().st_size > inventory['max_archive_bytes']):
                    raise ValueError('invalid collection contract')
                rows = inventory['files']
                if len(rows) > 4000 or len({r['path'] for r in rows}) != len(rows):
                    raise ValueError('invalid inventory membership')
                for row in rows:
                    relative = row['path']
                    module._member_path(tarfile.TarInfo(JOB+'/'+relative), JOB)
                    if (type(row['retained']) is not bool or type(row['size_bytes']) is not int or row['size_bytes'] < 0
                            or not (relative.startswith('results/') or relative in ROOT_FILES)
                            or (not row['retained'] and not (relative.startswith('results/') and Path(relative).name in OMIT))):
                        raise ValueError('invalid inventory row')
                    if row['retained']:
                        retained[JOB+'/'+relative] = row
            else:
                if inventory is None or name not in retained:
                    raise ValueError('archive membership differs from inventory')
                row = retained[name]
                with handle.extractfile(member) as stream:
                    if member.size != row['size_bytes'] or digest(stream) != row['sha256']:
                        raise ValueError('retained file fingerprint mismatch; collection is unverified')
    if inventory is None:
        raise ValueError('collection inventory missing')
    if names != {JOB+'/'+INVENTORY} | set(retained):
        raise ValueError('archive membership differs from inventory')
    return dict(retained_files_verified=len(retained), directly_checkpoint_resumable=False,
                verification='streamed_content_sha256_no_extraction',
                omitted_files=sum(not r['retained'] for r in rows))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    create = commands.add_parser('pack')
    create.add_argument('--root', type=Path, required=True)
    create.add_argument('--archive', type=Path, required=True)
    create.add_argument('--max-bytes', type=int, default=LIMIT)
    create.add_argument('--xz-preset', type=int, choices=(1, 6, 9))
    check = commands.add_parser('verify')
    check.add_argument('--archive', type=Path, required=True)
    check.add_argument('--sha256', required=True)
    args = parser.parse_args()
    result = pack(args.root, args.archive, args.max_bytes, args.xz_preset) if args.command == 'pack' else verify(args.archive, args.sha256)
    print(json.dumps(result, sort_keys=True))
