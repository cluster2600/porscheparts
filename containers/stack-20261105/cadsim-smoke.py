"""Independent-kernel STEP readback on an analytically dimensioned fixture."""
import importlib
import json
from importlib.metadata import version
from pathlib import Path
import subprocess
import tempfile

from build123d import Box, export_step

for module in ("gmsh", "meshio", "pyvista", "trimesh", "manifold3d",
               "numpy", "scipy", "foamlib", "shapely", "rtree", "networkx"):
    importlib.import_module(module)
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / "box.step"
    box = Box(10, 20, 30)
    assert abs(box.volume - 6000) < 1e-6
    export_step(box, path)
    code = "import cadquery as cq,sys; v=cq.importers.importStep(sys.argv[1]).val().Volume(); assert abs(v-6000)<1e-6; print(v)"
    readback = subprocess.run(["/opt/cadquery/bin/python", "-c", code, str(path)],
                              check=True, capture_output=True, text=True, timeout=90)
print(json.dumps({"status": "passed", "scope": "synthetic_step_interoperability",
                  "build123d": version("build123d"), "expected_volume_mm3": 6000,
                  "cadquery_readback_volume_mm3": float(readback.stdout.strip()),
                  "physical_qualification": False}))
