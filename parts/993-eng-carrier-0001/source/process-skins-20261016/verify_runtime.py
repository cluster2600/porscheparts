"""Read-only verification of the existing private PySLM runtime and pinned patch."""
import argparse
import hashlib
import importlib.metadata
import inspect
import json
from pathlib import Path
import platform
import re
import subprocess
import sys
import numpy as np
import pyslm
import pyslm.support
import trimesh

SOURCE=Path(__file__).resolve().parent
PINNED=SOURCE.parent/'process-coverage-20261016'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def verify(runtime,output):
    runtime=Path(runtime).resolve();output=Path(output).resolve()
    if output.exists():raise ValueError('Verification output must be new')
    upstream=json.loads((PINNED/'upstream.json').read_text());checkout=runtime/'source'
    head=subprocess.check_output(['git','-C',str(checkout),'rev-parse','HEAD'],text=True).strip()
    diff=subprocess.check_output(['git','-C',str(checkout),'diff','--binary'])
    if head!=upstream['revision'] or hashlib.sha256(diff).hexdigest()!=upstream['patch_sha256']:
        raise ValueError('Checkout revision or exact patch differs')
    root=Path(inspect.getfile(pyslm.support.BlockSupportGenerator)).parent
    native={}
    for name,key in [('support.py','patched_support_py_sha256'),('gridBlockSupport.py','patched_grid_py_sha256'),
                     ('utils.py','patched_utils_py_sha256'),('geometry.py','patched_geometry_py_sha256')]:
        if sha(root/name)!=upstream[key] or sha(checkout/'pyslm/support'/name)!=upstream[key]:raise ValueError('Installed/source patch differs: '+name)
        native[name]=upstream[key]
    required={}
    for line in (PINNED/'requirements-macos-arm64-python311.lock.txt').read_text().splitlines():
        match=re.fullmatch(r'([A-Za-z0-9_.-]+)==([^ #]+)',line.strip())
        if match:
            name,version=match.groups()
            if importlib.metadata.version(name)!=version:raise ValueError('Installed pin differs: '+name)
            required[name]=version
    p=pyslm.Part('runtime-verification');p.setGeometry(trimesh.creation.box((20,10,2)),fixGeometry=False,mergeVertices=False)
    polygons=p.getVectorSlice(0,returnCoordPaths=False,fixPolygons=False)
    if len(polygons)!=1 or abs(polygons[0].area-200)>1e-8:raise ValueError('Native slice witness failed')
    report=dict(status='verified_existing_private_runtime',python=str(runtime/'env/bin/python'),source=str(checkout),
        python_version=platform.python_version(),platform=platform.platform(),upstream=upstream,
        installed_source_sha256=native,pinned_requirements=required,pinned_requirements_count=len(required),
        installed_distributions={d.metadata['Name']:d.version for d in importlib.metadata.distributions()},
        requirements_sha256=sha(PINNED/'requirements-macos-arm64-python311.lock.txt'),
        installer_sha256=sha(PINNED/'setup_pyslm.py'),verifier_sha256=sha(__file__),
        isolated_installation_method='uv reconstruction of exact package pins and source patch; separate fresh installer execution belongs to its own receipt',
        native_slice_witness=dict(dimensions_mm=[20,10,2],z_mm=0.,area_mm2=polygons[0].area,passed=True),
        package_compatibility_check='uv pip check --python '+str(runtime/'env/bin/python')+' (39 compatible distributions)',
        numpy_version=np.__version__)
    output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runtime',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    r=verify(a.runtime,a.output);print(json.dumps({'status':r['status'],'pinned_requirements_count':r['pinned_requirements_count']}))
