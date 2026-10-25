"""Derive an isolated recipe; require exact zero-closing reproduction before local variants."""
import json
import os
from pathlib import Path
import signal
import subprocess
import time
from run_reconstruction import ROOT, fresh, save, sha

source = ROOT/'twins/935-horizontal-cooling-system-f0/source'
base = source/'picogk-935-assembly'
pins = {base/'Program.cs': '1be2d71fad739f681b828e5597332765a6e6d8156a012423879afd3648e15d6a',
        base/'Assembly935.csproj': '7ad882ece62f2f2ad73f3655401845ca742c3cbbdd6837d4b21ff0ffac069a03',
        ROOT/'parts/picogk-catalog/common/Sdf.cs': '8096c0bc8aa980cd463622d2838969987aa8a570ca7cb52a64eb08ea74ac7a40',
        Path('/Users/maxime/Developer/PicoGK/runtime/PicoGK.dll'): '710c4e0428efbe9c1cd1db1663247b45604f96d167a6726782ab8ddca350565a',
        Path('/Users/maxime/Developer/PicoGK/runtime/picogk.26.2.dylib'): '5c1cd3fc12766a85bc5c1441a95f065fb274338d1333c3ae2d3396b59d0e18e7'}
assert all(sha(p) == expected for p, expected in pins.items())
fragment = Path(__file__).with_name('root-repair-fragment-002.cs.txt')
text = (base/'Program.cs').read_text(); anchor = 'rotor.CalculateProperties(out float rotorVolume,out _);'
assert text.count(anchor) == 1
project = (base/'Assembly935.csproj').read_text(); include = '../../../../parts/picogk-catalog/common/Sdf.cs'
assert project.count(include) == 1
out = fresh(ROOT/'work/935-snap-resume-20261025/field-root-repair-002'); build = fresh(out/'build')
(build/'Program.cs').write_text(text.replace(anchor,fragment.read_text()+'\n'+anchor))
(build/'Assembly935.csproj').write_text(project.replace(include,str(ROOT/'parts/picogk-catalog/common/Sdf.cs')))
(build/'NuGet.Config').write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
dotnet = '/Users/maxime/.local/bin/dotnet'; env = dict(os.environ, DYLD_LIBRARY_PATH='/Users/maxime/Developer/PicoGK/runtime')
commands = [[dotnet,'build',str(build/'Assembly935.csproj'),'-c','Release','--configfile',str(build/'NuGet.Config'),
             '-p:PicoGKAssembly=/Users/maxime/Developer/PicoGK/runtime/PicoGK.dll','-o',str(build/'bin')]]
started = time.monotonic()
with (out/'build.log').open('x') as log:
    subprocess.run(commands[0],env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
parent_case = ROOT/'work/935-tip-correction-20261013/rotor-060-002/case.json'
assert sha(parent_case) == '079736b8e2b0e4ef51d61a448a76c6b832b0aa50ede2c093ce973d94e7cfc584'
case = json.loads(parent_case.read_text()); results = []
for radius in [0, .6, 1.2]:
    name = str(radius).replace('.','p'); case['root_closing_radius_mm'] = radius
    path = out/f'case-{name}.json'; save(path, case)
    command = [dotnet,str(build/'bin/Assembly935.dll'),str(path),sha(path),str(out/f'rotor-{name}')]
    commands.append(command); reason = None; start = time.monotonic()
    with (out/f'run-{name}.log').open('x') as log:
        process = subprocess.Popen(command,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try: code = process.wait(timeout=600)
        except subprocess.TimeoutExpired:
            reason = 'wall_time_limit'; os.killpg(process.pid,signal.SIGTERM)
            try: process.wait(timeout=10)
            except subprocess.TimeoutExpired: os.killpg(process.pid,signal.SIGKILL); process.wait()
            code = process.returncode
    result = dict(radius=radius,exit=code,stop_reason=reason,elapsed_s=time.monotonic()-start,timeout_s=600)
    save(out/f'execution-{name}.json',result); assert code == 0
    receipt = json.loads((out/f'rotor-{name}/receipt.json').read_text())
    digest = receipt['components'][0]['sha256']; assert digest == sha(out/f'rotor-{name}/rotor_candidate.stl')
    if radius == 0: assert digest == 'f32bbabab3e5f7d9ca7c5283d18703cfe7cedbd3eb2c72a57a1c222c0a9df1e5'
    result.update(geometry_sha256=digest,case_sha256=sha(path)); results.append(result)
    print(json.dumps(result),flush=True)
assert all(sha(p) == expected for p, expected in pins.items())
save(out/'execution.json',dict(source_sha256=sha(__file__),fragment_sha256=sha(fragment),commands=commands,
     base_inputs_sha256={str(p): expected for p, expected in pins.items()},inputs_unchanged=True,
     generated_program_sha256=sha(build/'Program.cs'),generated_project_sha256=sha(build/'Assembly935.csproj'),
     zero_closing_reproduces_original_STL_bytes=True,variants=results,elapsed_s=time.monotonic()-started,
     independent_surface_admission_pending=True,scale_verified=False,CFD_accepted=False,manufacturing_authorized=False))
