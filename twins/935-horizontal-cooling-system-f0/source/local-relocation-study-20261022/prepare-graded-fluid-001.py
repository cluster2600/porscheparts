"""Compose the certified relocated rotor and a conditional nodal mesh-size field."""
import importlib.util
import json
import signal
import sys

import numpy as np
import trimesh
from prepare_conforming_surface import load_surface
from prepare_foundation13_rotor import write_si_obj
from run_reconstruction import ROOT, fresh, read_obj, save, sha

signal.alarm(180)
sys.path.insert(0,str(ROOT/'twins/935-horizontal-cooling-system-f0/source/local-relocation-study-20261022'))
from graded_size import nodal_sizes

phase=ROOT/'work/935-local-relocation-20261022';candidate=phase/'candidate-002';proposal=json.loads((candidate/'proposal.json').read_text());bounds=json.loads((phase/'bounds-002/assessment.json').read_text())
assert bounds['complete_surface_bound_established'] and bounds['inputs_sha256']['/home/lolman/935-local-relocation-20261022/candidate-002/candidate.off']==sha(candidate/'candidate.off')==proposal['output_sha256']['candidate.off']
v,f=load_surface(candidate/'candidate.npz',proposal['output_sha256']['candidate.npz'],candidate/'candidate.stl',proposal['output_sha256']['candidate.stl'])
off=trimesh.load_mesh(candidate/'candidate.off',process=False);assert np.array_equal(off.vertices,v.astype(float)) and np.array_equal(off.faces,f)
helper=ROOT/'twins/935-horizontal-cooling-system-f0/source/reference-fluid-wall-study-20261022/compose-reference-wall-001.py';assert sha(helper)=='0a5db30edae38e2ba6845d05637fba21de87646083ebe2350f3e4cc795ab1c97'
spec=importlib.util.spec_from_file_location('retained_reference_wall',helper);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
parent=ROOT/'work/935-cfd-mesh-correction-20261022/prepared-concavity20-001/boundary.npz';assert sha(parent)=='67835eacd4d1c7f9736b5fc826979f8ad48366397b422e672043ef720c027f86'
out=fresh(phase/'graded-prepared-001');write_si_obj(out/'rotor-si.obj',v,f);rv,rf,_=read_obj(out/'rotor-si.obj');assert np.array_equal(rv,v.astype(float)*.001) and np.array_equal(rf,f)
with np.load(parent) as z:
    hole=z['hole'].copy();points,triangles,markers,volume=module.compose(z['vertices'],z['triangles'],z['markers'],rv,rf,hole)
np.savez_compressed(out/'boundary.npz',vertices=points,triangles=triangles,markers=markers,hole=hole)
with (out/'boundary.obj').open('x') as stream:np.savetxt(stream,points,fmt='v %.17g %.17g %.17g');np.savetxt(stream,triangles+1,fmt='f %d %d %d')
with (out/'fluid.smesh').open('x') as stream:
    stream.write(f'{len(points)} 3 0 0\n');np.savetxt(stream,np.column_stack([np.arange(len(points)),points]),fmt=['%d','%.17g','%.17g','%.17g']);stream.write(f'{len(triangles)} 1\n');np.savetxt(stream,np.column_stack([np.full(len(triangles),3),triangles,markers]),fmt='%d');stream.write('1\n0 '+' '.join(f'{x:.17g}' for x in hole)+'\n0\n')
sizes=nodal_sizes(points,triangles,markers)
with (out/'fluid.mtr').open('x') as stream:stream.write(f'{len(points)} 1\n');np.savetxt(stream,sizes,fmt='%.17g')
record={'status':'certified_rotor_PLC_with_conditional_nodal_size_field','source_sha256':sha(__file__),'compose_helper_sha256':sha(helper),'size_helper_sha256':sha(ROOT/'twins/935-horizontal-cooling-system-f0/source/local-relocation-study-20261022/graded_size.py'),'surface_bounds_sha256':sha(phase/'bounds-002/assessment.json'),'input_surface_npz_sha256':sha(candidate/'candidate.npz'),'boundary_vertices':len(points),'triangles':len(triangles),'rotor_triangles':len(rf),'volume_m3':volume,'nodal_size_field':{'near_m':.001,'far_m':.015,'growth':.2,'distance_definition':'nearest input rotor vertex; piecewise linear metric interpolation by TetGen','minimum_m':float(sizes.min()),'maximum_m':float(sizes.max())},'assumed_m_per_uncalibrated_source_unit':.001,'boundary_retriangulation_requires_complete_independent_certificate':True,'scale_verified':False,'CFD_accepted':False,'manufacturing_authorized':False,'output_sha256':{name:sha(out/name) for name in ['boundary.npz','boundary.obj','fluid.smesh','fluid.mtr','rotor-si.obj']}}
save(out/'receipt.json',record);print(json.dumps(record),flush=True)
