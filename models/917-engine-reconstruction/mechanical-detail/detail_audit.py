"""Use the house exact-zero witness once; preserve its strict topology predicate."""
import json
import numpy as np
import trimesh
import study
from reconstruct import save,sha256


def audit_native(directory):
    receipt=json.loads((directory/'receipt.json').read_text());records=receipt['parts']
    if isinstance(records,list):records={r['id']:r for r in records}
    meshes={};audits={}
    for name,row in records.items():
        print('Audit '+directory.name+'/'+name,flush=True)
        for ext in ('stl','vdb'):
            if sha256(directory/(name+'.'+ext))!=row[ext+'_sha256']:raise ValueError('Native file changed: '+name)
        try:
            raw=trimesh.load_mesh(directory/(name+'.stl'),process=False)
            if not isinstance(raw,trimesh.Trimesh) or not np.isfinite(raw.vertices).all():raise ValueError('Expected finite triangles')
            mesh,witness=study.prior.HYP.exact_zero_candidate(raw)
            topology=witness['audit']
            passed=bool(topology['strict_raw_mesh_screen_pass'] and topology['surface_components_including_degenerate_faces']==1 and witness['remaining_duplicate_face_groups']==0)
            audit={'source_sha256':sha256(directory/(name+'.stl')),'triangles':len(mesh.faces),'signed_volume_mm3_hypothesis':float(mesh.volume),
                   'passed':passed,'witness':witness,'self_intersection_checked':False}
            if passed:meshes[name]=mesh
        except ValueError as error:audit={'passed':False,'error':str(error)}
        audits[name]=audit
    save(directory/'independent-audit.json',audits);return meshes,audits


def verified_cache(directory):
    import hashlib
    receipt=json.loads((directory/'receipt.json').read_text())['parts']
    audits=json.loads((directory/'independent-audit.json').read_text());meshes={}
    if set(receipt)!=set(audits) or not all(r['passed'] for r in audits.values()):raise ValueError('Unaccepted native cache')
    for name,row in receipt.items():
        for ext in ('stl','vdb'):
            if sha256(directory/(name+'.'+ext))!=row[ext+'_sha256']:raise ValueError('Cached native file changed')
        raw=trimesh.load_mesh(directory/(name+'.stl'),process=False)
        vertices,inverse=np.unique(raw.vertices,axis=0,return_inverse=True);faces=inverse[raw.faces]
        cross=np.cross(vertices[faces[:,1]]-vertices[faces[:,0]],vertices[faces[:,2]]-vertices[faces[:,0]])
        faces=faces[np.any(cross!=0,axis=1)]
        digest=hashlib.sha256(np.asarray(vertices[faces],dtype='<f8').tobytes()).hexdigest()
        if digest!=audits[name]['witness']['remaining_oriented_faces_sha256']:raise ValueError('Cache geometry differs from its independent witness')
        meshes[name]=trimesh.Trimesh(vertices,faces,process=False)
    return meshes,audits
