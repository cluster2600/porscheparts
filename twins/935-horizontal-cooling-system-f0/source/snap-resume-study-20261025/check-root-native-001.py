"""Reuse the pinned CGAL checker with analytic refusal controls and bounded native resources."""
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import time

root = Path('/home/lolman/935-snap-resume-20261025/field-root-repair-002')
checker = Path('/home/lolman/935-cfd-pilot-20261022/check-si-surface')
source = checker.with_name('check_si_surface.cpp'); candidate = root/'rotor-0p6.stl'
sha = lambda p: hashlib.file_digest(Path(p).open('rb'), 'sha256').hexdigest()
assert sha(checker) == '69caa50a446cfef290a2735be90076aa4ea17907a2507e611704f68fddcd6ede'
assert sha(source) == 'd6fe9d09e72f1b13a561f4707dd78aaeb735d6b535ab06572d84f1053d8f284b'
expected = 'ee8f91167f6147edd125b2b4db9da65a5704aac95879a82f2aab6bada779f9ed'
assert sha(candidate) == expected and not (root/'intersection-assessment.json').exists()
out = root/'intersection-controls-001'; assert not out.exists(); out.mkdir(mode=0o700)
v = [[0., 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]]
f = [[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]]
controls = [('closed', v, f, 0), ('open', v, f[:-1], 3),
            ('crossing', v+[[x+.2, y+.2, z+.2] for x, y, z in v], f+[[i+4 for i in face] for face in f], 4)]


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (2*1024**3, 2*1024**3))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1024**3, 1024**3))


def run(path, name):
    started = time.monotonic(); reason = None
    with (root/(name+'.stdout')).open('x') as stdout, (root/(name+'.stderr')).open('x') as stderr:
        process = subprocess.Popen([str(checker), str(path)], stdout=stdout, stderr=stderr,
                                   preexec_fn=limits, start_new_session=True)
        try: code = process.wait(timeout=300)
        except subprocess.TimeoutExpired:
            reason = 'wall_time_limit'; os.killpg(process.pid, signal.SIGTERM)
            try: process.wait(timeout=10)
            except subprocess.TimeoutExpired: os.killpg(process.pid, signal.SIGKILL); process.wait()
            code = process.returncode
    return dict(exit=code, stop_reason=reason, elapsed_s=time.monotonic()-started,
                stdout_sha256=sha(root/(name+'.stdout')), stderr_sha256=sha(root/(name+'.stderr')))


results = {}
for name, vertices, faces, expected_exit in controls:
    path = out/(name+'.off')
    with path.open('x') as stream:
        stream.write(f'OFF\n{len(vertices)} {len(faces)} 0\n')
        for row in vertices: stream.write(' '.join(map(str, row))+'\n')
        for row in faces: stream.write('3 '+' '.join(map(str, row))+'\n')
    result = run(path, name); results[name] = result
    assert result['exit'] == expected_exit and result['stop_reason'] is None
    if name != 'open':
        response = json.loads((root/(name+'.stdout')).read_text())
        assert (response['self_intersection_pairs'] == 0) == (name == 'closed')
result = run(candidate, 'candidate'); response = None
if result['exit'] == 0:
    response = json.loads((root/'candidate.stdout').read_text())
    assert (response['vertices'], response['faces'], response['self_intersection_pairs']) == (660003, 1320006, 0)
assert sha(candidate) == expected and sha(checker) == '69caa50a446cfef290a2735be90076aa4ea17907a2507e611704f68fddcd6ede'
record = dict(source_sha256=sha(__file__), candidate_sha256=expected, checker_sha256=sha(checker),
              checker_source_sha256=sha(source), controls=results, execution=result, complete_surface=response,
              full_surface_self_intersections_passed=result['exit'] == 0, input_unchanged=True,
              worker_address_space_limit_GiB=2, timeout_s=300, scale_verified=False,
              CFD_accepted=False, manufacturing_authorized=False)
(root/'intersection-assessment.json').write_text(json.dumps(record, indent=2)+'\n')
print(json.dumps(record), flush=True)
raise SystemExit(0 if result['exit'] == 0 else 1)
