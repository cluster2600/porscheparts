"""Merge flagged tetrahedra across large internal faces; preserve every boundary face."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_list(path):
    text=path.read_text()
    if not re.search(r'format\s+ascii;',text):raise ValueError('ASCII OpenFOAM input required')
    match=re.search(r'^\s*(\d+)\s*\n\(\s*\n',text,re.M)
    if not match:raise ValueError('Missing list: '+str(path))
    rows=text[match.end():].split(')',1)[0] if path.name in ('owner','neighbour','underdeterminedCells','lowWeightFaces') else None
    if rows is None:
        rows=text[match.end():].split('\n)')[0].splitlines()
    else:rows=rows.split()
    if len(rows)!=int(match[1]):raise ValueError('List length mismatch: '+str(path))
    return rows


def face_nodes(row):
    values=[int(v) for v in re.findall(r'\d+',row)]
    if values[0]!=len(values)-1:raise ValueError('Invalid face')
    return values[1:]


def merged_connectivity(faces,owners,neighbours,selected):
    count=max(owners+neighbours)+1
    parent=list(range(count))
    def root(i):
        while parent[i]!=i:
            parent[i]=parent[parent[i]];i=parent[i]
        return i
    for i in sorted(selected):
        if i<0 or i>=len(neighbours):raise ValueError('Only internal faces can be removed')
        a,b=root(owners[i]),root(neighbours[i]);parent[max(a,b)]=min(a,b)
    roots=[root(i) for i in range(count)]
    labels={r:i for i,r in enumerate(sorted(set(roots)))}
    mapping=[labels[r] for r in roots]
    internal=[];boundary=[]
    for i,row in enumerate(faces):
        owner=mapping[owners[i]]
        if i>=len(neighbours):boundary.append((row,owner));continue
        neighbour=mapping[neighbours[i]]
        if owner==neighbour:continue
        if owner>neighbour:
            nodes=face_nodes(row)[::-1];row=str(len(nodes))+'('+' '.join(map(str,nodes))+')'
            owner,neighbour=neighbour,owner
        internal.append((owner,neighbour,row))
    internal.sort(key=lambda f:(f[0],f[1]))
    return ([f[2] for f in internal]+[f[0] for f in boundary],
            [f[0] for f in internal]+[f[1] for f in boundary],
            [f[1] for f in internal],len(labels))


def merge(source,diagnostics,output):
    if output.exists():raise ValueError('Output must be new')
    mesh=source/'constant/polyMesh';sets=diagnostics/'constant/polyMesh/sets'
    for name in ('points','faces','owner','neighbour','boundary'):
        if sha(mesh/name)!=sha(diagnostics/'constant/polyMesh'/name):
            raise ValueError('Diagnostics belong to a different mesh: '+name)
    owners=list(map(int,read_list(mesh/'owner')));neighbours=list(map(int,read_list(mesh/'neighbour')))
    faces=read_list(mesh/'faces');points=[tuple(map(float,row.strip('()').split())) for row in read_list(mesh/'points')]
    bad=set(map(int,read_list(sets/'underdeterminedCells')))
    selected=set(map(int,read_list(sets/'lowWeightFaces')));best={}
    for i,n in enumerate(neighbours):
        o=owners[i]
        if o not in bad and n not in bad:continue
        nodes=face_nodes(faces[i])
        if len(nodes)!=3:raise ValueError('Selection requires original tetrahedra')
        a,b,c=[points[j] for j in nodes]
        u=[b[j]-a[j] for j in range(3)];v=[c[j]-a[j] for j in range(3)]
        area2=sum((u[(j+1)%3]*v[(j+2)%3]-u[(j+2)%3]*v[(j+1)%3])**2 for j in range(3))
        for cell in (o,n):
            if cell in bad and (cell not in best or area2>best[cell][0]):best[cell]=(area2,i)
    if set(best)!=bad:raise ValueError('Flagged cell has no internal neighbour')
    selected.update(item[1] for item in best.values())
    new_faces,new_owner,new_neighbour,count=merged_connectivity(faces,owners,neighbours,selected)
    if new_faces[len(new_neighbour):]!=faces[len(neighbours):]:raise ValueError('Boundary face changed')
    for name in ('0','system','constant'):shutil.copytree(source/name,output/name)
    for name in ('case-report.json','accept_mesh.py'):shutil.copy2(source/name,output/name)
    target=output/'constant/polyMesh'
    def write(name,kind,rows):
        (target/name).write_text('FoamFile { format ascii; class '+kind+'; object '+name+'; }\n'+str(len(rows))+'\n(\n'+'\n'.join(map(str,rows))+'\n)\n')
    write('faces','faceList',new_faces);write('owner','labelList',new_owner);write('neighbour','labelList',new_neighbour)
    write('cellZones','regIOobject',[])
    if (target/'sets').exists():shutil.rmtree(target/'sets')
    removed=len(neighbours)-len(new_neighbour)
    boundary=(mesh/'boundary').read_text()
    (target/'boundary').write_text(re.sub(r'(startFace\s+)(\d+)',lambda m:m[1]+str(int(m[2])-removed),boundary))
    report=dict(status='candidate_requires_checkMesh',original_cells=max(owners)+1,cells=count,
        selected_faces=len(selected),removed_internal_faces=removed,flagged_cells=len(bad),
        exact_boundary_faces_preserved=True,points_unchanged=sha(mesh/'points')==sha(target/'points'),
        source_hashes={str(p):sha(p) for p in [Path(__file__),mesh/'faces',mesh/'points',mesh/'owner',mesh/'neighbour',mesh/'boundary',sets/'underdeterminedCells',sets/'lowWeightFaces',diagnostics/'log.checkMesh.before']},
        output_hashes={p.name:sha(p) for p in target.iterdir() if p.is_file()},manufacturing_authorized=False)
    (output/'merge-report.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('source','diagnostics','output'):parser.add_argument(name,type=Path)
    args=parser.parse_args();merge(args.source.resolve(),args.diagnostics.resolve(),args.output.resolve())
