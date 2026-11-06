"""Declare finite canonical-model occupancy sites before querying a native field.

Sites are design-frame diagnostics. Cap first-ear centroids can be close to an
edge and may remain unresolved at the chosen voxel size; failures are retained.
"""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np
import geometry


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--model',type=Path,required=True)
    p.add_argument('--native-input',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise FileExistsError('Use a fresh output file')
    model=json.loads(a.model.read_text());display=json.loads(a.native_input.read_text())
    if model['units']!='mm' or model['status']!='assumed' or display['geometry_sha256']!=sha(a.model):
        raise ValueError('Expected a bound assumed millimetre model and native input')
    components={c['name']:c for c in model['components']};meshes={c['name']:c for c in display['components']};probes=[]
    for x in [15,350,1050,1750,2085]:
        roof=components['integrated_tunnel'];bottom=components['tunnel_lower_return']
        ur=geometry.parameter_at_x(roof,x);ub=geometry.parameter_at_x(bottom,x)
        r=geometry.evaluate(roof,ur,7);b=geometry.evaluate(bottom,ub,1.5);z=float((r[2]+b[2])/2)
        for y in [-30,0,30]:
            probes.append({'label':f'tunnel_void_X{x}_Y{y}','class':'corridor_void','point_mm':[x,y,z],
                           'expected_inside':False,'construction':{'roof_uv':[ur,7],'lower_return_uv':[ub,1.5],'z_midpoint_mm':z}})
    for c in model['components']:
        if c['type']=='planar_profile_cap':
            mesh=meshes[c['name']];points=np.asarray(mesh['vertices_mm']);count=len(points)//2;ids=np.asarray(mesh['triangles'][0])
            point=((points[ids]+points[ids+count])/2).mean(axis=0)
            n=np.asarray(c['normal_direction'],float);n/=np.linalg.norm(n);uv=None
        else:
            nu=len(c['sections_mm'])-1;lo,hi=c.get('v_range',[0,len(c['sections_mm'][0])-int(not c['closed_profile'])])
            u=float(max(0,min(nu,round(nu/2))));v=float(max(lo,min(hi,round((lo+hi)/2))))
            point=geometry.evaluate(c,u,v);n=geometry.normal(c,u,v);uv=[u,v]
        probes.append({'label':c['name']+'_material','class':'canonical_wall_material','component':c['name'],
                       'point_mm':point.tolist(),'expected_inside':True,'canonical_uv':uv})
        for side in [-1,1]:
            probes.append({'label':c['name']+f'_normal_neighbor_{side}','class':'neighbor_observation_only','component':c['name'],
                           'point_mm':(point+side*(c['thickness_mm']/2+3)*n).tolist(),'expected_inside':None,
                           'reason':'May meet another union component; not a universal outside assertion.'})
    result={'geometry_sha256':sha(a.model),'native_input_sha256':sha(a.native_input),
            'construction_code_sha256':sha(__file__),'sampler_source_sha256':sha(geometry.__file__),
            'scope':'Finite design-frame probes only; no continuous clearance, source-interface or wall-convergence claim.',
            'probes':probes}
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'probes':len(probes),'output':str(a.output)}))


if __name__=='__main__':main()
