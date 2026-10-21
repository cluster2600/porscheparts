"""Package only the fixed, closed h2/CCX evidence; no scientific imports."""
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import sys
import time
import zipfile
import zlib


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''): h.update(block)
    return h.hexdigest()


def identity(st):
    return (st.st_dev, st.st_ino, st.st_mode, st.st_uid, st.st_gid,
            st.st_nlink, st.st_size, st.st_mtime_ns, st.st_ctime_ns)


def pack(path, expected):
    started = time.monotonic(); cpu = time.process_time()
    if sha(path) != expected: raise ValueError('Pack plan changed')
    plan = json.loads(path.read_text()); root = Path(plan['source_root']); out = Path(plan['destination'])
    records = {}; total = 0
    for name, rows in plan['archives'].items():
        target = out / name
        if target.exists() or target.is_symlink(): raise FileExistsError('Preserve an existing archive')
        with zipfile.ZipFile(target, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for member, row in sorted(rows.items()):
                source = root / member; before = source.stat()
                if source.is_symlink() or sha(source) != row['sha256'] or before.st_size != row['bytes']:
                    raise ValueError('Fixed original changed before packing')
                info = zipfile.ZipInfo(member, date_time=(1980, 1, 1, 0, 0, 0))
                info.create_system = 3; info.external_attr = 0o100644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED; info._compresslevel = 6
                digest = hashlib.sha256(); count = 0
                with source.open('rb') as src, archive.open(info, 'w') as dst:
                    for block in iter(lambda: src.read(1024 * 1024), b''):
                        count += len(block); digest.update(block); dst.write(block)
                if count != row['bytes'] or digest.hexdigest() != row['sha256'] or identity(source.stat()) != identity(before):
                    raise ValueError('Original changed during packing')
        if target.stat().st_size >= 100000000: raise ValueError('Archive exceeds the strict 100 MB limit')
        records[name] = dict(sha256=sha(target), bytes=target.stat().st_size, members=rows)
        total += sum(v['bytes'] for v in rows.values())
        print(json.dumps(dict(archive=name, bytes=target.stat().st_size, members=len(rows))), flush=True)
    unchanged = all(sha(root / p) == row['sha256'] for rows in plan['archives'].values() for p, row in rows.items())
    if not unchanged or sha(path) != expected: raise ValueError('Frozen originals or plan changed')
    receipt = dict(status='three_deterministic_archives_created_no_solver', archives=records,
                   original_bytes=total, originals_unchanged=unchanged, plan_sha256=expected,
                   source_sha256=sha(__file__), zlib_version=zlib.ZLIB_VERSION,
                   fixed_timestamp=[1980, 1, 1, 0, 0, 0], fixed_mode='100644', compression='DEFLATE level 6',
                   wall_seconds=time.monotonic()-started, CPU_seconds=time.process_time()-cpu,
                   maxRSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                   memory_units='Darwin bytes', actual_workers=0, new_solver_run=False)
    with path.with_name('packaging.json').open('x') as stream: json.dump(receipt, stream, indent=2); stream.write('\n')


if __name__ == '__main__':
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('180s packaging cap')))
    signal.alarm(180); resource.setrlimit(resource.RLIMIT_CPU, (150, 151)); os.nice(10)
    try: pack(Path(sys.argv[1]), sys.argv[2])
    finally: signal.alarm(0)
