"""Independent libigl audit of every complete mesh in the actual component 3MF."""
import hashlib
import importlib.util
from importlib.metadata import version
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import zipfile


def main():
    import numpy as np
    import igl.predicates
    archive=Path('/input/study.3mf');expected=json.loads(Path('/input/source-assessment.json').read_text());out=Path('/output')
    raw=archive.read_bytes();digest=hashlib.sha256(raw).hexdigest()
    if digest!=expected['archive_sha256']:raise ValueError('Actual archive differs')
    spec=importlib.util.spec_from_file_location('_retained_full_surface_topology','/source/audit.py')
    audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
    report=dict(status='incomplete',archive_sha256=digest,versions={name:version(name)for name in ['libigl','numpy','scipy']},components=[],
                scope='Full intracomponent topology and self intersections; intentional intercomponent overlap is a separate source-union stage',
                retained_needle_ratio_threshold=.001)
    core='{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}'
    with zipfile.ZipFile(archive)as z:model=ET.fromstring(z.read('3D/3dmodel.model'))
    objects={int(o.get('id')):o for o in model.findall('./'+core+'resources/'+core+'object')}
    for reference in expected['components']:
        obj=objects[reference['lib3mf_resource_id']]
        vertices=np.asarray([[float(v.get(c))for c in ['x','y','z']]for v in obj.findall('./'+core+'mesh/'+core+'vertices/'+core+'vertex')],dtype='<f8')
        faces=np.asarray([[int(t.get(c))for c in ['v1','v2','v3']]for t in obj.findall('./'+core+'mesh/'+core+'triangles/'+core+'triangle')],dtype='<i8')
        v32=vertices.astype('<f4');f32=faces.astype('<u4')
        exact_identity=(np.array_equal(v32.astype('<f8').view('<u8'),vertices.view('<u8')) and hashlib.sha256(v32.tobytes()).hexdigest()==reference['vertex_bytes_sha256'] and hashlib.sha256(f32.tobytes()).hexdigest()==reference['face_index_bytes_sha256'])
        if not exact_identity:raise ValueError('Complete component coordinate/face identity differs')
        topology=audit.topology(vertices,faces)
        found,pairs,_=igl.predicates.find_self_intersections(vertices,faces,False)
        pair_file=out/f'component-{reference["index"]}-self-intersection-pairs.json'
        pair_file.write_text(json.dumps(np.asarray(pairs).tolist())+'\n')
        tri=vertices[faces];twice=np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1)
        longest=np.max(np.sum((tri-np.roll(tri,-1,axis=1))**2,axis=2),axis=1)
        with np.errstate(divide='ignore',invalid='ignore'):needles=np.flatnonzero(twice/longest<.001).tolist()
        failures=[key for key in ['boundary_edges','nonmanifold_edges','inconsistent_orientation_edges','degenerate_triangles','needle_triangles']if topology[key]!=0]
        if topology['connected_components']!=1:failures.append('connected_components')
        if topology['volume_mm3']<=0:failures.append('nonpositive_volume')
        if len(pairs)or bool(found):failures.append('self_intersections')
        row=dict(index=reference['index'],source_mesh_identity_exact=True,topology=topology,self_intersection_pairs=len(pairs),self_intersection_pair_file=pair_file.name,
                 full_needle_triangle_indices=needles,failures=failures,status='passed'if not failures else'refused')
        report['components'].append(row)
        (out/'progress.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    report['status']='all_complete_component_surface_screens_passed'if len(report['components'])==3 and all(not r['failures']for r in report['components'])else'component_surface_screen_refused'
    (out/'assessment.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(status=report['status'],components=[dict(index=r['index'],failures=r['failures'])for r in report['components']])))


if __name__=='__main__':main()
