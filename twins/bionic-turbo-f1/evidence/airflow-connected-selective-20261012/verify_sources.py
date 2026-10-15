"""Reproduce exact official source evidence for the mesh displacement control."""
import hashlib,json,tarfile
from pathlib import Path
w=Path(__file__).parent;reference=json.loads((w/'motion-source-reference.json').read_text());archive=Path('work/bionic-native-diagnostics-20261012/OpenFOAM-v2406.tgz')
assert hashlib.sha256(archive.read_bytes()).hexdigest()==reference['archive_sha256']
with tarfile.open(archive) as t:
 for item in reference['members']:
  data=t.extractfile(item['member']).read();assert hashlib.sha256(data).hexdigest()==item['sha256']
  assert (w/Path(item['member']).name).read_bytes()==data
parameters=(w/'snapParameters.C').read_text();header=(w/'snapParameters.H').read_text();driver=(w/'snappySnapDriver.C').read_text()
assert 'nSmoothDispl_\n    (\n        meshRefinement::get<label>(dict, "nSolveIter", dryRun)' in parameters
assert 'return nSmoothDispl_;' in header
assert 'iter < snapParams.nSmoothDispl()' in driver
start=driver.index('// Freeze points on exposed points/faces');tail=driver[start:]
assert tail.index('freezeExposedPoints')<tail.index('meshMover.setDisplacement(disp)')<tail.index('smoothDisplacement(snapParams, meshMover)')<tail.index('meshOk = scaleMesh')
result=dict(source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),all_member_bytes_verified=True,parameter_maps_to_mesh_displacement_loop=True,boundary_freeze_precedes_internal_smoothing=True,flow_solver_source_modified=False)
with (w/'source-readback.json').open('x') as f:json.dump(result,f,indent=2)
print(result)
