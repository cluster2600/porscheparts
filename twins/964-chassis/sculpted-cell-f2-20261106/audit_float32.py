"""Check normal-offset triangles before conversion to PicoGK Vector3 floats.

Reports and rejects collapsed/coincident vertices, small/degenerate float32
facets or numerical winding reversals. Never merges or repairs input geometry.
"""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--model',type=Path,required=True)
    p.add_argument('--preview',type=Path,action='append',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise FileExistsError('Use a fresh output directory')
    expected=sha(a.model);results=[];passed=True
    for path in a.preview:
        preview=json.loads(path.read_text())
        if preview['canonical_model_sha256']!=expected:raise ValueError('Preview belongs to another canonical model')
        rows=[]
        for component in preview['components']:
            points=np.asarray(component['vertices_mm'],dtype=np.float64);faces=np.asarray(component['triangles'],dtype=np.int64)
            f32=points.astype(np.float32)
            p64=points[faces];p32=f32[faces]
            normal64=np.cross(p64[:,1]-p64[:,0],p64[:,2]-p64[:,0])
            normal32=np.cross(p32[:,1]-p32[:,0],p32[:,2]-p32[:,0])
            length_squared32=np.sum(normal32*normal32,axis=1,dtype=np.float32)
            coincident64=len(points)-len(np.unique(points,axis=0));coincident32=len(f32)-len(np.unique(f32,axis=0))
            bad=np.flatnonzero(~np.isfinite(length_squared32)|(length_squared32<np.float32(1e-16)))
            reversed_faces=np.flatnonzero(np.einsum('ij,ij->i',normal64,normal32.astype(np.float64))<=0)
            ok=coincident32==0 and len(bad)==0 and len(reversed_faces)==0
            rows.append({'name':component['name'],'vertices':len(points),'triangles':len(faces),
                         'coincident_vertices_float64':coincident64,'coincident_vertices_float32':coincident32,
                         'new_float32_vertex_coincidences':coincident32-coincident64,
                         'minimum_float32_cross_length_squared':float(length_squared32.min()),
                         'failed_float32_triangles':len(bad),'first_failed_triangle_ids':bad[:32].tolist(),
                         'winding_reversals_or_collapses':len(reversed_faces),
                         'first_reversed_or_collapsed_triangle_ids':reversed_faces[:32].tolist(),'passed':ok})
            passed=passed and ok
        results.append({'preview_sha256':sha(path),'components':rows})
    a.output.mkdir(parents=True,mode=0o700)
    report={'status':'float32_source_preflight_passed' if passed else 'float32_source_preflight_failed',
            'geometry_sha256':expected,'code_sha256':sha(__file__),'resolution_audits':results,
            'float32_cross_length_squared_rejection_threshold':float(np.float32(1e-16)),
            'numeric_scope':'IEEE float32 coordinates and operations; native C# retains its own exact Vector3 guard before mesh insertion.',
            'geometry_repaired_or_merged':False,'native_execution_admitted_by_this_check_alone':False}
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'failed_components':[
        row['name'] for result in results for row in result['components'] if not row['passed']]}))
    if not passed:raise SystemExit(1)


if __name__=='__main__':main()
