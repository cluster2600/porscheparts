"""Bind two normal-offset sampling resolutions before a native PicoGK study.

These are finite tessellation checks, not a self-intersection proof, wall
convergence result, interface admission or independent engineering approval.
"""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np
from geometry import catmull,sample_surface


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def audit_component(component,display,resolution):
    if (component['name']!=display['name'] or display['scope']!='structural_cell'
            or component['thickness_mm']!=display['physical_thickness_mm']):
        raise ValueError('Display does not match canonical component/thickness')
    points=np.asarray(display['vertices_mm'],float)
    faces=np.asarray(display['triangles'])
    if (points.ndim!=2 or points.shape[1]!=3 or len(points)%2
            or not np.isfinite(points).all() or np.max(np.abs(points))>10000
            or faces.ndim!=2 or faces.shape[1]!=3 or not np.issubdtype(faces.dtype,np.integer)
            or len(faces)==0 or np.min(faces)<0 or np.max(faces)>=len(points)):
        raise ValueError('Nonfinite, oversized or invalid triangular wall mesh')
    if component['type']=='planar_profile_cap':
        # Independently bind cap boundary order with a three-dimensional vector
        # area; this also works where NumPy no longer accepts 2-D np.cross.
        normal=np.asarray(component['normal_direction'],float)
        normal/=np.linalg.norm(normal)
        profile=component['profile_mm']
        base=np.array([catmull(profile,v,True) for v in
                       np.linspace(0,len(profile),len(profile)*resolution,endpoint=False)])
        shifted=base-base[0]
        if np.dot(np.cross(shifted,np.roll(shifted,-1,axis=0)).sum(axis=0),normal)<0:
            base=base[::-1].copy()
        normals=np.tile(normal,(len(base),1))
    else:
        base,_,normals=sample_surface(component,resolution)
    count=len(base);thickness=component['thickness_mm']
    if len(points)!=2*count:
        raise ValueError('Sampler resolution does not match the retained preview')
    expected=np.vstack([base+thickness/2*normals,base-thickness/2*normals])
    residual=float(np.max(np.linalg.norm(points-expected,axis=1)))
    if residual>1e-8:
        raise ValueError('Physical wall vertices differ from literal canonical normal offsets')
    triangles=points[faces]
    areas2=np.linalg.norm(np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]),axis=1)
    if np.min(areas2)<=1e-10 or len(np.unique(np.sort(faces,axis=1),axis=0))!=len(faces):
        raise ValueError('Degenerate or duplicate wall triangles')
    directed=np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]])
    edges=np.sort(directed,axis=1)
    _,inverse,counts=np.unique(edges,axis=0,return_inverse=True,return_counts=True)
    orientation=np.where(directed[:,0]<directed[:,1],1,-1)
    sums=np.bincount(inverse,weights=orientation)
    if np.any(counts!=2) or np.any(sums!=0):
        raise ValueError('Wall mesh has an open, nonmanifold or inconsistently oriented edge')
    volume=float(np.einsum('ij,ij->i',triangles[:,0],np.cross(triangles[:,1],triangles[:,2])).sum()/6)
    if volume<=0:
        raise ValueError('Wall mesh has nonpositive signed enclosed volume')
    return {'name':component['name'],'vertices':len(points),'triangles':len(faces),
            'physical_thickness_mm':thickness,'literal_offset_max_residual_mm':residual,
            'paired_wall_distance_min_mm':float(np.min(np.linalg.norm(points[:count]-points[count:],axis=1))),
            'paired_wall_distance_max_mm':float(np.max(np.linalg.norm(points[:count]-points[count:],axis=1))),
            'combinatorial_edge_incidence_two_and_opposed':True,
            'bounds_min_mm':points.min(axis=0).tolist(),'bounds_max_mm':points.max(axis=0).tolist(),
            'signed_tessellation_integral_mm3_diagnostic_only':volume,
            'volume_admitted':False,'geometric_self_intersections_verified_absent':False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model',type=Path,required=True)
    p.add_argument('--coarse-preview',type=Path,required=True)
    p.add_argument('--fine-preview',type=Path,required=True)
    p.add_argument('--coarse-segments',type=int,required=True)
    p.add_argument('--fine-segments',type=int,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise FileExistsError('Use a fresh output directory')
    if not 1<=a.coarse_segments<a.fine_segments<=12:
        raise ValueError('Expected two increasing, bounded sampling resolutions')
    paths=[a.model,a.coarse_preview,a.fine_preview]
    before={str(path):sha(path) for path in paths}
    model=json.loads(a.model.read_text())
    if model['status']!='assumed' or model['units']!='mm':
        raise ValueError('Expected an assumed millimetre canonical model')
    names=[c['name'] for c in model['components']]
    if len(set(names))!=len(names) or not 0<len(names)<=100:
        raise ValueError('Expected unique bounded canonical components')
    results=[];displays=[]
    for path,resolution in [(a.coarse_preview,a.coarse_segments),(a.fine_preview,a.fine_segments)]:
        preview=json.loads(path.read_text())
        if (preview['canonical_model_sha256']!=before[str(a.model)]
                or preview['parameter_sha256']!=model['parameter_sha256']
                or [c['name'] for c in preview['components']]!=names):
            raise ValueError('Preview provenance/component order differs from the canonical model')
        rows=[audit_component(c,d,resolution) for c,d in zip(model['components'],preview['components'])]
        results.append({'segments_per_canonical_span':resolution,'components':rows})
        displays.append(preview)
    comparisons=[]
    for low,high in zip(results[0]['components'],results[1]['components']):
        lv,hv=[r['signed_tessellation_integral_mm3_diagnostic_only'] for r in [low,high]]
        comparisons.append({'name':low['name'],'relative_diagnostic_integral_change':abs(hv-lv)/abs(hv),
                            'maximum_bound_change_mm':max(abs(x-y) for key in ['bounds_min_mm','bounds_max_mm']
                                                          for x,y in zip(low[key],high[key]))})
    if any(sha(path)!=before[str(path)] for path in paths):
        raise ValueError('Input bytes changed during the preflight')
    a.output.mkdir(parents=True,mode=0o700)
    manifest={'geometry_source_kind':'analytic_normal_offset_tessellation',
              'units':'mm','status':'assumed','geometry_sha256':before[str(a.model)],
              'parameter_sha256':model['parameter_sha256'],
              'sampler_sha256':sha(Path(__file__).with_name('geometry.py')),
              'segments_per_canonical_span':a.fine_segments,
              'source_preview_sha256':before[str(a.fine_preview)],
              'two_resolution_preflight_passed':True,'components':displays[1]['components']}
    target=a.output/'native-input.json'
    target.write_text(json.dumps(manifest,separators=(',',':'))+'\n')
    report={'status':'finite_two_resolution_native_preflight_passed',
            'geometry_sha256':before[str(a.model)],'input_sha256':before,
            'preflight_code_sha256':sha(__file__),'sampler_sha256':manifest['sampler_sha256'],
            'native_input_sha256':sha(target),'resolution_audits':results,
            'resolution_comparison':comparisons,
            'engineering_geometry_admission':False,'wall_thickness_convergence_verified':False,
            'continuous_clearance_verified':False,'geometric_self_intersections_verified_absent':False,
            'strength_verified':False,'manufacturing_authorized':False}
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'components':len(names),'output':str(a.output)}))


if __name__=='__main__':main()
