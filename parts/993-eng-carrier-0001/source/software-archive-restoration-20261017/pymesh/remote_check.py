"""Metadata and exact owned-scope checks for this one fresh PyMesh restoration."""
import hashlib, json, pathlib, platform, subprocess, sys

mode, p = sys.argv[1], json.loads(sys.argv[2]); root = pathlib.Path(p['prefix'])


def sha(path):
    h = hashlib.sha256()
    with pathlib.Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()


def query(unit):
    r = subprocess.run(['systemctl', '--user', 'show', unit, '--no-pager', '-p', 'LoadState', '-p', 'ActiveState', '-p', 'ControlGroup'], capture_output=True, text=True, timeout=5)
    d = dict(line.split('=', 1) for line in r.stdout.splitlines() if '=' in line)
    if r.returncode not in (0, 1, 4) or 'LoadState' not in d or 'ActiveState' not in d: raise ValueError('Query error is not absence')
    if d['LoadState'] == 'not-found':
        if d['ActiveState'] != 'inactive' or d.get('ControlGroup'): raise ValueError('Invalid absent-scope metadata')
        return dict(d, absent=True)
    if r.returncode != 0: raise ValueError('Loaded scope query failed')
    return dict(d, absent=False)


if mode != 'cleanup' and sha(p['archive']) != p['archive_sha256']: raise ValueError('Existing archive changed')
if mode == 'preflight':
    if platform.system() != 'Linux' or platform.machine() != 'x86_64': raise ValueError('Retained rootfs requires Linux x86_64')
    if root.resolve() != root: raise ValueError('Fresh prefix path contains a symlink')
    if root.exists() or root.is_symlink(): raise ValueError('Fresh remote prefix required')
    for unit in p['units']:
        if not query(unit)['absent']: raise ValueError('Owned scope is not fresh')
    root.mkdir(mode=0o700)
    (root/'smoke').mkdir(mode=0o700)
    with (root/'owner.json').open('x') as f: json.dump(p['owner'], f, sort_keys=True)
    report = dict(status='fresh_owned_prefix_verified', archive_sha256=p['archive_sha256'], prefix=str(root), owner=p['owner'])
else:
    if json.loads((root/'owner.json').read_text()) != p['owner']: raise ValueError('Owned prefix changed')
    if mode == 'cleanup':
        states = {}
        for unit in p['attempted_units']:
            d = query(unit)
            if not d['absent'] and d['ActiveState'] not in ('inactive', 'failed'):
                if pathlib.PurePosixPath(d.get('ControlGroup', '')).name != unit: raise ValueError('Cgroup identity differs')
                for action in ('kill', 'stop'):
                    r = subprocess.run(['systemctl', '--user', action, unit], capture_output=True, text=True, timeout=8)
                    if r.returncode != 0: raise ValueError('Owned scope cleanup failed')
                d = query(unit)
            if not d['absent'] and d['ActiveState'] not in ('inactive', 'failed'): raise ValueError('Owned scope remains active')
            states[unit] = d
        report = dict(status='owned_scopes_inactive_or_absent_verified', scopes=states)
    elif mode in ('uploaded', 'restored', 'post'):
        for name, digest in p['copied_files'].items():
            q = root/name
            if q.is_symlink() or not q.is_file() or sha(q) != digest: raise ValueError('Copied source differs')
        report = dict(status='copied_sources_verified', copied_files_sha256=p['copied_files'])
        if mode in ('restored', 'post'):
            installed = root/'pymesh'; receipt = installed/'installation-receipt.json'; runtime = json.loads(receipt.read_text())
            if runtime['export_archive_sha256'] != p['archive_sha256'] or runtime['native_module_sha256'] != p['native_sha256']:
                raise ValueError('Restored runtime differs')
            for name, digest in runtime['runtime_files_sha256'].items():
                q = installed/'rootfs'/name
                if q.is_symlink() or sha(q) != digest: raise ValueError('Restored runtime file changed')
            for name, value in runtime['rootfs_symlinks'].items():
                if str((installed/'rootfs'/name).readlink()) != value: raise ValueError('Restored runtime symlink changed')
            for name, digest in runtime['source_files_sha256'].items():
                if sha(installed/name) != digest: raise ValueError('Installed source changed')
            report.update(installation_receipt_sha256=sha(receipt), runtime_file_count=len(runtime['runtime_files_sha256']),
                          runtime_symlink_count=len(runtime['rootfs_symlinks']))
            if mode == 'post':
                if report != p['restored_before']: raise ValueError('Restoration identity changed during smoke')
                smoke = json.loads((root/'smoke'/'smoke-receipt.json').read_text())
                if smoke['status'] != 'restored_runtime_import_and_existing_prism_smoke_passed' or smoke['volume_mm3'] != 4000:
                    raise ValueError('Smoke receipt refused')
                if sha(root/'smoke'/'result.npz') != smoke['result_sha256']: raise ValueError('Native result changed')
                report.update(smoke=smoke, smoke_receipt_sha256=sha(root/'smoke'/'smoke-receipt.json'))
    else: raise ValueError('Unknown operation')
print(json.dumps(report, sort_keys=True))
