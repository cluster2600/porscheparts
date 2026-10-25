"""Restore the original physical names after MMG, without modifying its geometry."""
import argparse
import json
from pathlib import Path

from mesh_surface import quality_passes,sha


def physical_names(surfaces,volumes):
    if set(surfaces)!={101,102,103} or set(volumes)!={1}:
        raise ValueError('MMG changed the expected surface or volume references')
    return ((2,101,'inlet'),(2,102,'outlet'),(2,103,'walls'),(3,1,'coolant'))


def convert(parent,medit,expected,output):
    record=json.loads((parent/'mesh-report.json').read_text())
    audit=json.loads((parent/'saved-readback.json').read_text())
    if sha(parent/'coolant.msh')!=record['mesh_sha256'] or record['mesh_sha256']!=audit['mesh_sha256']:
        raise ValueError('Parent mesh changed')
    if sha(medit)!=expected:raise ValueError('MMG transfer hash mismatch')
    if output.exists():raise ValueError('Output must be new')
    import gmsh
    import numpy as np
    gmsh.initialize([])
    try:
        gmsh.option.setNumber('General.Terminal',0);gmsh.open(str(medit))
        names=physical_names([tag for dim,tag in gmsh.model.getEntities(2)],
                             [tag for dim,tag in gmsh.model.getEntities(3)])
        if list(gmsh.model.mesh.getElementTypes(3))!=[4]:raise ValueError('Expected linear tetrahedra')
        for dim,tag,name in names:gmsh.model.addPhysicalGroup(dim,[tag],tag,name)
        tags=gmsh.model.mesh.getElements(3)[1][0]
        q=np.asarray(gmsh.model.mesh.getElementQualities(tags,'minSICN'))
        v=np.asarray(gmsh.model.mesh.getElementQualities(tags,'volume'))*1e9
        output.mkdir(parents=True)
        gmsh.option.setNumber('Mesh.MshFileVersion',2.2);gmsh.option.setNumber('Mesh.Binary',0)
        gmsh.write(str(output/'coolant.msh'))
        report=dict(status='mmg_candidate_requires_independent_readback_and_checkMesh',
            source_sha256=sha(Path(__file__)),parent_receipt_sha256=sha(parent/'mesh-report.json'),
            parent_mesh_sha256=record['mesh_sha256'],medit_sha256=expected,
            surface_receipt_sha256=record['surface_receipt_sha256'],gmsh_version=gmsh.__version__,
            cells=len(tags),minimum_sicn=float(q.min()),below_sicn_01=int(np.count_nonzero(q<.1)),
            minimum_volume_mm3=float(v.min()),volume_mm3=float(v.sum()),
            volume_quality_passed=quality_passes(q,v),mesh_coordinates='m',
            mesh_sha256=sha(output/'coolant.msh'),openfoam_mesh_accepted=False,
            hydraulic_performance_validated=False,manufacturing_authorized=False)
        (output/'mesh-report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
        print(json.dumps(report,indent=2),flush=True)
    finally:gmsh.finalize()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('parent',type=Path);parser.add_argument('medit',type=Path)
    parser.add_argument('expected_sha256');parser.add_argument('output',type=Path)
    a=parser.parse_args();convert(a.parent.resolve(),a.medit.resolve(),a.expected_sha256,a.output.resolve())
