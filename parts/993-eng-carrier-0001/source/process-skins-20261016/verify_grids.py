"""Native grid/contact witnesses, including triangles bridging an opening or Z gap."""
import argparse
import hashlib
import inspect
import json
from pathlib import Path
import shutil
import numpy as np
import pyslm.support
import shapely
from shapely.geometry import Polygon
import trimesh
from grid_intervals import trim_and_admit

SOURCE=Path(__file__).resolve().parent

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def verify(output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False);(output/'source').mkdir()
    sources=[SOURCE/name for name in ['verify_grids.py','grid_intervals.py']]
    frozen={str(p):digest(p) for p in sources}
    for p in sources:shutil.copy2(p,output/'source'/p.name)
    runtime=[Path(inspect.getfile(pyslm.support.GridBlockSupport)),
             Path(inspect.getfile(pyslm.support.geometry.extrudeFace))]
    native_hashes={str(p):digest(p) for p in runtime}
    rectangle=Polygon([(0,0),(30,0),(30,20),(0,20)])
    holey=Polygon([(0,0),(40,0),(40,30),(0,30)],holes=[[(11,11),(11,21),(21,21),(21,11)]])
    a=trimesh.creation.extrude_polygon(rectangle,10);b=a.copy();b.apply_translation([0,0,20])
    cases=[('box',a,None),('inner-opening',trimesh.creation.extrude_polygon(holey,10),(15.,10.,22.,4.,6.)),
           ('two-Z-intervals',trimesh.util.concatenate([a,b]),None)]
    rows=[]
    for name,volume,bridge in cases:
        block=pyslm.support.GridBlockSupport(supportVolume=volume)
        block.gridSpacing=[5,5];block.supportWallThickness=1;block.supportTeethBaseInterval=1.5
        block.useLowerSupportTeeth=True;block.useUpperSupportTeeth=True
        grids=block.generateSupportSlices();generated=[];audits=[]
        for axis,grid in enumerate(grids):
            if axis==0 and bridge:
                x,y0,y1,z0,z1=bridge
                identity=next(int(o) for o in np.unique(grid.face_attributes['order'])
                    if grid.triangles[np.flatnonzero(grid.face_attributes['order']==o)[0],0,0]==x)
                kind=int(grid.face_attributes['type'][np.flatnonzero(grid.face_attributes['order']==identity)[0]])
                bad=trimesh.Trimesh([[x,y0,z0],[x,y1,z0],[x,y1,z1],[x,y0,z1]],[[0,1,2],[0,2,3]],process=False)
                bad.face_attributes['order']=np.full(2,identity);bad.face_attributes['type']=np.full(2,kind)
                grid=block.concatenateMeshes([grid,bad])
            mesh,receipt=trim_and_admit(volume,grid,axis,.2)
            assert receipt['expected_planes']==receipt['generated_planes']
            assert all(row['whole_surface_outside_admitted_domain_area_mm2']==0 and
                all(item['passed'] for item in row['contacts']) for row in receipt['planes'])
            generated.append(mesh);audits.append(receipt)
        trimmed=sum(row['explicitly_trimmed_area_mm2'] for audit in audits for row in audit['planes'])
        if bridge:assert trimmed>9.
        if name=='two-Z-intervals':
            for mesh in generated:
                assert not np.any((mesh.vertices[:,2]>10.200000001)&(mesh.vertices[:,2]<19.799999999))
        mesh=block.concatenateMeshes(generated)
        mesh.export(output/(name+'-grids.stl'));volume.export(output/(name+'-envelope.stl'))
        rows.append(dict(name=name,status='passed',injected_invalid_bridge=bool(bridge),
            explicitly_removed_area_mm2=trimmed,grid_area_mm2=mesh.area,axes=audits))
    # A bridge crossing the solid Z gap leaves two one-ended, disconnected
    # fragments after clipping. The other grid family is at y=0,5,10,15:
    # no other sheet crosses the injected y in [2,3]. It must remain rejected.
    volume=cases[2][1];block=pyslm.support.GridBlockSupport(supportVolume=volume);block.gridSpacing=[5,5]
    block.supportWallThickness=1;block.supportTeethBaseInterval=1.5
    block.useLowerSupportTeeth=True;block.useUpperSupportTeeth=True
    native=block.generateSupportSlices()[0]
    order=next(int(o) for o in np.unique(native.face_attributes['order'])
        if native.triangles[np.flatnonzero(native.face_attributes['order']==o)[0],0,0]==5.)
    bridge=trimesh.Trimesh([[5,2,9],[5,3,9],[5,3,21],[5,2,21]],[[0,1,2],[0,2,3]],process=False)
    bridge.face_attributes['order']=np.full(2,order);bridge.face_attributes['type']=np.zeros(2,dtype=int)
    try:trim_and_admit(volume,block.concatenateMeshes([native,bridge]),0,.2)
    except ValueError as error:
        negative=getattr(error,'receipt',None)
        assert negative and not all(row['passed'] for row in negative['contacts'])
    else:raise AssertionError('One-ended isolated fragments were admitted')
    assert all(digest(p)==sha for p,sha in {**frozen,**native_hashes}.items())
    report=dict(status='passed',source_sha256=frozen,runtime_source_sha256=native_hashes,
        source_and_runtime_unchanged=True,cases=rows,negative_isolated_bridge=negative)
    (output/'assessment.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path)
    report=verify(parser.parse_args().output);print(json.dumps({'status':report['status'],'cases':len(report['cases'])}))
