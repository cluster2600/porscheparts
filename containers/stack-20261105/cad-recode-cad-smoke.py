"""Exercise CAD interchange and the packaged mechanical/thermal solver."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import cadquery as cq
import numpy as np
import trimesh

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    body = cq.Workplane('XY').box(10,20,30)
    cq.exporters.export(body,str(root/'box.step'))
    readback = cq.importers.importStep(str(root/'box.step')).val()
    assert readback.isValid()
    np.testing.assert_allclose(readback.Volume(),6000,rtol=0,atol=1e-6)
    mesh = trimesh.creation.box([10,20,30])
    assert mesh.is_watertight
    np.testing.assert_allclose(mesh.volume,6000,rtol=0,atol=1e-6)
    subprocess.run([sys.executable,'/opt/cad-recode/pipeline.py','--help'],check=True,stdout=subprocess.DEVNULL)
    subprocess.run([sys.executable,'/opt/cad-recode/ccx_smoke.py',str(root/'ccx')],check=True)
print(json.dumps({'status':'CAD_RECODE_CAD_STEP_AND_CCX_PASS','untrusted_generated_code_executed':False}))
