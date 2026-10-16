"""Run independent geometry/contact witnesses before processing a carrier."""
import argparse
import hashlib
import inspect
import json
from pathlib import Path
import shutil
import numpy as np
import shapely
from shapely.geometry import Polygon
import trimesh
import pyslm.support
from pyslm.support.geometry import boolDiff
from peripheral_skins import generate
from prismatic_envelopes import projected_prism_union

SOURCE=Path(__file__).resolve().parent

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def verify(output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False);(output/'source').mkdir()
    sources=[SOURCE/name for name in ['verify_skins.py','peripheral_skins.py','prismatic_envelopes.py','exact_regions.py','grid_intervals.py']]
    frozen={str(p):digest(p) for p in sources}
    for p in sources:shutil.copy2(p,output/'source'/p.name)
    runtime=[Path(inspect.getfile(pyslm.support.GridBlockSupport)),Path(inspect.getfile(pyslm.support.geometry.extrudeFace))]
    native_hashes={str(p):digest(p) for p in runtime}
    rectangle=Polygon([(0,0),(30,0),(30,20),(0,20)])
    holey=Polygon([(0,0),(40,0),(40,30),(0,30)],holes=[[(10,10),(10,20),(20,20),(20,10)]])
    a=trimesh.creation.extrude_polygon(rectangle,10);b=a.copy();b.apply_translation([0,0,20])
    xy=np.array([[0.,0.],[20.,0.],[0.,20.]])
    triangles=trimesh.Trimesh(np.vstack([np.column_stack([xy,np.full(3,z)]) for z in [10.,20.]]),[[0,1,2],[3,4,5]],process=False)
    union,prism_receipt=projected_prism_union(triangles)
    solid=trimesh.creation.box((60,60,4));solid.apply_translation([0,0,10]);free=boolDiff(union,solid)
    assert abs(union.volume-4000)<1e-8 and abs(free.volume-3200)<1e-8
    cases=[('box',a,rectangle,[0,10],1),('inner-opening',trimesh.creation.extrude_polygon(holey,10),holey,[0,10],2),
           ('two-Z-intervals',trimesh.util.concatenate([a,b]),rectangle,[0,10,20,30],2),
           ('multi-height-prisms',free,Polygon(xy),[0,8,12,20],2)]
    rows=[]
    for name,volume,footprint,interfaces,expected in cases:
        identity=hashlib.sha256(volume.vertices.tobytes()+volume.faces.tobytes()).hexdigest()
        block=pyslm.support.GridBlockSupport(supportVolume=volume)
        block.gridSpacing=[5,5];block.supportWallThickness=1;block.supportTeethBaseInterval=1.5
        block.useLowerSupportTeeth=True;block.useUpperSupportTeeth=True
        meshes,receipt=generate(block);skin=trimesh.util.concatenate(meshes)
        assert len(meshes)==expected==receipt['generated_vertical_components']==receipt['expected_vertical_components']
        assert identity==hashlib.sha256(volume.vertices.tobytes()+volume.faces.tobytes()).hexdigest()
        xy_error=float(shapely.distance(shapely.points(skin.vertices[:,:2]),footprint.boundary).max())
        assert xy_error<1e-9
        assert np.isfinite(skin.vertices).all() and skin.area>0
        contacts=[]
        for z in interfaces:
            lines=trimesh.intersections.mesh_plane(skin,[0,0,1],[0,0,z])
            length=float(np.linalg.norm(np.diff(lines,axis=1),axis=2).sum());assert length>0
            contacts.append(dict(z_mm=z,segments=len(lines),trace_length_mm=length))
        for low,high in zip(interfaces[1::2],interfaces[2::2]):
            for z in np.linspace(low+.21,high-.21,3):
                assert len(trimesh.intersections.mesh_plane(skin,[0,0,1],[0,0,z]))==0
        assert skin.bounds[0,2]>=interfaces[0]-.200000001 and skin.bounds[1,2]<=interfaces[-1]+.200000001
        for item in receipt['components']:
            assert abs(item['unfolding']['source_vertical_area_mm2']-item['unfolding']['unfolded_domain_area_mm2'])<1e-8
            assert item['unfolding']['source_coordinate_roundtrip_max_mm']<1e-9
            assert item['infill']['outside_free_domain_and_contact_band_area_mm2']==0
        skin.export(output/(name+'-skins.stl'));volume.export(output/(name+'-envelope.stl'))
        rows.append(dict(name=name,receipt=receipt,source_volume_mm3=volume.volume,
            source_geometry_unchanged=True,source_mesh_sha256=identity,
            skin_area_mm2=skin.area,XY_reference_boundary_max_error_mm=xy_error,
            contacts=contacts,bounds_mm=skin.bounds.tolist(),
            tooth_parameters_mm={name:getattr(block,name) for name in ['supportTeethHeight','supportTeethTopLength',
                'supportTeethBottomLength','supportTeethBaseInterval','supportTeethUpperPenetration']}))
    assert all(digest(p)==sha for p,sha in {**frozen,**native_hashes}.items())
    report=dict(status='passed',source_sha256=frozen,runtime_source_sha256=native_hashes,
                source_and_runtime_unchanged=True,prism_union_witness=prism_receipt,cases=rows)
    (output/'assessment.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path)
    report=verify(parser.parse_args().output);print(json.dumps({'status':report['status'],'cases':len(report['cases'])}))
