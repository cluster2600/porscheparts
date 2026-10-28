"""Reuse the qualified native PicoGK root-addition experiment on the corrected rotor."""
import json
import os
from pathlib import Path
import signal
import subprocess
import time
from run_reconstruction import ROOT, save, sha

out = ROOT/'work/935-snap-resume-20261025'
qualified = ROOT/'work/935-picogk-mac-20261012'
proof = json.loads((qualified/'qualified-run.json').read_text())
assert proof['qualified_executable_sha256']['MacStudy935.dll'] == 'b93e5247bf9acdd83cf48f02d36ba83541ed907708da5eaa9141f5c965c1312c'
native = Path('/Users/maxime/Developer/PicoGK/runtime')
inputs = {qualified/'qualified-executable'/k: v for k, v in proof['qualified_executable_sha256'].items()}
inputs.update({native/k: v for k, v in proof['native_library_sha256'].items()})
rotor = ROOT/'work/935-tip-correction-20261013/rotor-060-002/rotor_candidate.stl'
sections = ROOT/'work/935-tip-correction-20261013/sections-003/sections.json'
inputs.update({rotor: 'f32bbabab3e5f7d9ca7c5283d18703cfe7cedbd3eb2c72a57a1c222c0a9df1e5',
               sections: 'd13ff7829b5b9a1589618bdc672bfb15841f53b8e94f17beb119b0ac99f45a5f'})
assert all(sha(p) == digest for p, digest in inputs.items())
case = out/'root-screen-case.json'; target = out/'root-screen-001'
assert not case.exists() and not target.exists() and not (out/'root-screen-execution.json').exists()
save(case, dict(purpose='hypothesis_screen', scale_verified=False, scale_mm_per_source_unit=1,
               rotor_stl_path=str(rotor), rotor_stl_sha256=inputs[rotor],
               sections_path=str(sections), sections_sha256=inputs[sections]))
command = ['/Users/maxime/.local/bin/dotnet', str(qualified/'qualified-executable/MacStudy935.dll'),
           'roots', str(case), str(target)]
env = dict(os.environ, DYLD_LIBRARY_PATH=str(native))
started = time.monotonic(); reason = None
with (out/'root-screen-runtime.log').open('x') as log:
    process = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    try:
        code = process.wait(timeout=600)
    except subprocess.TimeoutExpired:
        reason = 'wall_time_limit'; os.killpg(process.pid, signal.SIGTERM)
        try: process.wait(timeout=10)
        except subprocess.TimeoutExpired: os.killpg(process.pid, signal.SIGKILL); process.wait()
        code = process.returncode
unchanged = all(sha(p) == digest for p, digest in inputs.items())
save(out/'root-screen-execution.json', dict(source_sha256=sha(__file__), command=command,
     pinned_inputs_sha256={str(p): digest for p, digest in inputs.items()}, inputs_unchanged=unchanged,
     exit=code, stop_reason=reason, elapsed_s=time.monotonic()-started, timeout_s=600,
     case_sha256=sha(case), independent_surface_admission_pending=True,
     scale_verified=False, CFD_accepted=False, manufacturing_authorized=False))
assert code == 0 and unchanged
print(target, flush=True)
