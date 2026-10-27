"""Audit complete boundary markers, connectivity and exact signed tetra volumes."""
import json,sys,time
from pathlib import Path
from fractions import Fraction
import numpy as np
from import_conforming_volume import ROOT,table,exact_orientation,integer_points,determinant,helper
from prepare_conforming_surface import sha
from run_reconstruction import fresh,save
prepared,meshed,output=map(Path,sys.argv[1:]);t=time.monotonic();proof=json.loads((meshed/'execution.json').read_text());assert proof['exit']==0 and proof['stop_reason'] is None and proof['input_file_unchanged']
reference_proof=json.loads((prepared/'receipt.json').read_text());assert sha(prepared/'boundary.npz')==reference_proof['output_sha256']['boundary.npz'];assert sha(prepared/'fluid.smesh')==reference_proof['output_sha256']['fluid.smesh']==proof['input_smesh_sha256']==sha(meshed/'fluid.smesh')
z=np.load(prepared/'boundary.npz');reference=z['vertices'];surface=z['triangles'];source_markers=z['markers'];vertices=table(meshed/'fluid.1.node','node');cells=table(meshed/'fluid.1.ele','ele')
with (meshed/'fluid.1.face').open() as stream:
 head=list(map(int,stream.readline().split()));assert len(head)==2 and head[1]==1 and 0<head[0]<20_000_000;data=np.loadtxt(stream,dtype=np.int64,ndmin=2)
assert data.shape==(head[0],5) and np.array_equal(data[:,0],np.arange(len(data))) and set(np.unique(data[:,4]))<={0,1,2,3,4}
boundary=data[data[:,4]>0,1:4];markers=data[data[:,4]>0,4];assert len(boundary)==len(surface)
lookup={tuple(p):i for i,p in enumerate(reference)};assert len(lookup)==len(reference)
map_ids={int(i):lookup[tuple(vertices[i])] for i in np.unique(boundary)}
mapped=np.array([[map_ids[int(i)] for i in tri] for tri in boundary]);a=np.sort(surface,axis=1);b=np.sort(mapped,axis=1);order=lambda x:np.lexsort((x[:,2],x[:,1],x[:,0]));sa=order(a);sb=order(b)
assert np.array_equal(a[sa],b[sb]) and np.array_equal(source_markers[sa],markers[sb])
checker=ROOT/'twins/m64-cylinder-head/source/wholebody/audit_indexed_tetrahedra.py';topology=helper(checker,'_935_fluid_connectivity').connectivity_metrics(vertices,cells,boundary)
exact=exact_orientation(vertices,cells);integers,scale=integer_points(reference);zero=(0,0,0);surface_integer=sum(determinant(zero,*(integers[int(j)] for j in tri)) for tri in surface);surface_volume=Fraction(surface_integer,6*scale**3)
assert not exact['negative'] and not exact['zero'] and Fraction(exact['signed_volume_exact'])==surface_volume
assert topology['boundary_matches'] and topology['tetra_connected_components']==1 and topology['repeated_node_tetrahedra']==0
out=fresh(output);np.savez_compressed(out/'volume.npz',vertices=vertices,tetrahedra=cells,boundary=boundary,markers=markers)
report={'status':'all_cells_and_boundary_markers_audited','source_sha256':sha(__file__),'helper_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [Path(sys.modules['import_conforming_volume'].__file__),checker]},'prepared_receipt_sha256':sha(prepared/'receipt.json'),'execution_sha256':sha(meshed/'execution.json'),'vertices':len(vertices),'tetrahedra':len(cells),'boundary_triangles':len(boundary),'complete_boundary_coordinate_triangle_marker_bijection':True,'exact_cell_orientation':exact,'exact_PLC_volume_equal':True,'fluid_volume_m3':float(surface_volume),'indexed_connectivity':topology,'CFD_quality_admitted':False,'CFD_accepted':False,'manufacturing_authorized':False,'volume_npz_sha256':sha(out/'volume.npz'),'elapsed_s':time.monotonic()-t}
save(out/'assessment.json',report);print(json.dumps(report),flush=True)
