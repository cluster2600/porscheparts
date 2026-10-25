"""Reconstruct finished processor meshes into a fresh case with Foundation 13's actual utility."""
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import time

phase = Path('/home/lolman/935-snap-resume-20261025'); source = phase/'parallel-snap-001'
out = phase/'reconstructed-snap-002'
sha = lambda p: hashlib.file_digest(Path(p).open('rb'), 'sha256').hexdigest()
parent = json.loads((source/'execution.json').read_text())
assert parent['exit'] == 0 and parent['stop_reason'] is None and parent['parent_checkpoint_unchanged']
assert parent['source_sha256'] == '1e3785d550fdccf4aa34739ddc464315a0e136b6491ffb545a4df79b094cd079'
assert 'superseded and replaced' in (source/'log.reconstruct').read_text()
assert subprocess.run(['pgrep','-x','snappyHexMesh'], stdout=subprocess.DEVNULL).returncode == 1
control = phase/'reconstruct-qualification-001/cube-002/assessment.json'
proof = json.loads(control.read_text())
assert proof['source_sha256'] == 'c6073543cf12c7b5f1d151292a2864a2e2d2d7200e1fee275a556414888486f6'
assert proof['every_reconstructed_coordinate_exact'] and proof['native_full_quality_passed']
assert not proof['legacy_command_wrote_mesh'] and not proof['original_global_mesh_copied'] and not proof['parent_processor_addressing_copied']
assert not out.exists(); out.mkdir(mode=0o700)
inputs = [f for rank in range(4) for f in (source/f'processor{rank}').rglob('*') if f.is_file()]
inputs += [f for folder in ['system','constant/triSurface'] for f in (source/folder).rglob('*') if f.is_file()]
before = {str(f.relative_to(source)): sha(f) for f in inputs}
shutil.copytree(source/'system',out/'system'); (out/'constant').mkdir()
shutil.copytree(source/'constant/triSurface',out/'constant/triSurface')
for rank in range(4):
    shutil.copytree(source/f'processor{rank}',out/f'processor{rank}',ignore=shutil.ignore_patterns('*ProcAddressing'))
(out/'constant/polyMesh').mkdir()
edge = source/'processor0/constant/polyMesh/level0Edge'
assert all(sha(source/f'processor{rank}/constant/polyMesh/level0Edge') == sha(edge) for rank in range(4))
shutil.copyfile(edge,out/'constant/polyMesh/level0Edge')
assert not any((out/'constant/polyMesh'/name).exists() for name in ['points','faces','owner','neighbour','boundary'])
assert all(sha(out/name) == expected for name, expected in before.items() if not name.endswith('ProcAddressing'))
assert sha(out/'system/meshQualityDict') == 'bafbc5ced7e83c5a1cc11291a0937c3499a6713e8e3411a83f93464381ba2c7d'
pre = Path('/home/lolman/935-conforming-20261022/rootless-cfd-preflight-002/receipt.json')
assert sha(pre) == '1e6f331b419c3849d6321beeff39b64a5f21407dbec778a4016629f8e27a563d'
command = list(json.loads(pre.read_text())['command']); command[command.index('--bind')+1] = str(out)
assert '--unshare-all' in command and '--share-net' not in command
command[-1] = '''source /opt/openfoam13/etc/bashrc >/dev/null 2>&1
set -euo pipefail
reconstructPar -case /workspace -constant -noFields -noSets -noLagrangian > /workspace/log.reconstruct 2>&1
checkMesh -case /workspace -allGeometry -allTopology -meshQuality > /workspace/log.checkMesh.allGeometry 2>&1
'''


def limits():
    resource.setrlimit(resource.RLIMIT_AS,(12*1024**3,12*1024**3))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    resource.setrlimit(resource.RLIMIT_FSIZE,(2*1024**3,2*1024**3))


started = time.monotonic(); reason = None
with (out/'runtime.log').open('x') as log:
    process = subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,preexec_fn=limits,start_new_session=True)
    try: code = process.wait(timeout=900)
    except subprocess.TimeoutExpired:
        reason = 'wall_time_limit'; os.killpg(process.pid,signal.SIGTERM)
        try: process.wait(timeout=10)
        except subprocess.TimeoutExpired: os.killpg(process.pid,signal.SIGKILL); process.wait()
        code = process.returncode
quality = (out/'log.checkMesh.allGeometry').read_text() if (out/'log.checkMesh.allGeometry').exists() else ''
unchanged = all(sha(source/name) == expected for name, expected in before.items())
mesh = out/'constant/polyMesh'
files = {name: sha(mesh/name) for name in ['points','faces','owner','neighbour','boundary'] if (mesh/name).exists()}
record = dict(source_sha256=sha(__file__), parent_execution_sha256=sha(source/'execution.json'),
              moved_cube_qualification_sha256=sha(control), processor_inputs_sha256=before,
              original_global_mesh_copied=False, stale_processor_addressing_copied=False,
              processor_inputs_exact_before_reconstruction=True, source_unchanged=unchanged,
              exit=code,stop_reason=reason,elapsed_s=time.monotonic()-started,timeout_s=900,
              actual_reconstruction_utility='reconstructPar', level0Edge_reference_sha256=sha(edge),native_mesh_sha256=files,
              extended_native_quality_passed='Mesh OK.' in quality and 'Failed' not in quality,
              complete_point_union_readback_pending=True, complete_wall_and_volume_admission_pending=True,
              boundary_layers_executed=False,CFD_executed=False,CFD_accepted=False,manufacturing_authorized=False)
(out/'execution.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record),flush=True)
assert unchanged
raise SystemExit(0 if code == 0 else 1)
