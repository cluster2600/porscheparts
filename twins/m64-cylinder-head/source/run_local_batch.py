"""Trusted LOCAL argv campaign, not a security sandbox or engineering release.

Manifest m64-local-batch/v1: campaign_timeout_seconds (2..3600), inputs
{absolute_file: sha256}, commands (1..8): argv, script, timeout_seconds,
optional gate {report: relative_output_file, key: top_level_boolean_key}.
Each script must be pinned and be argv[0] (direct) or argv[1] (interpreter).
Declare imported scripts/dependencies in inputs too; this is not auto-discovery.
Literal {output} in arguments expands to the fresh private output directory,
which is also cwd. No shell, retry, remote provisioning, or LLM API is used.
One second of campaign time is reserved for process-group kill and wait.
Passing gate reports must remain unchanged through the rest of the campaign.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import time

MAX_JSON = 1024 * 1024
FORBIDDEN = {'ssh', 'scp', 'sftp', 'rsync', 'docker', 'podman', 'vast', 'vastai',
             'bao', 'vault', 'sh', 'bash', 'zsh', 'fish', 'cmd', 'powershell'}


class StopBatch(Exception):
    pass


def require(ok, reason):
    if not ok:
        raise StopBatch(reason)


def remaining(deadline):
    left = deadline - time.monotonic()
    require(left > 0, 'campaign_timeout')
    return left


def digest(path, deadline=math.inf):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            remaining(deadline)
            result.update(block)
    return result.hexdigest()


def json_bytes(path):
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= MAX_JSON,
            'bounded_regular_json_required')
    with path.open('rb') as stream:
        data = stream.read(MAX_JSON + 1)
    require(len(data) <= MAX_JSON, 'bounded_regular_json_required')
    return data


def read_json(path):
    return json.loads(json_bytes(path))


def absolute_file(value):
    require(isinstance(value, str), 'absolute_file_required')
    path = Path(value)
    require(path.is_absolute() and '..' not in path.parts and path.is_file()
            and not path.is_symlink(), 'absolute_regular_file_required')
    return path


def bounded_number(value, maximum):
    require(type(value) in (int, float) and math.isfinite(value) and 0 < value <= maximum,
            'bounded_timeout_required')
    return float(value)


def validate(doc):
    require(isinstance(doc, dict) and doc.get('schema') == 'm64-local-batch/v1', 'manifest_schema')
    total = bounded_number(doc.get('campaign_timeout_seconds'), 3600)
    require(total >= 2, 'campaign_reserves_cleanup_second')
    inputs, commands = doc.get('inputs'), doc.get('commands')
    require(isinstance(inputs, dict) and 1 <= len(inputs) <= 256, 'bounded_inputs_required')
    pins = {}
    for value, pin in inputs.items():
        require(isinstance(pin, str) and re.fullmatch('[0-9a-f]{64}', pin), 'sha256_required')
        pins[absolute_file(value)] = pin
    require(isinstance(commands, list) and 1 <= len(commands) <= 8, 'one_to_eight_commands')
    for row in commands:
        require(isinstance(row, dict), 'command_object_required')
        argv = row.get('argv')
        require(isinstance(argv, list) and 1 <= len(argv) <= 256 and
                all(isinstance(a, str) and '\0' not in a for a in argv), 'argv_array_required')
        executable = absolute_file(argv[0])
        require(executable.name.lower() not in FORBIDDEN, 'local_commands_only')
        script = absolute_file(row.get('script'))
        require(script in pins and str(script) in argv[:2], 'explicit_pinned_script_required')
        bounded_number(row.get('timeout_seconds'), total)
        if 'gate' in row:
            gate = row['gate']
            require(isinstance(gate, dict) and isinstance(gate.get('report'), str) and
                    isinstance(gate.get('key'), str) and gate['key'], 'explicit_gate_required')
            path = Path(gate['report'])
            require(not path.is_absolute() and '..' not in path.parts and path.as_posix() not in ('', '.'),
                    'relative_gate_report_required')
    return total, pins, commands


def verify_inputs(pins, deadline):
    for path, pin in pins.items():
        remaining(deadline)
        require(path.is_file() and not path.is_symlink() and digest(path, deadline) == pin, 'input_changed')


def kill_and_wait(process, deadline):
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=min(1., max(.001, deadline - time.monotonic())))
    except subprocess.TimeoutExpired as error:
        raise StopBatch('process_cleanup_timeout') from error


def interrupted(signum, frame):
    raise StopBatch('interrupted')


def run_batch(manifest, output):
    started = time.monotonic()
    report = {'schema': 'm64-local-batch-result/v1', 'status': 'stopped', 'commands_completed': 0,
              'command_count': 0, 'steps': [], 'CFD_authorized': False, 'manufacturing_authorized': False}
    created, handlers, pins = False, {}, {}
    deadline = math.inf
    try:
        require(os.name == 'posix', 'posix_process_groups_required')
        output = Path(output).absolute()
        require(not output.exists() and not output.is_symlink(), 'fresh_output_required')
        output.mkdir(mode=0o700); created = True
        manifest = absolute_file(str(Path(manifest).absolute()))
        raw_manifest = json_bytes(manifest)
        manifest_pin = hashlib.sha256(raw_manifest).hexdigest()
        total, pins, commands = validate(json.loads(raw_manifest))
        deadline, work_deadline = started + total, started + total - 1
        require(pins.get(manifest, manifest_pin) == manifest_pin, 'manifest_pin_mismatch')
        pins[manifest] = manifest_pin
        report.update(command_count=len(commands), manifest_sha256=manifest_pin,
                      campaign_timeout_seconds=total, cleanup_reserve_seconds=1)
        for sig in (signal.SIGINT, signal.SIGTERM):
            handlers[sig] = signal.signal(sig, interrupted)
        verify_inputs(pins, work_deadline)
        for index, command in enumerate(commands, 1):
            report['failed_command_index'] = index
            verify_inputs(pins, work_deadline)
            gate = command.get('gate')
            gate_path = output / gate['report'] if gate else None
            if gate_path:
                require(not gate_path.exists() and not gate_path.is_symlink(), 'gate_report_must_be_new')
            log_path = output / f'step-{index:02d}.log'
            row = {'index': index, 'log': log_path.name, 'exit_code': None}
            report['steps'].append(row)
            argv = [a.replace('{output}', str(output)) for a in command['argv']]
            process = None
            try:
                with log_path.open('xb') as log:
                    row['timeout_seconds'] = min(command['timeout_seconds'], remaining(work_deadline))
                    command_deadline = time.monotonic() + row['timeout_seconds']
                    process = subprocess.Popen(argv, cwd=output, stdin=subprocess.DEVNULL,
                        stdout=log, stderr=subprocess.STDOUT, shell=False, start_new_session=True)
                    row['exit_code'] = process.wait(timeout=remaining(command_deadline))
            except subprocess.TimeoutExpired as error:
                raise StopBatch('command_timeout') from error
            finally:
                if process is not None:
                    # Also kill descendants left behind by a normally exiting parent.
                    active = {sig: signal.signal(sig, signal.SIG_IGN) for sig in handlers}
                    try:
                        kill_and_wait(process, deadline)
                        row['process_group_cleanup_completed'] = True
                    finally:
                        for sig, handler in active.items(): signal.signal(sig, handler)
            verify_inputs(pins, work_deadline)
            require(row['exit_code'] == 0, 'command_failed')
            if gate:
                require(gate_path.resolve().is_relative_to(output.resolve()), 'gate_outside_output')
                gate_pin = digest(gate_path, work_deadline)
                require(read_json(gate_path).get(gate['key']) is True, 'gate_not_true')
                require(digest(gate_path, work_deadline) == gate_pin, 'gate_changed')
                row.update(gate_passed=True, gate_report_sha256=gate_pin)
                pins[gate_path] = gate_pin
            row['log_sha256'] = digest(log_path, work_deadline)
            report['commands_completed'] += 1
        verify_inputs(pins, work_deadline)
        report.update(status='completed', inputs_unchanged=True)
        report.pop('failed_command_index', None)
    except StopBatch as error:
        report['reason'] = str(error)
        if str(error) == 'input_changed': report['inputs_unchanged'] = False
    except Exception as error:
        report['reason'] = type(error).__name__  # Never print private paths, argv or log content.
    finally:
        for sig, handler in handlers.items(): signal.signal(sig, handler)
        report['seconds'] = time.monotonic() - started
        if created:
            try:
                with (output / 'batch-report.json').open('x') as stream:
                    json.dump(report, stream, indent=2, allow_nan=False); stream.write('\n')
                (output / 'batch-report.json').chmod(0o600)
            except OSError:
                report.update(status='stopped', reason='batch_report_write_failed')
        summary = {k: report[k] for k in ('schema', 'status', 'commands_completed', 'command_count',
                   'failed_command_index', 'reason', 'seconds') if k in report}
        summary['CFD_authorized'] = False
        text = json.dumps(summary, allow_nan=False)
        require(len(text.encode()) <= 4095, 'summary_bound')
        print(text)
    return 0 if report['status'] == 'completed' else 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    raise SystemExit(run_batch(args.manifest, args.output))
