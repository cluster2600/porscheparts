"""Archive a terminal native check, omitting only independently hash-matched inputs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tarfile
import time


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--instance-id', type=int, required=True)
    parser.add_argument('--input-manifest-sha256', required=True)
    parser.add_argument('--input-archive-sha256', required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    state = root.with_name(root.name+'.collection.json')
    archive = root.with_name(root.name+'-results.tar.gz')
    assert not state.exists() and not archive.exists(), 'Inspect the existing collector handle before retrying'
    assert json.loads((root/'ownership.json').read_text())['instance_id'] == args.instance_id
    assert sha(root/'input-manifest.json') == args.input_manifest_sha256
    assert sha(root/'inputs.tar.gz') == args.input_archive_sha256
    owned_live = []
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        try:
            command = (proc/'cmdline').read_bytes()
            if (b'check_recovered_mesh.py' in command or b'checkMesh' in command) and (proc/'cwd').resolve().is_relative_to(root):
                status = (proc/'stat').read_text().rsplit(')', 1)[1].split()[0]
                if status != 'Z':
                    owned_live.append(int(proc.name))
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
    assert not owned_live, 'Owned worker or native check is still live'
    terminal_path = root/'terminal.json'
    error_path = root/'worker-error.json'
    assert terminal_path.exists() or error_path.exists(), 'No terminal worker receipt; preserve and diagnose the same job'
    expected = {row['path']: row for row in json.loads((root/'input-manifest.json').read_text())['files']}
    for name, digest in [('input-manifest.json', args.input_manifest_sha256), ('inputs.tar.gz', args.input_archive_sha256)]:
        expected[name] = {'sha256': digest, 'bytes': (root/name).stat().st_size}
    files, omitted, changed = [], [], []
    status = dict(pid=os.getpid(), stage='hashing_terminal_files', started_epoch=time.time(),
                  source_sha256=sha(__file__), archive=str(archive))

    def save():
        temp = state.with_suffix('.pending')
        temp.write_text(json.dumps(status, indent=2)+'\n')
        temp.replace(state)

    save()
    for path in sorted(root.rglob('*')):
        assert not path.is_symlink(), 'Unexpected task symlink refused'
        if not path.is_file():
            continue
        row = {'path': str(path.relative_to(root)), 'sha256': sha(path), 'bytes': path.stat().st_size}
        original = expected.get(row['path'])
        if original and row['sha256'] == original['sha256'] and row['bytes'] == original['bytes']:
            omitted.append(row)
        else:
            files.append(row)
            if original:
                changed.append(row['path'])
    manifest = dict(files=files, omitted_verified_inputs=omitted, changed_input_paths=changed,
                    worker_confirmed_terminal=True, native_check_processes_confirmed_absent=True,
                    instance_id=args.instance_id, source_sha256=sha(__file__),
                    worker_terminal=json.loads((terminal_path if terminal_path.exists() else error_path).read_text()))
    manifest_path = root/'recovery-manifest.json'
    with manifest_path.open('x') as stream:
        stream.write(json.dumps(manifest, indent=2)+'\n')
    status['stage'] = 'archiving_terminal_files'
    save()
    with tarfile.open(archive, 'w:gz', compresslevel=1) as target:
        for row in files:
            target.add(root/row['path'], arcname=row['path'], recursive=False)
        target.add(manifest_path, arcname=manifest_path.name, recursive=False)
    status.update(stage='complete', archive_sha256=sha(archive), archive_bytes=archive.stat().st_size,
                  files=len(files), omitted_inputs=len(omitted), completed_epoch=time.time())
    save()
    print(json.dumps(status), flush=True)


if __name__ == '__main__':
    main()
