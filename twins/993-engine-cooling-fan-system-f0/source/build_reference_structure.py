"""Run in a new case directory containing audited rotor-mm-analysis.stl.

Exploratory centrifugal screen only; bore restraint and material are assumptions.
"""
from pathlib import Path
import gmsh
import math
import json
import numpy as np

if any(Path(name).exists() for name in ("rotor.inp", "assumptions.json")):
    raise FileExistsError("Use a new directory to preserve structural runs")
# ponytail: fixed bore screening; replace with measured shaft contact before qualification.
gmsh.initialize()
gmsh.option.setNumber("General.NumThreads", 2)
gmsh.merge("rotor-mm-analysis.stl")
gmsh.option.setNumber("Mesh.MeshOnlyEmpty", 1)
surfaces = [tag for dim, tag in gmsh.model.getEntities(2)]
loop = gmsh.model.geo.addSurfaceLoop(surfaces)
volume = gmsh.model.geo.addVolume([loop])
gmsh.model.geo.synchronize()
gmsh.model.addPhysicalGroup(3, [volume], 1)
gmsh.model.setPhysicalName(3, 1, "ROTOR")
gmsh.option.setNumber("Mesh.MeshSizeMin", .7)
gmsh.option.setNumber("Mesh.MeshSizeMax", 4.5)
gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 24)
gmsh.option.setNumber("Mesh.Algorithm3D", 10)
gmsh.option.setNumber("Mesh.OptimizeThreshold", .1)
gmsh.option.setNumber("Mesh.Optimize", 0)
gmsh.model.mesh.generate(3)
gmsh.model.mesh.optimize("")
gmsh.model.mesh.setOrder(2)
points, _ = gmsh.model.mesh.getIntegrationPoints(11, "Gauss2")
_, determinants, _ = gmsh.model.mesh.getJacobians(11, points)
assert np.isfinite(determinants).all() and min(determinants) > 0
print("MINIMUM_JACOBIAN", min(determinants))
gmsh.write("rotor.inp")
tags, xyz, _ = gmsh.model.mesh.getNodes()
xyz = np.asarray(xyz).reshape(-1, 3)
fixed = tags[(np.hypot(xyz[:, 0], xyz[:, 1]) < 17.35)]
assert len(fixed) > 20
element_types, element_tags, _ = gmsh.model.mesh.getElements(3)
assert list(element_types) == [11]
print("QUADRATIC_TETS", len(element_tags[0]), "NODES", len(tags), "BORE_FIXED_NODES", len(fixed))
gmsh.finalize()
with open("rotor.inp", "a") as f:
    f.write("\n*NSET,NSET=BORE\n")
    for start in range(0, len(fixed), 12):
        f.write(",".join(str(n) for n in fixed[start:start+12]) + "\n")
    f.write("*MATERIAL,NAME=AL_ASSUMED\n*ELASTIC\n70000,0.33\n*DENSITY\n2.67e-9\n")
    f.write("*SOLID SECTION,ELSET=ROTOR,MATERIAL=AL_ASSUMED\n")
    f.write("*BOUNDARY\nBORE,1,3\n*STEP\n*STATIC\n*DLOAD\n")
    f.write(f"ROTOR,CENTRIF,{(10000*math.pi/30)**2},0,0,0,0,0,1\n")
    f.write("*NODE FILE\nU\n*EL FILE\nS\n*EL PRINT,ELSET=ROTOR\nS\n*END STEP\n")
with open("assumptions.json", "w") as f:
    json.dump({"purpose":"centrifugal_screening_only", "rpm":10000,
        "rpm_is_design_scenario_not_verified_engine_limit":True,
        "units":"mm,N,s,tonne", "E_MPa_assumed":70000,"poisson_assumed":.33,
        "density_tonne_mm3":2.67e-9,"boundary":"all translations fixed at r < 17.35 mm on hypothetical 34 mm bore; no bearing/contact model",
        "thermal_aerodynamic_fatigue_and_resonance_not_included":True,
        "quadratic_tetrahedra":len(element_tags[0]),"nodes":len(tags)},f,indent=2)
