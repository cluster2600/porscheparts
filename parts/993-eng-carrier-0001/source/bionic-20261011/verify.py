"""Independent unit-cube solution for the actual Gmsh/CalculiX path."""
import json
import sys
from pathlib import Path

import gmsh
import numpy as np

from simulate import execute, nset, parse_dat, selfcheck


def verify(folder):
    selfcheck()
    folder.mkdir(parents=True, exist_ok=False)
    gmsh.initialize()
    try:
        gmsh.option.setNumber('General.Terminal', 0)
        gmsh.option.setNumber('General.NumThreads', 1)
        box = gmsh.model.occ.addBox(0, 0, 0, 1, 1, 1)
        gmsh.model.occ.synchronize()
        gmsh.model.addPhysicalGroup(3, [box], name='BODY')
        gmsh.option.setNumber('Mesh.MeshSizeMin', 0.4)
        gmsh.option.setNumber('Mesh.MeshSizeMax', 0.4)
        gmsh.option.setNumber('Mesh.ElementOrder', 2)
        gmsh.model.mesh.generate(3)
        tags, xyz, _ = gmsh.model.mesh.getNodes()
        order = np.argsort(tags); tags = tags[order]; xyz = xyz.reshape(-1, 3)[order]
        gmsh.write(str(folder/'mesh.inp'))
    finally:
        gmsh.finalize()
    lines = ['** One mm cube: analytical uniaxial extension',
             '*INCLUDE,INPUT=mesh.inp', '*MATERIAL,NAME=TEST', '*ELASTIC',
             '1000,0.25', '*SOLID SECTION,ELSET=BODY,MATERIAL=TEST']
    lines += nset('ALLN', tags)
    lines += ['*STEP', '*STATIC,SOLVER=SPOOLES', '*BOUNDARY']
    for dof in range(3):
        lines += [f'{node},{dof+1},{dof+1},0' for node in tags[abs(xyz[:, dof]) < 1e-9]]
    lines += [f'{node},1,1,0.001' for node in tags[abs(xyz[:, 0]-1) < 1e-9]]
    lines += ['*NODE PRINT,NSET=ALLN', 'U,RF', '*EL PRINT,ELSET=BODY', 'S', '*END STEP']
    (folder/'uniaxial.inp').write_text('\n'.join(lines)+'\n')
    seconds = execute(folder, 'uniaxial')
    values = parse_dat(folder/'uniaxial.dat')
    u = values['displacements']; s = values['stresses']; rf = values['forces']
    assert np.array_equal(u[:, 0].astype(int), tags)
    expected_u = xyz * [0.001, -0.00025, -0.00025]
    displacement_error = float(abs(u[:, 1:]-expected_u).max())
    stress_error = float(abs(s[:, 2:]-[1, 0, 0, 0, 0, 0]).max())
    right = abs(xyz[:, 0]-1) < 1e-9
    force_error = float(abs(rf[right, 1].sum()-1))
    assert displacement_error < 1e-8, displacement_error
    assert stress_error < 1e-5, stress_error
    assert force_error < 1e-5, force_error
    result = {'analytical_case': '1 mm cube, E=1000 MPa, nu=0.25, strain_x=0.001',
              'expected_stress_x_MPa': 1, 'expected_reaction_N': 1,
              'max_displacement_error_mm': displacement_error,
              'max_stress_error_MPa': stress_error, 'reaction_error_N': force_error,
              'seconds': seconds, 'passed': True}
    (folder/'verification.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    verify(Path(sys.argv[1]))
