"""Build a new T10 space after an exact oriented-boundary transfer to the retained reference."""
import argparse
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
from pathlib import Path
import resource
import signal
import math
import numpy as np

EDGES=[(0,1),(1,2),(0,2),(0,3),(1,3),(2,3)]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def oriented_boundary(vertices,faces):
    result=[]
    for face in faces:
        p=tuple(map(tuple,vertices[face]))
        result.append(min(p,p[1:]+p[:1],p[2:]+p[:2]))
    return sorted(result)


def inherited_bound(candidate_vertices,candidate_faces,reference_vertices,reference_faces,record):
    if oriented_boundary(candidate_vertices,candidate_faces)!=oriented_boundary(reference_vertices,reference_faces):
        raise ValueError('Complete oriented reference boundary differs')
    bound=Q(float(record['whole_surface_reference_distance_upper_mm']))+Q(record['complete_corner_transport_L1_bound_mm'])
    rounded=float(bound)
    if Q(rounded)<bound:rounded=math.nextafter(rounded,math.inf)
    return rounded


def main():
    p=argparse.ArgumentParser(__doc__)
    for name in ['volume','exact-audit','reference-geometry','reference-mapping','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    audit=json.loads(a.exact_audit.read_text());record=json.loads((a.reference_geometry/'assessment.json').read_text());proof=json.loads(a.reference_mapping.read_text())
    if audit['status']!='full_exact_orientation_and_indexed_volume_screens_passed'or sha(a.volume)not in audit['source_sha256'].values():raise ValueError('Matching exact candidate volume audit required')
    if proof['status']!='complete_C3D10_mapping_and_geometry_budget_passed'or not proof['whole_simplex_and_whole_homotopy_positive']:raise ValueError('Accepted complete reference mapping required')
    for name in ['linear.npz','quadratic.npz']:
        if sha(a.reference_geometry/name)!=record['output_sha256'][name]:raise ValueError('Reference geometry identity differs')
    if sha(a.reference_geometry/'quadratic.npz')not in proof['source_sha256'].values()or sha(a.reference_geometry/'assessment.json')not in proof['source_sha256'].values():raise ValueError('Source-bound reference mapping required')
    with np.load(a.volume,allow_pickle=False)as data:vertices=data['vertices'].copy();faces=data['boundary'].copy()
    with np.load(a.reference_geometry/'linear.npz',allow_pickle=False)as data:reference=data['vertices'].copy();reference_faces=data['boundary'].copy()
    with np.load(a.reference_geometry/'quadratic.npz',allow_pickle=False)as data:reference_quadratic=data['vertices'].copy();reference_quadratic_faces=data['boundary'].copy()
    if not np.array_equal(reference,reference_quadratic[:len(reference)])or not np.array_equal(reference_faces,reference_quadratic_faces[:,:3]):raise ValueError('Reference linear and quadratic boundaries differ')
    bound=inherited_bound(vertices,faces,reference,reference_faces,record)
    if bound>.06:raise ValueError('Inherited geometry budget exhausted')
    a.output.mkdir(parents=True);resource.setrlimit(resource.RLIMIT_CPU,(180,190));signal.alarm(210)
    source=Path(__file__).parents[1]/'resume-20261020/prepare_tetgen_mechanics_ccx.py';spec=importlib.util.spec_from_file_location('_unchanged_ccx_numeric_codec',source);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    with np.load(a.volume,allow_pickle=False)as data:corners=data['vertices'].copy();cells=data['tetrahedra'].copy();boundary=data['boundary'].copy()
    parent_nodes=len(corners);edge_pairs=np.concatenate([np.sort(cells[:,[i,j]],axis=1)for i,j in EDGES]);unique,inverse=np.unique(edge_pairs,axis=0,return_inverse=True);del edge_pairs
    node_pairs=parent_nodes+inverse.reshape(6,-1).T;quadratic=np.column_stack([cells,node_pairs]);del inverse
    midpoint=(corners[unique[:,0]]+corners[unique[:,1]])/2;vertices=np.vstack([corners,midpoint]);transport=vertices.copy();maximum_corner_error=Q(0)
    with(a.output/'mesh-P1.inp').open('w')as p1,(a.output/'mesh-P2.inp').open('w')as p2:
        for stream in [p1,p2]:stream.write('** Matched mechanics geometry; all input numeric fields <=20 characters\n*NODE,NSET=ALLN\n')
        for i,row in enumerate(vertices):
            tokens=[module.ccx_field(x)for x in row];parsed=list(map(float,tokens));transport[i]=parsed;line=str(i+1)+','+','.join(tokens)+'\n';p2.write(line)
            if i<parent_nodes:
                p1.write(line);cost=sum(abs(Q(float(x))-Q(float(y)))for x,y in zip(row,parsed));maximum_corner_error=max(maximum_corner_error,cost)
        p1.write('*ELEMENT,TYPE=C3D4,ELSET=BODY\n');p2.write('*ELEMENT,TYPE=C3D10,ELSET=BODY\n')
        for i,(linear,higher)in enumerate(zip(cells,quadratic),1):p1.write(str(i)+','+','.join(str(int(x)+1)for x in linear)+'\n');p2.write(str(i)+','+','.join(str(int(x)+1)for x in higher)+'\n')
    keys=unique[:,0]*parent_nodes+unique[:,1];surface_mid=[]
    for i,j in [(0,1),(1,2),(2,0)]:
        pair=np.sort(boundary[:,[i,j]],axis=1);code=pair[:,0]*parent_nodes+pair[:,1];index=np.searchsorted(keys,code)
        if not np.array_equal(keys[index],code):raise ValueError('A complete boundary edge is missing')
        surface_mid.append(parent_nodes+index)
    quadratic_boundary=np.column_stack([boundary,*surface_mid])
    np.savez_compressed(a.output/'linear.npz',vertices=transport[:parent_nodes],tetrahedra=cells,boundary=boundary)
    np.savez_compressed(a.output/'quadratic.npz',vertices=transport,tetrahedra=quadratic,boundary=quadratic_boundary)
    report=dict(status='matched_C3D4_C3D10_geometry_prepared_Jacobian_audit_pending',source_volume_sha256=sha(a.volume),linear_nodes=parent_nodes,quadratic_nodes=len(vertices),elements=len(cells),boundary_faces=len(boundary),complete_corner_transport_L1_bound_mm=str(maximum_corner_error),whole_surface_reference_distance_upper_mm=float(bound),edge_order=EDGES,source_sha256={str(p):sha(p)for p in [a.volume,a.exact_audit,a.reference_geometry/'assessment.json',a.reference_geometry/'linear.npz',a.reference_geometry/'quadratic.npz',a.reference_mapping,source,Path(__file__)]},output_sha256={p.name:sha(p)for p in a.output.iterdir()if p.is_file()},geometry_adopted=False)
    report['complete_oriented_reference_boundary_identity']=True
    report['inherited_linear_surface_distance_bound_mm']=bound
    report['scope']='Replacement interior connectivity; unchanged oriented exterior before fresh numeric transport; not nested refinement or new mechanical results'
    (a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');signal.alarm(0);print(json.dumps({k:report[k]for k in ['status','linear_nodes','quadratic_nodes','elements']}))

if __name__=='__main__':main()
