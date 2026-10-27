"""Complete one uncovered cell by extending a selected convex pair to a convex triple."""
import argparse
import json
from pathlib import Path

from merge_flagged_cells import face_nodes,read_list,sha


def convex_union(tetrahedra):
    import numpy as np
    from scipy.spatial import ConvexHull
    points=np.unique(np.vstack(tetrahedra),axis=0)
    volume=sum(abs(np.linalg.det((t[1:]-t[0]).T))/6 for t in tetrahedra)
    hull=ConvexHull(points-points.mean(axis=0)).volume
    return bool(volume>0 and abs(hull-volume)<=volume*1e-10)


def complete(case,selection,output):
    import numpy as np
    if output.exists():raise ValueError('Output must be new')
    report=json.loads((selection/'selection-report.json').read_text())
    mesh=case/'constant/polyMesh'
    for name,digest in report['mesh_hashes'].items():
        if sha(mesh/name)!=digest:raise ValueError('Selection mesh changed')
    if sha(selection/'convexMerges')!=report['selection_sha256']:raise ValueError('Parent selection changed')
    if len(report['uncovered_cells'])!=1:raise ValueError('Exactly one uncovered cell required')
    cell=report['uncovered_cells'][0]
    owners=list(map(int,read_list(mesh/'owner')));neighbours=list(map(int,read_list(mesh/'neighbour')))
    faces=read_list(mesh/'faces');points=np.array([list(map(float,r.strip('()').split())) for r in read_list(mesh/'points')])
    pairs={c:p['cells'] for p in report['selected'] for c in p['cells']}
    options=[(i,pairs[b if a==cell else a]) for i,(a,b) in enumerate(zip(owners,neighbours))
             if (a==cell or b==cell) and (b if a==cell else a) in pairs]
    relevant={cell}|{c for _,pair in options for c in pair};cell_faces={c:set() for c in relevant}
    for i,a in enumerate(owners):
        if a in relevant:cell_faces[a].add(i)
        if i<len(neighbours) and neighbours[i] in relevant:cell_faces[neighbours[i]].add(i)
    for face,pair in options:
        cluster=[cell,*pair]
        vertices=[np.unique([v for i in cell_faces[c] for v in face_nodes(faces[i])]) for c in cluster]
        if any(len(v)!=4 for v in vertices):raise ValueError('Expected original tetrahedra')
        if not convex_union([points[v] for v in vertices]):continue
        exterior=set()
        for c in cluster:exterior^=cell_faces[c]
        areas=[]
        for i in exterior:
            if i>=len(neighbours):continue
            p=points[face_nodes(faces[i])];areas.append(.5*np.cross(p[1]-p[0],p[2]-p[0]))
        a=np.asarray(areas);a/=np.linalg.norm(a,axis=1).mean();determinant=float(abs(np.linalg.det(a.T@a)))
        if determinant<.001:continue
        output.mkdir(parents=True)
        selected=sorted({p['face'] for p in report['selected']}|{face})
        (output/'convexMerges').write_text('FoamFile { format ascii; class faceSet; object convexMerges; }\n'+str(len(selected))+'\n(\n'+'\n'.join(map(str,selected))+'\n)\n')
        receipt=dict(status='convex_triple_selection_requires_native_checks',source_sha256=sha(Path(__file__)),
            parent_report_sha256=sha(selection/'selection-report.json'),cluster=cluster,added_face=face,
            determinant=determinant,convex_hull_volume_matches_cell_sum=True,
            selection_sha256=sha(output/'convexMerges'),manufacturing_authorized=False)
        (output/'completion-report.json').write_text(json.dumps(receipt,indent=2)+'\n')
        print(json.dumps(receipt,indent=2));return
    raise ValueError('No convex triple meeting the unchanged determinant threshold')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('case','selection','output'):p.add_argument(name,type=Path)
    a=p.parse_args();complete(a.case.resolve(),a.selection.resolve(),a.output.resolve())
