"""Propose conforming interior-edge-star subdivision at an exact rational fraction with exact cavity checks.

Only a local proposal: whole-mesh incidence, embedding, source identity and
solver intake must be independently checked after assembly. No part is edited.
"""
from collections import Counter,defaultdict
from fractions import Fraction as Q
import numpy as np

def boundary(cells):
    counts=Counter();signed=Counter()
    for a,b,c,d in cells:
        for face in [(b,c,d),(a,d,c),(a,b,d),(a,c,b)]:
            key=tuple(sorted(map(int,face)))
            parity=sum(face[i]>face[j] for i in range(3) for j in range(i+1,3))%2
            counts[key]+=1;signed[key]+=(-1 if parity else 1)
    assert all(n in (1,2) for n in counts.values()),'Nonmanifold cavity face'
    assert all(signed[k]==0 for k,n in counts.items() if n==2),'Internal orientation mismatch'
    return {k:signed[k] for k,n in counts.items() if n==1}

def volume(points):
    p=[[Q(float(x)) for x in row] for row in points]
    a,b,c=[[p[i][j]-p[0][j] for j in range(3)] for i in (1,2,3)]
    return (a[0]*(b[1]*c[2]-b[2]*c[1])-a[1]*(b[0]*c[2]-b[2]*c[0])+a[2]*(b[0]*c[1]-b[1]*c[0]))/6

def propose(vertices,star,edge,new_node_id,volume_cap=Q(1,2),*,fraction=Q(1,2)):
    v=np.asarray(vertices);cells=np.asarray(star,dtype=np.int64)
    assert v.ndim==2 and v.shape[1]==3 and np.isfinite(v).all()
    assert cells.ndim==2 and cells.shape[1]==4 and len(cells)>=3
    assert cells.min()>=0 and cells.max()<len(v)
    assert all(len(set(map(int,row)))==4 for row in cells)
    assert len({tuple(sorted(map(int,row))) for row in cells})==len(cells)
    a,b=map(int,edge);assert a!=b and 0<=a<len(v) and 0<=b<len(v)
    assert type(new_node_id) is int and new_node_id>=len(v)
    links=[];neighbors=defaultdict(set)
    for row in cells:
        assert a in row and b in row,'Cell outside requested edge star'
        u,w=[int(x) for x in row if x not in (a,b)]
        pair=tuple(sorted((u,w)));assert pair not in links
        links.append(pair);neighbors[u].add(w);neighbors[w].add(u)
    assert all(len(n)==2 for n in neighbors.values()),'Edge link is open or nonmanifold'
    todo=[next(iter(neighbors))];seen=set()
    while todo:
        u=todo.pop()
        if u not in seen:seen.add(u);todo.extend(neighbors[u]-seen)
    assert len(seen)==len(neighbors),'Disconnected edge link'
    old_boundary=boundary(cells)
    assert all(not (a in face and b in face) for face in old_boundary),'Edge reaches cavity boundary'
    assert isinstance(fraction,Q) and 0<fraction<1,'Exact interior rational fraction required'
    exact_point=[Q(float(v[a,j]))+(Q(float(v[b,j]))-Q(float(v[a,j])))*fraction for j in range(3)]
    midpoint=v[[a,b]].mean(axis=0) if fraction==Q(1,2) else np.array([float(x) for x in exact_point])
    assert np.isfinite(midpoint).all(), 'Nonfinite midpoint'
    assert all(Q(float(midpoint[j]))==exact_point[j] for j in range(3)), 'Rounded edge point leaves the exact parent edge'
    assert not any(np.array_equal(midpoint,v[x]) for x in set(cells.flat)), 'Midpoint duplicates cavity vertex'
    output=[]
    for row in cells:
        left=row.copy();right=row.copy();left[left==b]=new_node_id;right[right==a]=new_node_id
        output.extend([left,right])
    output=np.asarray(output,dtype=np.int64)
    assert boundary(output)==old_boundary,'Cavity boundary roster changed'
    old_volumes=[volume(v[row]) for row in cells]
    new_volumes=[volume([midpoint if int(i)==new_node_id else v[i] for i in row]) for row in output]
    assert all(x>0 for x in old_volumes),'Nonpositive parent tetrahedron'
    assert all(0<x<=volume_cap for x in new_volumes),'Candidate volume or orientation refused'
    assert sum(old_volumes)==sum(new_volumes),'Exact cavity volume differs'
    assert all(new_volumes[2*i]==fraction*parent and new_volumes[2*i+1]==(1-fraction)*parent for i,parent in enumerate(old_volumes)),'Exact per-parent partition differs'
    return midpoint,output,dict(status='local_interior_edge_refinement_proposal_checked',
        fraction=str(fraction),exact_per_parent_partition_preserved=True,source_cells=len(cells),candidate_cells=len(output),boundary_faces=len(old_boundary),
        exact_cavity_volume_preserved=True,old_vertices_unmodified=True,
        maximum_candidate_volume_mm3=float(max(new_volumes)),global_mesh_accepted=False,
        scope='Closed local edge-star candidate. Whole assembly and mechanical comparison remain mandatory.')
