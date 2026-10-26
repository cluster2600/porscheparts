"""Private CFD trial using the independently envelope-checked flip candidate."""
import hashlib,importlib.util,json,sys
from pathlib import Path
import numpy as np,trimesh

root=Path.cwd();source=root/'twins/935-horizontal-cooling-system-f0/source';sys.path.insert(0,str(source))
spec=importlib.util.spec_from_file_location('wall',source/'reference-fluid-wall-study-20261022/compose-reference-wall-001.py')
wall=importlib.util.module_from_spec(spec);spec.loader.exec_module(wall)
trial=root/'work/935-cfd-root0p7-20261026-flips';candidate=trial/'candidate.off'
parent=root/'work/935-cfd-mesh-correction-20261022/prepared-concavity20-001/boundary.npz'
assert wall.sha(candidate)=='59118742062e1c16eaf77217c7257ad636f4d16e685eebaa13c65ab11ba0a163'
assert wall.sha(parent)=='67835eacd4d1c7f9736b5fc826979f8ad48366397b422e672043ef720c027f86'
envelope=json.loads((trial/'envelope.stdout').read_text())
assert envelope['complete_containment_pass'] and envelope['topology_and_self_intersection_checks_pass']
mesh=trimesh.load_mesh(candidate,process=False);rv=np.asarray(mesh.vertices)*.001;rf=np.asarray(mesh.faces)
assert len(rv)==439365 and len(rf)==878730 and mesh.is_watertight and mesh.is_winding_consistent
out=root/'work/935-cfd-root0p7-20261026-flipped-plc';out.mkdir(exist_ok=False)
with (out/'rotor.obj').open('x') as stream:
    np.savetxt(stream,rv,fmt='v %.17g %.17g %.17g')
    np.savetxt(stream,rf+1,fmt='f %d %d %d')
readback=trimesh.load_mesh(out/'rotor.obj',process=False)
assert np.array_equal(readback.vertices,rv) and np.array_equal(readback.faces,rf)
with np.load(parent) as z:
    hole=z['hole'].copy();v,f,tags,volume=wall.compose(z['vertices'],z['triangles'],z['markers'],rv,rf,hole)
np.savez_compressed(out/'boundary.npz',vertices=v,triangles=f,markers=tags,hole=hole)
with (out/'fluid.smesh').open('x') as stream:
    stream.write(f'{len(v)} 3 0 0\n');np.savetxt(stream,np.column_stack([np.arange(len(v)),v]),fmt=['%d','%.17g','%.17g','%.17g'])
    stream.write(f'{len(f)} 1\n');np.savetxt(stream,np.column_stack([np.full(len(f),3),f,tags]),fmt='%d')
    stream.write('1\n0 '+' '.join(f'{x:.17g}' for x in hole)+'\n0\n')
receipt={'status':'closed_flipped_exploratory_PLC_pending_volume_quality','source_sha256':wall.sha(__file__),'candidate_off_sha256':wall.sha(candidate),'envelope_result_sha256':wall.sha(trial/'envelope.stdout'),'parent_boundary_sha256':wall.sha(parent),'rotor_OBJ_sha256':wall.sha(out/'rotor.obj'),'vertices':len(v),'triangles':len(f),'volume_m3':volume,'hole':hole.tolist(),'scale_verified':False,'CFD_accepted':False,'output_sha256':{'boundary.npz':wall.sha(out/'boundary.npz'),'fluid.smesh':wall.sha(out/'fluid.smesh')}}
wall.save(out/'receipt.json',receipt);print(json.dumps(receipt),flush=True)
