"""Freeze real prism-chain/XY-mask/full-part inputs for exact native CSG operations."""
import argparse
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import shutil
import numpy as np
import pyslm
import pyslm.support
import shapely
import trimesh
from prismatic_envelopes import prism_boundary_chain,reduce_exact_horizontal_patches
from exact_regions import polygon_parts

SOURCE=Path(__file__).resolve().parent
CORE=SOURCE.parent/'process-coverage-20261016/build_pyslm.py'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def prepare(input_path,output,expected_sha256,reduce_horizontal=False,unreduced_sources=()):
    input_path=Path(input_path).resolve();output=Path(output).resolve()
    if sha(input_path)!=expected_sha256:raise ValueError('Input SHA-256 mismatch')
    output.mkdir(parents=True,exist_ok=False);(output/'source').mkdir()
    spec=importlib.util.spec_from_file_location('carrier_part_input',CORE);core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
    files=[Path(__file__).resolve(),CORE,SOURCE/'prismatic_envelopes.py',SOURCE/'exact_regions.py',
        Path(inspect.getfile(pyslm.support.utils.getOverhangMesh)),Path(inspect.getfile(pyslm.support.geometry.extrudeFace))]
    hashes={str(p):sha(p) for p in files}
    for i,p in enumerate(files):shutil.copy2(p,output/'source'/f'{i:02d}-{p.name}')
    part=pyslm.Part('carrier');part.setGeometry(core.exact_mesh(input_path),fixGeometry=False,mergeVertices=False)
    part.rotation=core.PARAMETERS['rotation_degrees_xyz'];part.dropToPlatform(core.PARAMETERS['support_gap_mm'])
    np.savez_compressed(output/'part.npz',vertices=part.geometry.vertices,faces=part.geometry.faces)
    generator=pyslm.support.GridBlockSupportGenerator();sources=pyslm.support.utils.getOverhangMesh(part,core.PARAMETERS['overhang_angle_degrees'],True)
    rows=[];exclusions=[]
    for i,source in enumerate(sources):
        projection=shapely.union_all(shapely.polygons(source.triangles[:,:,:2]));mask=projection.buffer(-generator.outerSupportEdgeGap)
        retained=[]
        for j,polygon in enumerate(polygon_parts(mask)):
            if polygon.area<generator.minimumAreaThreshold:
                exclusions.append(dict(source_index=i,polygon_index=j,area_mm2=polygon.area,reason='configured_minimum_projected_area'))
            else:retained.append((j,polygon))
        if not retained:
            exclusions.append(dict(source_index=i,projected_area_mm2=projection.area,buffered_area_mm2=mask.area,reason='no_retained_polygon'))
            continue
        if reduce_horizontal and i not in unreduced_sources:reduced,reduction=reduce_exact_horizontal_patches(source)
        else:reduced=source;reduction=None
        chain,chain_receipt=prism_boundary_chain(reduced)
        chain_name=f'source-{i:03d}-chain.npz';np.savez_compressed(output/chain_name,vertices=chain.vertices,faces=chain.faces)
        for j,polygon in retained:
            triangles=shapely.get_parts(shapely.constrained_delaunay_triangles(polygon))
            points=np.asarray([np.asarray(t.exterior.coords)[:3] for t in triangles]);xy,inverse=np.unique(points.reshape(-1,2),axis=0,return_inverse=True)
            area_error=polygon.symmetric_difference(shapely.union_all(triangles)).area
            if area_error!=0:raise ValueError('Mask triangulation changed the domain')
            height=float(part.geometry.bounds[1,2]+generator.upperProjectionOffset)
            plane=trimesh.Trimesh(np.column_stack([xy,np.full(len(xy),height)]),inverse.reshape(-1,3),process=False)
            volume=pyslm.support.geometry.extrudeFace(plane,height=0.)
            if not volume.is_watertight or not volume.is_winding_consistent or volume.volume<=0:raise ValueError('Invalid clip mask')
            mask_name=f'source-{i:03d}-mask-{j:03d}.npz';np.savez_compressed(output/mask_name,vertices=volume.vertices,faces=volume.faces)
            rows.append(dict(index=len(rows),source_index=i,source_polygon_index=j,source_triangles=len(source.faces),
                projected_area_mm2=polygon.area,bounds_xy_mm=list(polygon.bounds),source_projected_area_mm2=projection.area,
                edge_gap_excluded_area_mm2=projection.difference(mask).area,chain=chain_name,chain_sha256=sha(output/chain_name),
                mask=mask_name,mask_sha256=sha(output/mask_name),mask_triangles=len(volume.faces),
                mask_symmetric_difference_area_mm2=area_error,chain_receipt=chain_receipt,horizontal_reduction=reduction))
            print(json.dumps(dict(region=len(rows)-1,source=i,chain_triangles=len(chain.faces),mask_triangles=len(volume.faces))),flush=True)
    if sha(input_path)!=expected_sha256 or any(sha(p)!=digest for p,digest in hashes.items()):raise ValueError('Source/input changed')
    report=dict(status='inputs_frozen_not_admitted_envelopes',input=str(input_path),input_sha256=expected_sha256,
        part='part.npz',part_sha256=sha(output/'part.npz'),parameters=core.PARAMETERS,
        edge_gap_mm=generator.outerSupportEdgeGap,minimum_projected_area_mm2=generator.minimumAreaThreshold,
        source_sha256=hashes,sources_and_input_unchanged=True,expected_regions=len(rows),overhang_source_regions=len(sources),
        horizontal_reduction_enabled=bool(reduce_horizontal),unreduced_source_indices=list(unreduced_sources),
        regions=rows,configured_area_exclusions=exclusions)
    (output/'inputs.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('input',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--sha256',required=True);p.add_argument('--reduce-horizontal',action='store_true')
    p.add_argument('--unreduced-source',type=int,action='append',default=[]);a=p.parse_args()
    r=prepare(a.input,a.output,a.sha256,a.reduce_horizontal,a.unreduced_source);print(json.dumps({'expected_regions':r['expected_regions']}))
