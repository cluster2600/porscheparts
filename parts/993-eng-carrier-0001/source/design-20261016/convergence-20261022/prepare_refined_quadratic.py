"""Convert the exact-positive nested refined mesh into shared-edge quadratic geometry."""
import argparse
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
from pathlib import Path
import resource
import signal

EDGES=[(0,1),(1,2),(0,2),(0,3),(1,3),(2,3)]


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--volume',type=Path,required=True);p.add_argument('--refinement-proof',type=Path,required=True);p.add_argument('--exact-audit',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    a.output.mkdir(parents=True);resource.setrlimit(resource.RLIMIT_CPU,(180,190));signal.alarm(210)
    import numpy as np
    refinement=json.loads(a.refinement_proof.read_text());audit=json.loads(a.exact_audit.read_text())
    if sha(a.volume)!=refinement['output_sha256']['transport.npz']or audit['status']!='full_exact_orientation_and_indexed_volume_screens_passed'or sha(a.volume)not in audit['source_sha256'].values():raise ValueError('Matching complete refined volume audit required')
    if not refinement['all_parent_nodes_and_midsides_unchanged']or not refinement['continuous_tractions_unchanged']:raise ValueError('Retained refinement provenance required')
    source=Path(__file__).parents[1]/'resume-20261020/prepare_tetgen_mechanics_ccx.py';spec=importlib.util.spec_from_file_location('_retained_ccx_codec',source);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
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
    report=dict(status='matched_C3D4_C3D10_geometry_prepared_Jacobian_audit_pending',source_volume_sha256=sha(a.volume),linear_nodes=parent_nodes,quadratic_nodes=len(vertices),elements=len(cells),boundary_faces=len(boundary),complete_corner_transport_L1_bound_mm=str(maximum_corner_error),whole_surface_reference_distance_upper_mm=refinement['whole_surface_distance_upper_mm'],edge_order=EDGES,source_sha256={str(p):sha(p)for p in [a.volume,a.refinement_proof,a.exact_audit,source,Path(__file__)]},output_sha256={p.name:sha(p)for p in a.output.iterdir()if p.is_file()},geometry_adopted=False)
    (a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');signal.alarm(0);print(json.dumps({k:report[k]for k in ['status','linear_nodes','quadratic_nodes','elements']}))

if __name__=='__main__':main()
