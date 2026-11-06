"""Run the frozen bounded Kali checker using only hash-checked stdin payloads."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('job', 'output'):
        parser.add_argument('--'+name, required=True, type=Path)
    args = parser.parse_args(); job = json.loads(args.job.read_text()); started = time.monotonic()
    for row in job['inputs']:
        assert sha(row['path']) == row['sha256']
    source, parent, candidate = [Path(job[key]).read_bytes() for key in ('source', 'parent', 'candidate')]
    assert 0 < len(source) < 65536 and 0 < len(parent) <= 256*1024**2 and 0 < len(candidate) <= 256*1024**2
    header = dict(schema='935-read-only-streamed-source-audit-1')
    for key, payload in (('source', source), ('parent', parent), ('candidate', candidate)):
        header[key+'_bytes'] = len(payload); header[key+'_sha256'] = hashlib.sha256(payload).hexdigest()
    assert header['source_sha256'] == '3ae75b1a8a47c65405aae2111c89343eeec3aa0d3f7a8c32ac3b0be65648fae1'
    args.output.mkdir(mode=0o700, exist_ok=False)
    (args.output/'executed-command.json').write_text(json.dumps(dict(command=job['command'], header=header), indent=2)+'\n')
    payload = json.dumps(header).encode()+b'\n'+source+parent+candidate
    child = subprocess.Popen(job['command'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    timed_out = False
    try:
        stdout, stderr = child.communicate(payload, timeout=120)
    except subprocess.TimeoutExpired:
        timed_out = True; os.killpg(child.pid, signal.SIGTERM)
        try:
            stdout, stderr = child.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL); stdout, stderr = child.communicate()
    assert child.poll() is not None
    (args.output/'stdout.log').write_bytes(stdout); (args.output/'stderr.log').write_bytes(stderr)
    execution = dict(exit_code=child.returncode, timed_out=timed_out, owned_ssh_child_reaped=True, seconds=time.monotonic()-started)
    (args.output/'execution.json').write_text(json.dumps(execution, indent=2)+'\n')
    assert child.returncode == 0 and not timed_out
    result = json.loads(stdout.decode())
    assert result['parent_sha256'] == header['parent_sha256'] and result['candidate_sha256'] == header['candidate_sha256']
    assert result['source_prefix_and_provenance_exact'] and result['whole_edge_incidence_and_winding_passed']
    assert result['no_duplicate_or_zero_area_faces'] and result['persistent_payload_files_written'] == 0
    assert not result['intersection_and_vertex_fan_replay_performed']
    for row in job['inputs']:
        assert sha(row['path']) == row['sha256']
    (args.output/'report.json').write_text(json.dumps(result, indent=2)+'\n'); print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
