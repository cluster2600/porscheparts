"""Use MMG's required entities to confine remeshing to the remaining stencil defects."""
import argparse
import json
from pathlib import Path

from mesh_surface import sha
from relocate_stencil import PATTERNS,determinants,tetra_metrics


def patch(tets,seeds):
    import numpy as np
    active=np.zeros(len(tets),bool);active[seeds]=True
    for _ in range(2):active=np.any(np.isin(tets,np.unique(tets[active])),axis=1)
    return active


def prepare(parent,output):
    import gmsh
    import numpy as np
    receipt=json.loads((parent/'mesh-report.json').read_text())
    audit=json.loads((parent/'saved-readback.json').read_text())
    if sha(parent/'coolant.msh')!=receipt['mesh_sha256'] or receipt['mesh_sha256']!=audit['mesh_sha256']:
        raise ValueError('Parent mesh binding changed')
    if audit['independent_volume_quality_passed'] is not True:raise ValueError('Independent SICN screen required')
    if output.exists():raise ValueError('Output must be new')
    gmsh.initialize([])
    try:
        gmsh.option.setNumber('General.Terminal',0);gmsh.open(str(parent/'coolant.msh'))
        tags,x,_=gmsh.model.mesh.getNodes();order=np.argsort(tags);tags=np.asarray(tags)[order];x=np.asarray(x).reshape(-1,3)[order]
        if list(gmsh.model.mesh.getElementTypes(3))!=[4]:raise ValueError('Linear tetrahedra required')
        t=np.searchsorted(tags,np.asarray(gmsh.model.mesh.getElements(3)[2][0]).reshape(-1,4))
        triangles=[];references=[]
        for reference in (101,102,103):
            faces=np.searchsorted(tags,np.asarray(gmsh.model.mesh.getElements(2,reference)[2][0]).reshape(-1,3))
            triangles.extend(faces);references.extend([reference]*len(faces))
        triangles=np.asarray(triangles)
        _,inverse,counts=np.unique(np.sort(t[:,PATTERNS].reshape(-1,3),axis=1),axis=0,return_inverse=True,return_counts=True)
        if counts.max()!=2:raise ValueError('Nonmanifold incidence')
        internal=(counts[inverse]==2).reshape(-1,4)
        order=np.argsort(inverse,kind='stable');starts=np.r_[0,np.cumsum(counts)[:-1]];first=starts[counts==2]
        pairs=np.c_[order[first]//4,order[first+1]//4]
        q,v=tetra_metrics(x[t]);d=determinants(x[t],internal);weights=v[pairs].min(axis=1)/v[pairs].sum(axis=1)
        seeds=np.unique(np.r_[np.flatnonzero((q<.1)|(d<.001)),pairs[weights<.05].ravel()])
        if not len(seeds):raise ValueError('No defects to repair')
        active=patch(t,seeds)
        if active.sum()>20000:raise ValueError('Local region exceeds 20000 cells')
        fixed=np.zeros(len(x),bool);fixed[t[~active].ravel()]=True
        required_triangles=np.all(fixed[triangles],axis=1)
        output.mkdir(parents=True);medit=output/'input.mesh'
        with medit.open('w') as f:
            f.write('MeshVersionFormatted 2\nDimension 3\nVertices\n'+str(len(x))+'\n')
            for p in x:f.write(' '.join(format(float(a),'.17g') for a in p)+' 0\n')
            f.write('Triangles\n'+str(len(triangles))+'\n')
            for face,reference in zip(triangles,references):f.write(' '.join(map(str,face+1))+' '+str(reference)+'\n')
            f.write('Tetrahedra\n'+str(len(t))+'\n')
            for tet in t:f.write(' '.join(map(str,tet+1))+' 1\n')
            for name,ids in (('RequiredVertices',np.flatnonzero(fixed)+1),
                             ('RequiredTriangles',np.flatnonzero(required_triangles)+1),
                             ('RequiredTetrahedra',np.flatnonzero(~active)+1)):
                f.write(name+'\n'+str(len(ids))+'\n'+'\n'.join(map(str,ids))+'\n')
            f.write('End\n')
        record=dict(status='local_mmg_input_not_repaired',source_sha256=sha(Path(__file__)),
            parent_mesh_sha256=receipt['mesh_sha256'],input_sha256=sha(medit),units='m',
            seed_cells=seeds.tolist(),active_cells=int(active.sum()),required_tetrahedra=int((~active).sum()),
            required_triangles=int(required_triangles.sum()),required_vertices=int(fixed.sum()),
            boundary_hausdorff_parameter_m=.000005,manufacturing_authorized=False)
        (output/'input-report.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
    finally:gmsh.finalize()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('parent',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();prepare(a.parent.resolve(),a.output.resolve())
