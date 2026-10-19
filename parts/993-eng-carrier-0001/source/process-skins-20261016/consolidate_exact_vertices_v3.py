"""Consolidate exact positions, retaining CSR and proving discarded segments covered.

No coordinate moves, radius, positive-area deletion or implicit attribute repair.
This certificate establishes identical triangle-soup support, not admission.
"""
import argparse,hashlib,json,shutil,sys
from pathlib import Path
import numpy as np

def consolidate(mesh_path,output):
    mesh_path=Path(mesh_path).resolve();output=Path(output).resolve()
    output.mkdir(parents=True,exist_ok=False)
    source=Path(__file__).resolve();shutil.copyfile(source,output/source.name)
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    before={str(p):sha(p) for p in [mesh_path,source,output/source.name]}
    d=np.load(mesh_path,allow_pickle=False);v=d['vertices'];raw_faces=d['faces']
    if v.dtype!=np.float64 or v.ndim!=2 or v.shape[1]!=3 or not np.isfinite(v).all():raise ValueError('Expected finite float64 positions')
    if not np.issubdtype(raw_faces.dtype,np.integer) or raw_faces.ndim!=2 or raw_faces.shape[1]!=3:raise ValueError('Expected integer triangle indices')
    f=np.asarray(raw_faces,dtype=np.int64)
    if not np.array_equal(f,raw_faces) or not len(f) or f.min()<0 or f.max()>=len(v):raise ValueError('Invalid/lossy indices')
    if 'canonical_input_face' in d:raise ValueError('Canonical input mapping already exists')
    vertices,inverse=np.unique(v,axis=0,return_inverse=True);mapped=inverse[f]
    if not np.array_equal(vertices[inverse],v):raise ValueError('Coordinate changed')
    keep=(mapped[:,0]!=mapped[:,1])&(mapped[:,1]!=mapped[:,2])&(mapped[:,2]!=mapped[:,0])
    retained=np.flatnonzero(keep);dropped=np.flatnonzero(~keep);faces=mapped[keep]
    edges=np.vstack([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]])
    edge_faces=np.tile(np.arange(len(faces)),3)
    witnesses={tuple(sorted(map(int,e))):int(i) for e,i in zip(edges,edge_faces)}
    used=set(map(int,np.unique(faces)));coverage=[]
    for i in dropped:
        ids=np.unique(mapped[i])
        if len(ids)==2 and tuple(ids) in witnesses:
            coverage.append([int(i),int(ids[0]),int(ids[1]),witnesses[tuple(ids)]])
        elif len(ids)==1 and int(ids[0]) in used:
            witness=int(np.flatnonzero(np.any(faces==ids[0],axis=1))[0]);coverage.append([int(i),int(ids[0]),int(ids[0]),witness])
        else:raise ValueError('Discarded segment/point is not proved covered by a retained triangle')
    data=dict(vertices=vertices,faces=faces,canonical_input_face=retained)
    csr={'all_parent_offsets','all_parent_faces'}
    if bool(csr&set(d.files)) and not csr.issubset(d.files):raise ValueError('Incomplete CSR')
    if csr.issubset(d.files):
        offsets=d['all_parent_offsets'];parents=d['all_parent_faces']
        if not np.issubdtype(offsets.dtype,np.integer) or not np.issubdtype(parents.dtype,np.integer):raise ValueError('Noninteger CSR')
        if offsets.shape!=(len(f)+1,) or offsets[0]!=0 or offsets[-1]!=len(parents) or np.any(offsets[1:]<=offsets[:-1]) or np.any(offsets<0) or np.any(offsets>len(parents)):raise ValueError('Invalid parent CSR')
        rows=[parents[int(offsets[i]):int(offsets[i+1])] for i in retained]
        data['all_parent_offsets']=np.concatenate([[0],np.cumsum([len(row) for row in rows])])
        data['all_parent_faces']=np.concatenate(rows)
    for key in d.files:
        if key in ['vertices','faces'] or key in csr:continue
        if d[key].ndim==0 or len(d[key])!=len(f):raise ValueError('Unknown non-face attribute')
        data[key]=d[key][keep]
    np.savez_compressed(output/'result.npz',**data)
    np.savez_compressed(output/'identity-map.npz',old_vertex_to_new=inverse,
        retained_input_face_ids=retained,discarded_input_face_ids=dropped,
        discarded_support_witnesses=np.asarray(coverage,dtype=np.int64).reshape(-1,4))
    unchanged=all(sha(p)==value for p,value in before.items())
    if not unchanged:raise ValueError('Source/input changed')
    report={'schema':'exact-position-consolidation-v3','status':'exact_representation_consolidated_pending_independent_audit',
        'inputs_sha256':before,'input_sha256':sha(mesh_path),'result_sha256':sha(output/'result.npz'),
        'identity_map_sha256':sha(output/'identity-map.npz'),'identities_unchanged':True,
        'original_vertices':len(v),'vertices':len(vertices),'exactly_equal_vertex_identities_consolidated':len(v)-len(vertices),
        'original_faces':len(f),'faces':len(faces),'discarded_repeated_position_faces':len(dropped),
        'discarded_support_covered_by_retained_faces':len(coverage)==len(dropped),
        'coordinate_displacement_mm':0.0,'discarded_surface_area_mm2':0.0,'discarded_signed_volume_mm3':0.0,
        'retained_face_attributes':list(data.keys())[2:],'all_geometric_parents_preserved':csr.issubset(d.files),
        'runtime':{'python':sys.version,'numpy':np.__version__},
        'proof':'Every retained triangle has exactly the same three XYZ positions/orientation as its input face. Every discarded face has repeated exact positions and its entire segment/point lies on a listed retained edge/triangle. Therefore the union of the entire encoded triangle soup is identical, not only its positive-area subset. All parent CSR rows of retained faces are unchanged.',
        'scope':'Exact representation equality only. Native global intersections, strict topology, composed exact-native drift and semantic interface gates remain required; no part admitted.'}
    (output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mesh',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();print(json.dumps(consolidate(a.mesh,a.output)))
