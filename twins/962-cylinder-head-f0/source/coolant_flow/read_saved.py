"""Read every saved tetrahedron and compare the retained boundary independently."""
import argparse
import json
from pathlib import Path

from mesh_surface import sha


def tetra_metrics(points):
    import numpy as np
    edges = np.stack([points[:,i]-points[:,0] for i in (1,2,3)],axis=2)
    reference = np.array([[1,.5,.5],[0,np.sqrt(3)/2,np.sqrt(3)/6],[0,0,np.sqrt(2/3)]])
    a = edges @ np.linalg.inv(reference)
    cof = np.stack([np.cross(a[:,:,1],a[:,:,2]),np.cross(a[:,:,2],a[:,:,0]),np.cross(a[:,:,0],a[:,:,1])],axis=2)
    det = np.einsum('ij,ij->i',a[:,:,0],cof[:,:,0])
    denominator = np.linalg.norm(a,axis=(1,2))*np.linalg.norm(cof,axis=(1,2))
    quality = np.divide(3*det,denominator,out=np.zeros(len(a)),where=denominator>0)
    volumes = np.einsum('ij,ij->i',edges[:,:,0],np.cross(edges[:,:,1],edges[:,:,2]))/6
    return quality,volumes


def inspect(surface, case):
    import gmsh
    import numpy as np
    import trimesh
    from scipy.spatial import cKDTree
    report = json.loads((case/'mesh-report.json').read_text())
    reference_receipt = json.loads((surface/'surface-report.json').read_text())
    if sha(case/'coolant.msh') != report['mesh_sha256'] or sha(surface/'coolant.stl') != reference_receipt['candidate_sha256']:
        raise ValueError('Saved input changed')
    if (case/'saved-readback.json').exists():raise ValueError('Do not replace a readback')
    gmsh.initialize([])
    try:
        gmsh.option.setNumber('General.Terminal',0);gmsh.open(str(case/'coolant.msh'))
        tags,xyz,_=gmsh.model.mesh.getNodes();order=np.argsort(tags);tags=np.asarray(tags)[order]
        xyz=np.asarray(xyz).reshape(-1,3)[order]*1000
        if len(np.unique(tags))!=len(tags) or not np.isfinite(xyz).all():raise ValueError('Invalid saved nodes')
        typ,element_tags,connect=gmsh.model.mesh.getElements(3)
        if list(typ)!=[4]:raise ValueError('Saved volume is not linear tetrahedra')
        t=np.asarray(connect[0]).reshape(-1,4)
        typ,_,connect=gmsh.model.mesh.getElements(2)
        if list(typ)!=[2]:raise ValueError('Saved boundary is not linear triangles')
        boundary=np.asarray(connect[0]).reshape(-1,3)
        indices=np.searchsorted(tags,t)
        if indices.max()>=len(tags) or not np.array_equal(tags[indices],t):raise ValueError('Unknown tet node')
        q,v=tetra_metrics(xyz[indices])
        native_q=gmsh.model.mesh.getElementQualities(element_tags[0],'minSICN')
        if not np.allclose(q,native_q,rtol=1e-8,atol=1e-10):raise ValueError('Independent SICN disagrees with native values')
        original=trimesh.load_mesh(surface/'coolant.stl',process=True)
        bound_tags=np.unique(boundary);bi=np.searchsorted(tags,bound_tags)
        distances,mapping=cKDTree(original.vertices).query(xyz[bi])
        if distances.max()>1e-9 or len(np.unique(mapping))!=len(original.vertices) or len(bound_tags)!=len(original.vertices):
            raise ValueError('Saved boundary coordinates differ from the screened surface')
        mapped=mapping[np.searchsorted(bound_tags,boundary)]
        def canonical(faces):
            result=faces.copy()
            for i in range(3):
                mask=np.argmin(faces,axis=1)==i;result[mask]=np.roll(faces[mask],-i,axis=1)
            return result[np.lexsort(result.T[::-1])]
        if not np.array_equal(canonical(mapped),canonical(original.faces)):
            raise ValueError('Saved oriented boundary triangles changed')
        tf=np.concatenate([t[:,pattern] for pattern in ((1,2,3),(0,3,2),(0,1,3),(0,2,1))])
        keys,index,inverse,counts=np.unique(np.sort(tf,axis=1),axis=0,return_index=True,return_inverse=True,return_counts=True)
        parity=(tf[:,0]>tf[:,1])^(tf[:,0]>tf[:,2])^(tf[:,1]>tf[:,2])
        signed=np.bincount(inverse,weights=np.where(parity,-1,1))
        if counts.max()>2 or np.any(signed[counts==2]!=0):raise ValueError('Nonconformal or inconsistently oriented interior faces')
        if not np.array_equal(canonical(tf[index[counts==1]]),canonical(boundary)):
            raise ValueError('Volume exterior differs from the tagged boundary')
        face_lookup={tuple(sorted(f)):i for i,f in enumerate(original.faces)}
        vertex_lookup=dict(zip(map(int,bound_tags),map(int,mapping)))
        poor=[]
        for cell in np.flatnonzero(q<.1):
            nodes=t[cell];local=[vertex_lookup.get(int(n),-1) for n in nodes]
            source_faces=[]
            for pattern in ((1,2,3),(0,3,2),(0,1,3),(0,2,1)):
                key=tuple(sorted(local[i] for i in pattern))
                if -1 not in key and key in face_lookup:source_faces.append(face_lookup[key])
            poor.append(dict(cell=int(cell),sicn=float(q[cell]),boundary_nodes=sum(i>=0 for i in local),
                             source_boundary_faces=source_faces,centre_mm=xyz[indices[cell]].mean(axis=0).tolist()))
        result=dict(status='complete_saved_volume_readback_not_a_flow_solution',cells=len(t),
                    minimum_sicn=float(q.min()),below_sicn_01=int(np.count_nonzero(q<.1)),
                    minimum_volume_mm3=float(v.min()),volume_mm3=float(v.sum()),
                    maximum_boundary_coordinate_difference_mm=float(distances.max()),
                    boundary_triangles=len(boundary),boundary_orientation_preserved=True,
                    interior_face_incidence_and_orientation_passed=True,
                    unreferenced_nodes=int(len(tags)-len(np.unique(t))),
                    poor_cells=poor,
                    independent_volume_quality_passed=bool(np.all(q>=.1) and np.all(v>0)),
                    mesh_sha256=sha(case/'coolant.msh'),source_sha256=sha(Path(__file__)),
                    openfoam_mesh_accepted=False,hydraulic_performance_validated=False,manufacturing_authorized=False)
        (case/'saved-readback.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
        print(json.dumps(result,indent=2),flush=True)
    finally:gmsh.finalize()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('surface',type=Path);parser.add_argument('case',type=Path)
    args=parser.parse_args();inspect(args.surface.resolve(),args.case.resolve())
