"""Split only tetrahedra with multiple boundary faces; preserve every surface triangle."""
import hashlib, json, shutil, sys
from pathlib import Path
import numpy as np
from import_conforming_volume import exact_orientation
from run_reconstruction import fresh

def children(vertices, cells, selected):
    centre = vertices[cells[selected]].mean(axis=1)
    ids = np.arange(len(vertices), len(vertices)+len(centre))
    pieces = np.concatenate([np.column_stack([cells[selected][:, face], ids]) for face in [[1,2,3],[0,3,2],[0,1,3],[0,2,1]]])
    result = np.vstack([vertices, centre]); t = result[pieces]
    signed = np.einsum('ij,ij->i', t[:,1]-t[:,0], np.cross(t[:,2]-t[:,0],t[:,3]-t[:,0]))
    assert np.all(signed != 0)
    pieces[signed<0] = pieces[signed<0][:,[1,0,2,3]]
    return result, np.vstack([cells[~selected], pieces])

control_vertices = np.array([[0.,0,0],[1,0,0],[0,1,0],[0,0,1]])
v, c = children(control_vertices, np.array([[0,1,2,3]]), np.array([True]))
control = exact_orientation(v,c)
assert control['signed_volume_exact'] == '1/6' and not control['negative'] and not control['zero'] and len(c)==4

prepared, audited, output = map(Path,sys.argv[1:]); sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
proof=json.loads((audited/'assessment.json').read_text());assert proof['volume_npz_sha256']==sha(audited/'volume.npz') and proof['complete_boundary_coordinate_triangle_marker_bijection']
z=np.load(audited/'volume.npz');vertices=z['vertices'];cells=z['tetrahedra'];boundary=z['boundary'];markers=z['markers']
all_faces=np.sort(cells[:,[[1,2,3],[0,3,2],[0,1,3],[0,2,1]]].reshape(-1,3),axis=1)
_,inverse,counts=np.unique(all_faces,axis=0,return_inverse=True,return_counts=True)
assert np.all((counts==1)|(counts==2)) and int((counts==1).sum())==len(boundary)
boundary_count=(counts[inverse].reshape(-1,4)==1).sum(axis=1);selected=boundary_count>=2
assert selected.any()
vertices,new_cells=children(vertices,cells,selected)
out=fresh(output);shutil.copyfile(prepared/'fluid.smesh',out/'fluid.smesh')
with (out/'fluid.1.node').open('x') as stream:
    stream.write(f'{len(vertices)} 3 0 0\n');np.savetxt(stream,np.column_stack([np.arange(len(vertices)),vertices]),fmt=['%d','%.17g','%.17g','%.17g'])
with (out/'fluid.1.ele').open('x') as stream:
    stream.write(f'{len(new_cells)} 4 0\n');np.savetxt(stream,np.column_stack([np.arange(len(new_cells)),new_cells]),fmt='%d')
with (out/'fluid.1.face').open('x') as stream:
    stream.write(f'{len(boundary)} 1\n');np.savetxt(stream,np.column_stack([np.arange(len(boundary)),boundary,markers]),fmt='%d')
report={'status':'boundary_rank_subdivision_pending_full_audit','exit':0,'stop_reason':None,'input_file_unchanged':sha(out/'fluid.smesh')==sha(prepared/'fluid.smesh'),'input_smesh_sha256':sha(prepared/'fluid.smesh'),'source_sha256':sha(__file__),'parent_assessment_sha256':sha(audited/'assessment.json'),'cells_subdivided':int(selected.sum()),'input_cells':len(cells),'output_cells':len(new_cells),'input_boundary_faces_per_cell':{str(i):int((boundary_count==i).sum()) for i in range(5)},'unit_tetrahedron_exact_partition_control':control,'boundary_vertices_changed':False,'CFD_executed':False,'CFD_accepted':False,'manufacturing_authorized':False}
(out/'execution.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
