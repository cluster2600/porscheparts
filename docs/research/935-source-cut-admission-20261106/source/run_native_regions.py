"""Run source-region native controls and exports with owned, bounded children."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time


def sha(path):
    return hashlib.file_digest(Path(path).open('rb'), 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    spec = json.loads(args.job.read_text())
    assert spec['schema'] == '935-source-cut-native-1'
    for item in spec['inputs']:
        assert sha(item['path']) == item['sha256']
    args.output.mkdir(mode=0o700, exist_ok=False)
    assert shutil.disk_usage(args.output).free >= 4 * 1024**3
    started = time.monotonic()
    rows = []
    phases = [('build-controls', 'build', True, None),
              ('check-controls', 'check', True, 'build-controls'),
              ('build-regions', 'build', False, None),
              ('check-regions', 'check', False, 'build-regions')]
    try:
        for name, mode, controls_only, built in phases:
            command = [sys.executable, spec['native_source'], '--job', str(args.job),
                       '--output', str(args.output / name), '--mode', mode]
            if controls_only:
                command += ['--controls-only']
            if built:
                command += ['--built', str(args.output / built)]
            peak = 0
            sampled = False
            reason = None
            phase_started = time.monotonic()
            with (args.output / (name + '.log')).open('xb') as log:
                child = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                         start_new_session=True)
                try:
                    while child.poll() is None:
                        probe = subprocess.run(['ps', '-o', 'rss=', '-p', str(child.pid)],
                                               capture_output=True, text=True)
                        assert probe.returncode == 0 or child.poll() is not None
                        memory = probe.stdout.strip()
                        if memory:
                            sampled = True
                            peak = max(peak, int(memory))
                        if time.monotonic() - started > 600:
                            reason = 'shared_600_second_budget'
                        elif peak > 4 * 1024**2:
                            reason = '4_GiB_child_RSS_budget'
                        elif shutil.disk_usage(args.output).free < 4 * 1024**3:
                            reason = '4_GiB_disk_floor'
                        if reason:
                            break
                        time.sleep(.2)
                finally:
                    if child.poll() is None:
                        os.killpg(child.pid, signal.SIGTERM)
                        try:
                            child.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            os.killpg(child.pid, signal.SIGKILL)
                    code = child.wait()
            row = dict(phase=name, exit_code=code, seconds=time.monotonic()-phase_started,
                       maximum_sampled_child_RSS_KiB=peak if sampled else None,
                       owned_child_reaped=True, stop_reason=reason)
            rows.append(row)
            print(json.dumps(row), flush=True)
            assert code == 0 and reason is None, row
            assert (args.output / name / 'report.json').is_file()
        for item in spec['inputs']:
            assert sha(item['path']) == item['sha256']
    finally:
        (args.output / 'execution.json').write_text(json.dumps(dict(
            source_sha256=sha(__file__), job_sha256=sha(args.job), phases=rows,
            seconds=time.monotonic()-started, all_owned_children_reaped=all(
                row['owned_child_reaped'] for row in rows), complete=len(rows)==4 and all(
                    row['exit_code']==0 and row['stop_reason'] is None for row in rows)), indent=2)+'\n')


if __name__ == '__main__':
    main()
