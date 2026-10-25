"""Catch the Foundation 13 legacy no-op and qualify actual reconstruction of moved points."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import numpy as np

sha = lambda p: hashlib.file_digest(Path(p).open('rb'), 'sha256').hexdigest()
source = Path('/home/lolman/935-local-relocation-20261022/parallel-cube-001')
out = Path('/home/lolman/935-snap-resume-20261025/reconstruct-qualification-001/cube-002')
assert not out.exists(); out.mkdir(mode=0o700)
originals = {str(f.relative_to(source)): sha(f) for f in source.rglob('*') if f.is_file()}


def points(path):
    text = path.read_text()
    match = re.fullmatch(r'.*?FoamFile\s*\{[^{}]*\}\s*(\d+)\s*\((.*)\)\s*',
                         re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.S), re.S)
    if not match or not 0 < int(match[1]) <= 1000: raise ValueError('Bounded analytic point list required')
    values = np.fromstring(match[2].replace('(', ' ').replace(')', ' '), sep=' ').reshape(-1, 3)
    if values.shape != (int(match[1]), 3) or not np.isfinite(values).all(): raise ValueError('Complete finite points required')
    return values


reference = points(source/'constant/polyMesh/points') + [.125, 0, 0]
assert reference.shape == (343, 3)
shutil.copytree(source/'system', out/'system')
for rank in range(4):
    shutil.copytree(source/f'processor{rank}', out/f'processor{rank}')
    for stale in (out/f'processor{rank}/constant/polyMesh').glob('*ProcAddressing'): stale.unlink()
    path = out/f'processor{rank}/constant/polyMesh/points'
    moved = points(path) + [.125, 0, 0]
    with path.open('w') as stream:
        stream.write(f'FoamFile {{format ascii;class vectorField;object points;}}\n{len(moved)}\n(\n')
        np.savetxt(stream, moved, fmt='(%.17g %.17g %.17g)'); stream.write(')\n')
(out/'constant').mkdir()
pre = Path('/home/lolman/935-conforming-20261022/rootless-cfd-preflight-002/receipt.json')
assert sha(pre) == '1e6f331b419c3849d6321beeff39b64a5f21407dbec778a4016629f8e27a563d'
command = list(json.loads(pre.read_text())['command']); command[command.index('--bind')+1] = str(out)
assert '--unshare-all' in command and '--share-net' not in command
prefix = 'source /opt/openfoam13/etc/bashrc >/dev/null 2>&1\nset -euo pipefail\n'
command[-1] = prefix+'reconstructParMesh -case /workspace -constant > /workspace/log.legacy 2>&1\n'
legacy = subprocess.run(command, capture_output=True, text=True, timeout=30)
legacy_wrote_mesh = (out/'constant/polyMesh/points').exists()
assert legacy.returncode == 0 and not legacy_wrote_mesh
command[-1] = prefix+'''reconstructPar -case /workspace -constant -noFields -noSets -noLagrangian > /workspace/log.reconstruct 2>&1
checkMesh -case /workspace -allGeometry -allTopology -meshQuality > /workspace/log.checkMesh 2>&1
'''
current = subprocess.run(command, capture_output=True, text=True, timeout=60)
assert current.returncode == 0
actual = points(out/'constant/polyMesh/points')
order = lambda a: a[np.lexsort((a[:, 2], a[:, 1], a[:, 0]))]
assert np.array_equal(order(actual), order(reference))
quality = (out/'log.checkMesh').read_text(); assert 'Mesh OK.' in quality and 'Failed' not in quality
assert all(sha(source/name) == expected for name, expected in originals.items())
record = dict(source_sha256=sha(__file__), Foundation13_legacy_command_exit=legacy.returncode,
              legacy_command_wrote_mesh=legacy_wrote_mesh, original_global_mesh_copied=False, parent_processor_addressing_copied=False,
              current_command_exit=current.returncode, reconstructed_points=len(actual),
              translation_source_units=[.125, 0, 0], every_reconstructed_coordinate_exact=True,
              native_full_quality_passed=True, source_cube_unchanged=True,
              reconstructed_points_sha256=sha(out/'constant/polyMesh/points'),
              legacy_log_sha256=sha(out/'log.legacy'), reconstruction_log_sha256=sha(out/'log.reconstruct'),
              check_log_sha256=sha(out/'log.checkMesh'), network_isolation_unchanged=True,
              CFD_accepted=False, manufacturing_authorized=False)
(out/'assessment.json').write_text(json.dumps(record, indent=2)+'\n'); print(json.dumps(record), flush=True)
