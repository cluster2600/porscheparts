"""Summarize completed centrifugal screening, retaining all stress peaks."""
import sys
import runpy
import numpy as np
import json
import hashlib
from pathlib import Path

p = Path(sys.argv[1])
assert "Job finished" in (p / "log.ccx").read_text()
stress = runpy.run_path(str(Path(__file__).resolve().parents[2] / "reference-917-engine/source/render_f36_structural_field.py"))["parse_element_stress"](p / "rotor.dat")
nodes, elements, mode = {}, {}, ""
for line in (p / "rotor.inp").read_text().splitlines():
    if line.startswith("*"):
        mode = "n" if line == "*NODE" else "e" if line.startswith("*ELEMENT,") else ""
    elif mode:
        fields = line.split(",")
        if mode == "n":
            nodes[int(fields[0])] = np.array(list(map(float, fields[1:])))
        else:
            elements[int(fields[0])] = list(map(int, fields[1:]))
disp, active = {}, False
for line in (p / "rotor.frd").read_text().splitlines():
    if line.startswith(" -4"):
        active = "DISP" in line
    if active and line.startswith(" -1"):
        disp[int(line[3:13])] = np.array([float(line[i:i+12]) for i in (13,25,37)])
assert set(stress) == set(elements) and set(disp) == set(nodes)
peak = max(stress, key=stress.get)
values = np.array(list(stress.values()))
blade_values = [s for e, s in stress.items()
                if np.linalg.norm(np.mean([nodes[i] for i in elements[e][:4]], axis=0)[:2]) > 82.5]
assert np.isfinite(values).all() and all(np.isfinite(d).all() for d in disp.values())
result = {"status":"linear_elastic_centrifugal_screen_only", "rpm":10000,
    "tetrahedra":len(elements), "von_mises_max_MPa":float(values.max()),
    "von_mises_p99_MPa":float(np.quantile(values,.99)),
    "blade_region_radius_above_82p5mm_max_MPa":max(blade_values),
    "peak_element_center_mm":np.mean([nodes[i] for i in elements[peak][:4]],axis=0).tolist(),
    "maximum_displacement_mm":max(float(np.linalg.norm(d)) for d in disp.values()),
    "maximum_radial_extension_mm":max(float(np.linalg.norm((nodes[i]+d)[:2])-np.linalg.norm(nodes[i][:2])) for i,d in disp.items()),
    "mesh_independence":False, "material_qualification_demonstrated":False,
    "manufacturing_authorized":False,
    "file_sha256":{name:hashlib.sha256((p/name).read_bytes()).hexdigest()
        for name in ['rotor.inp','rotor.dat','rotor.frd','log.ccx','log.gmsh','assumptions.json','surface-audit.json']}}
(p / "summary.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps(result,indent=2))
