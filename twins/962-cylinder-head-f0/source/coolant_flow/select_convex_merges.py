"""Select disjoint convex tetrahedron pairs for the native OpenFOAM face remover."""
import argparse
import json
from pathlib import Path

from merge_flagged_cells import face_nodes,read_list,sha


def convex_pair(a,b):
    import numpy as np
    from scipy.spatial import ConvexHull
    points=np.unique(np.vstack([a,b]),axis=0)
    if len(points)!=5:return False
    volume=sum(abs(np.linalg.det((t[1:]-t[0]).T))/6 for t in (a,b))
    hull=ConvexHull(points-points.mean(axis=0)).volume
    return bool(volume>0 and abs(hull-volume)<=volume*1e-10)


def select(case,output):
    import numpy as np
    from relocate_stencil import determinants
    if output.exists():raise ValueError('Output must be new')
    mesh=case/'constant/polyMesh';sets=mesh/'sets'
    owners=list(map(int,read_list(mesh/'owner')));neighbours=list(map(int,read_list(mesh/'neighbour')))
    faces=read_list(mesh/'faces');points=np.array([list(map(float,r.strip('()').split())) for r in read_list(mesh/'points')])
    bad=set(map(int,read_list(sets/'underdeterminedCells')))
    low=list(map(int,read_list(sets/'lowWeightFaces')))
    targets=bad|{owners[i] for i in low}|{neighbours[i] for i in low}
    adjacent={c:[] for c in targets};relevant=set(targets)
    for i,n in enumerate(neighbours):
        o=owners[i]
        if o in targets:adjacent[o].append((i,n));relevant.add(n)
        if n in targets:adjacent[n].append((i,o));relevant.add(o)
    cell_faces={c:set() for c in relevant}
    for i,o in enumerate(owners):
        if o in relevant:cell_faces[o].add(i)
        if i<len(neighbours) and neighbours[i] in relevant:cell_faces[neighbours[i]].add(i)
    vertices={c:np.unique([v for i in cell_faces[c] for v in face_nodes(faces[i])]) for c in relevant}
    if any(len(v)!=4 for v in vertices.values()):raise ValueError('Selection requires tetrahedra')
    volumes={c:abs(np.linalg.det((points[v[1:]]-points[v[0]]).T))/6 for c,v in vertices.items()}
    requests=list(sorted(bad))
    for i in low:
        a,b=owners[i],neighbours[i];requests.insert(0,min((a,b),key=lambda c:volumes[c]))
    used=set();chosen=[];uncovered=[]
    for cell in requests:
        if cell in used:continue
        candidates=[]
        for face,other in adjacent[cell]:
            if other in used or not convex_pair(points[vertices[cell]],points[vertices[other]]):continue
            exterior=cell_faces[cell]^cell_faces[other]
            area=[]
            for i in exterior:
                if i>=len(neighbours):continue
                p=points[face_nodes(faces[i])];area.append(.5*np.cross(p[1]-p[0],p[2]-p[0]))
            a=np.asarray(area);a=a/np.linalg.norm(a,axis=1).mean()
            determinant=abs(np.linalg.det(a.T@a))
            if determinant>=.001:candidates.append((determinant,face,other))
        if not candidates:uncovered.append(cell);continue
        determinant,face,other=max(candidates)
        used.update((cell,other));chosen.append(dict(face=face,cells=[cell,other],determinant=float(determinant)))
    output.mkdir(parents=True)
    selected=sorted(v['face'] for v in chosen)
    (output/'convexMerges').write_text('FoamFile { format ascii; class faceSet; object convexMerges; }\n'+str(len(selected))+'\n(\n'+'\n'.join(map(str,selected))+'\n)\n')
    report=dict(status='convex_pair_selection_requires_native_mesh_checks',source_sha256=sha(Path(__file__)),
        mesh_hashes={n:sha(mesh/n) for n in ('points','faces','owner','neighbour','boundary')},
        diagnostic_hashes={n:sha(sets/n) for n in ('underdeterminedCells','lowWeightFaces')},
        native_check_sha256=sha(case/'log.checkMesh.before'),selected=chosen,
        uncovered_cells=sorted(set(uncovered)-used),selection_sha256=sha(output/'convexMerges'),
        openfoam_mesh_accepted=False,manufacturing_authorized=False)
    (output/'selection-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('SELECTED',len(chosen),'UNCOVERED',report['uncovered_cells'],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('case',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();select(a.case.resolve(),a.output.resolve())
