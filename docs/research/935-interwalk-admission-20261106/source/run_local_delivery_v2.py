"""Execute a pinned local delivery ledger, retaining child termination and output witnesses."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time


def sha(path):
    return hashlib.file_digest(Path(path).open('rb'), 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    assert plan['schema'] == '935-local-source-delivery-1'
    for item in plan['inputs']:
        assert sha(item['path']) == item['sha256']
    args.output.mkdir(mode=0o700, exist_ok=False)
    started = time.monotonic()
    rows = []
    complete = False
    requested_signals = []
    def request_shutdown(number, _frame):
        requested_signals.append(number)
    previous_handlers = {number: signal.signal(number, request_shutdown)
                         for number in (signal.SIGTERM, signal.SIGINT)}
    try:
        for phase in plan['phases']:
            if requested_signals:
                raise RuntimeError('shutdown_requested_before_next_phase')
            peak = None
            reason = None
            began = time.monotonic()
            environment = os.environ.copy()
            environment.update(phase.get('environment', {}))
            with (args.output/(phase['name']+'.log')).open('xb') as log:
                child = subprocess.Popen(phase['command'], env=environment, stdout=log,
                                         stderr=subprocess.STDOUT, start_new_session=True)
                try:
                    while child.poll() is None:
                        if requested_signals:
                            reason = 'external_signal_'+str(requested_signals[0])
                            break
                        probe = subprocess.run(['ps','-o','rss=','-p',str(child.pid)],
                                               capture_output=True, text=True)
                        assert probe.returncode == 0 or child.poll() is not None
                        if probe.stdout.strip():
                            peak = max(peak or 0, int(probe.stdout.strip()))
                        if time.monotonic()-started > 600:
                            reason = 'shared_600_second_wall_budget'
                        elif (peak or 0) > 4*1024**2:
                            reason = '4_GiB_RSS_budget'
                        elif shutil.disk_usage(args.output).free < 4*1024**3:
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
            if requested_signals:
                reason = reason or 'external_signal_'+str(requested_signals[0])
            valid = code == 0 and reason is None and Path(phase['expected_report']).is_file()
            row = dict(phase=phase['name'],exit_code=code,seconds=time.monotonic()-began,
                       maximum_sampled_child_RSS_KiB=peak,stop_reason=reason,
                       expected_report_exists=Path(phase['expected_report']).is_file(),
                       owned_child_reaped=True,successful=valid)
            rows.append(row)
            print(json.dumps(row),flush=True)
            assert valid, row
        for item in plan['inputs']:
            assert sha(item['path']) == item['sha256']
        if requested_signals:
            raise RuntimeError('shutdown_requested_before_completion')
        complete = True
    finally:
        (args.output/'execution.json').write_text(json.dumps(dict(
            source_sha256=sha(__file__),plan_sha256=sha(args.plan),phases=rows,
            complete=complete,all_owned_children_reaped=True,
            requested_signals=requested_signals,
            seconds=time.monotonic()-started),indent=2)+'\n')
        for number, handler in previous_handlers.items():
            signal.signal(number, handler)


if __name__ == '__main__':
    main()
