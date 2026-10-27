"""Independently screen a locally remeshed MMG boundary before binding it to the volume."""
import argparse
import json
from pathlib import Path
import shutil

from import_mmg import convert
from mesh_surface import sha
from prepare_surface import inspect as inspect_surface
from read_saved import inspect as inspect_volume


def exchange(parent,medit,expected,native,native_sha,output):
    if sha(native)!=native_sha:raise ValueError('Native master changed')
    if output.exists():raise ValueError('Output must be new')
    output.mkdir(parents=True)
    imported=output/'imported';convert(parent,medit,expected,imported)
    import gmsh
    import numpy as np
    import trimesh
    surface=output/'surface';surface.mkdir()
    gmsh.initialize([])
    try:
        gmsh.option.setNumber('General.Terminal',0);gmsh.open(str(imported/'coolant.msh'))
        tags,x,_=gmsh.model.mesh.getNodes();order=np.argsort(tags);tags=np.asarray(tags)[order]
        x=np.asarray(x).reshape(-1,3)[order]*1000
        types,_,conn=gmsh.model.mesh.getElements(2)
        if list(types)!=[2]:raise ValueError('Linear boundary triangles required')
        faces=np.searchsorted(tags,np.asarray(conn[0]).reshape(-1,3))
        mesh=trimesh.Trimesh(vertices=x,faces=faces,process=False)
        (surface/'coolant.stl').write_text(trimesh.exchange.stl.export_stl_ascii(mesh))
    finally:gmsh.finalize()
    record=dict(status='mmg_surface_awaiting_independent_checks',source_sha256=native_sha,
        candidate_sha256=sha(surface/'coolant.stl'),exchange_source_sha256=sha(Path(__file__)),
        volume_source_sha256=sha(imported/'coolant.msh'),manufacturing_authorized=False)
    (surface/'native-report.json').write_text(json.dumps(record,indent=2)+'\n')
    checked=inspect_surface(native,surface/'coolant.stl',surface)
    if checked['geometry_admitted'] is not True:raise ValueError('Remeshed boundary rejected')
    volume=output/'volume';volume.mkdir();shutil.copy2(imported/'coolant.msh',volume/'coolant.msh')
    bound=json.loads((imported/'mesh-report.json').read_text())
    bound.update(status='mmg_volume_with_independently_screened_new_boundary',
        unbound_import_receipt_sha256=sha(imported/'mesh-report.json'),
        exchange_source_sha256=sha(Path(__file__)),surface_receipt_sha256=sha(surface/'surface-report.json'))
    (volume/'mesh-report.json').write_text(json.dumps(bound,indent=2)+'\n')
    inspect_volume(surface,volume)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('parent',type=Path);p.add_argument('medit',type=Path);p.add_argument('expected_sha256')
    p.add_argument('native',type=Path);p.add_argument('native_sha256');p.add_argument('output',type=Path)
    a=p.parse_args();exchange(a.parent.resolve(),a.medit.resolve(),a.expected_sha256,a.native.resolve(),a.native_sha256,a.output.resolve())
