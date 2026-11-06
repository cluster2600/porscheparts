"""Recover exact public model bytes into an empty dedicated target; no inference."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import shutil
import threading
import time
import urllib.request


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', required=True, type=Path)
    args = parser.parse_args(); job = json.loads(args.job.read_text()); started = time.monotonic()
    for row in job['inputs']:
        assert sha(row['path']) == row['sha256']
    candidate = json.loads(Path(job['upstream_candidate']).read_text())
    original = json.loads(Path(job['original_receipt']).read_text())
    assert candidate['all_expected_files_match'] and len(candidate['files']) == len(original['files']) == 15
    expected = {x['file']:x['sha256'] for x in original['files']}
    assert all(expected[x['file']] == x['expected_sha256'] for x in candidate['files'])
    target, staging, backup = map(Path, (job['target'], job['staging'], job['empty_target_backup']))
    assert target.is_dir() and not target.is_symlink() and not any(target.iterdir())
    assert not staging.exists() and not backup.exists()
    total = sum(x['bytes'] for x in candidate['files'])
    assert shutil.disk_usage(target).free >= total+job['free_disk_reserve_bytes']
    staging.mkdir(mode=0o700); stop = threading.Event()
    output = Path(job['report']); assert not output.exists()
    results = []; errors = []

    def download(row):
        name = row['file']; assert Path(name).name == name and name not in ('.', '..')
        url = 'https://huggingface.co/'+candidate['repository']+'/resolve/'+candidate['resolved_revision']+'/'+name
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        digest = hashlib.sha256(); written = 0; dest = staging/name
        with opener.open(url, timeout=30) as response, dest.open('xb') as stream:
            while True:
                assert not stop.is_set() and time.monotonic()-started <= job['wall_seconds'], 'download_deadline_or_peer_failure'
                assert shutil.disk_usage(target).free >= job['free_disk_reserve_bytes'], 'disk_reserve'
                block = response.read(8*1024**2)
                if not block:
                    break
                written += len(block); assert written <= row['bytes']
                stream.write(block); digest.update(block)
        assert written == row['bytes'] and digest.hexdigest() == expected[name], 'model_byte_identity_mismatch'
        dest.chmod(0o400)
        return dict(file=name, bytes=written, sha256=digest.hexdigest())

    with ThreadPoolExecutor(max_workers=job['maximum_workers']) as executor:
        futures = [executor.submit(download, row) for row in candidate['files']]
        for future in as_completed(futures):
            try:
                result = future.result(); results.append(result)
                print(json.dumps(dict(file=result['file'], verified_bytes=result['bytes'])), flush=True)
            except Exception as error:
                stop.set(); errors.append(type(error).__name__)
    installed = False
    if not errors:
        assert len(results) == 15 and not any(target.iterdir())
        for row in candidate['files']:
            assert sha(staging/row['file']) == expected[row['file']]
        target.rename(backup)
        try:
            staging.rename(target); installed = True
        except Exception:
            backup.rename(target)
            raise
        for row in candidate['files']:
            assert sha(target/row['file']) == expected[row['file']]
    for row in job['inputs']:
        assert sha(row['path']) == row['sha256']
    report = dict(source_sha256=sha(__file__), job_sha256=sha(args.job), repository=candidate['repository'],
                  resolved_revision=candidate['resolved_revision'], expected_files=15, verified_files=len(results),
                  verified_bytes=sum(x['bytes'] for x in results), restored=installed, empty_target_preserved=installed,
                  error_types=errors, all_download_workers_joined=True, model_inference_performed=False,
                  private_data_transmitted=False, seconds=time.monotonic()-started)
    output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report), flush=True); assert installed and not errors


if __name__ == '__main__':
    main()
