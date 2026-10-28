"""Export added interior mesh points while retaining every original vertex and boundary marker."""
import hashlib,json,shutil,sys
from pathlib import Path
import numpy as np
prepared,parent,proposal,out=map(Path,sys.argv[1:]);assert not out.exists();sha=lambda p:hashlib.file_digest(Path(p).open('rb'),'sha256').hexdigest()
receipt=json.loads((proposal/'receipt.json').read_text());assert receipt['candidate_sha256']==sha(proposal/'candidate.npz') and receipt['parent_assessment_sha256']==sha(parent/'assessment.json')
reference=json.loads((parent/'assessment.json').read_text());assert reference['volume_npz_sha256']==sha(parent/'volume.npz') and reference['prepared_receipt_sha256']==sha(prepared/'receipt.json')
old=np.load(parent/'volume.npz');new=np.load(proposal/'candidate.npz')
assert np.array_equal(old['vertices'],new['vertices'][:len(old['vertices'])]) and len(new['vertices'])>=len(old['vertices'])
assert all(np.array_equal(old[k],new[k]) for k in ['boundary','markers'])
assert np.isfinite(new['vertices']).all() and len(new['vertices'])<=1_000_000
cells=new['tetrahedra'];vertices=new['vertices'];assert cells.shape[1]==4 and cells.min()>=0 and cells.max()<len(vertices) and len(cells)<=2_000_000
out.mkdir(mode=0o700);shutil.copyfile(prepared/'fluid.smesh',out/'fluid.smesh')
for suffix,values,header,fmt in [('node',vertices,f'{len(vertices)} 3 0 0',['%d','%.17g','%.17g','%.17g']),('ele',cells,f'{len(cells)} 4 0','%d'),('face',np.column_stack([new['boundary'],new['markers']]),f"{len(new['boundary'])} 1",'%d')]:
    with (out/f'fluid.1.{suffix}').open('x') as stream:
        stream.write(header+'\n');np.savetxt(stream,np.column_stack([np.arange(len(values)),values]),fmt=fmt)
result={'status':'kernel_star_proposal_pending_independent_audit','source_sha256':sha(__file__),'proposal_receipt_sha256':sha(proposal/'receipt.json'),'input_smesh_sha256':sha(prepared/'fluid.smesh'),'input_file_unchanged':sha(out/'fluid.smesh')==sha(prepared/'fluid.smesh'),'exit':0,'stop_reason':None,'original_vertex_coordinates_unchanged':True,'boundary_marker_arrays_exactly_unchanged':True,'added_interior_mesh_points':len(new['vertices'])-len(old['vertices']),'CFD_accepted':False,'manufacturing_authorized':False};(out/'execution.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
