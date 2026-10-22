"""Compose the bounded repaired rotor with the retained conditional outer duct."""
import importlib.util,json,signal
from pathlib import Path
import numpy as np
import trimesh
from prepare_conforming_surface import load_surface
from prepare_foundation13_rotor import write_si_obj
from run_reconstruction import fresh,read_obj,save,sha

signal.alarm(300)
root=Path.cwd();phase=root/'work/935-surface-facet-repair-20261022';accepted=phase/'accepted-005';proof=json.loads((accepted/'assessment.json').read_text())
assert proof['status']=='quantized_candidate_full_topology_readback_and_both_independent_bounds_passed' and proof['complete_surface_bound_established']
for name,expected in proof['output_sha256'].items():assert sha(accepted/name)==expected
v,f=load_surface(accepted/'candidate.npz',proof['output_sha256']['candidate.npz'],accepted/'candidate.stl',proof['output_sha256']['candidate.stl'])
helper=root/'twins/935-horizontal-cooling-system-f0/source/reference-fluid-wall-study-20261022/compose-reference-wall-001.py';assert sha(helper)=='0a5db30edae38e2ba6845d05637fba21de87646083ebe2350f3e4cc795ab1c97'
spec=importlib.util.spec_from_file_location('frozen_reference_wall',helper);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
old_off=phase/'diagnostic-inputs/reference.off';old_obj=root/'work/935-cfd-pilot-20261022/rotor-001/coarse/constant/triSurface/rotor.obj';assert sha(old_off)=='addba09e1ee2d7814f19a3262ac0910f0bc5b9d58dd43ada3254444845392e5a' and sha(old_obj)=='5eb9ee8a73b140198013fe511916c150316acc8e31174a2ca1fea4bac4db3e44'
reference=trimesh.load_mesh(old_off,process=False);ov,of,_=read_obj(old_obj);lookup={tuple(x):i for i,x in enumerate(ov)};assert len(lookup)==len(ov)
mapping=np.array([lookup[tuple(x)] for x in np.asarray(reference.vertices,dtype=float)*.001]);assert len(np.unique(mapping))==len(ov)
a=np.sort(mapping[np.asarray(reference.faces)],axis=1);b=np.sort(of,axis=1);order=lambda x:np.lexsort(x.T[::-1]);assert np.array_equal(a[order(a)],b[order(b)])
parent=root/'work/935-cfd-mesh-correction-20261022/prepared-concavity20-001';assert sha(parent/'boundary.npz')=='67835eacd4d1c7f9736b5fc826979f8ad48366397b422e672043ef720c027f86'
out=fresh(phase/'prepared-fluid-001');write_si_obj(out/'rotor-si.obj',v,f);rv,rf,_=read_obj(out/'rotor-si.obj');assert np.array_equal(rv,v.astype(float)*.001) and np.array_equal(rf,f)
with np.load(parent/'boundary.npz') as z:hole=z['hole'].copy();points,triangles,markers,volume=module.compose(z['vertices'],z['triangles'],z['markers'],rv,rf,hole)
np.savez_compressed(out/'boundary.npz',vertices=points,triangles=triangles,markers=markers,hole=hole)
with (out/'boundary.obj').open('x') as s:np.savetxt(s,points,fmt='v %.17g %.17g %.17g');np.savetxt(s,triangles+1,fmt='f %d %d %d')
with (out/'fluid.smesh').open('x') as s:
    s.write(f'{len(points)} 3 0 0\n');np.savetxt(s,np.column_stack([np.arange(len(points)),points]),fmt=['%d','%.17g','%.17g','%.17g']);s.write(f'{len(triangles)} 1\n');np.savetxt(s,np.column_stack([np.full(len(triangles),3),triangles,markers]),fmt='%d');s.write('1\n0 '+' '.join(f'{x:.17g}' for x in hole)+'\n0\n')
r={'status':'bounded_repaired_rotor_PLC_pending_exact_intersection_and_volume_audits','source_sha256':sha(__file__),'reused_compose_source_sha256':sha(helper),'accepted_geometry_assessment_sha256':sha(accepted/'assessment.json'),'complete_original_and_reference_bounds_passed':True,'original_master_bound_native_units':.0225,'reserved_numeric_margin_native_units':.0025,'parent_boundary_sha256':sha(parent/'boundary.npz'),'baseline_SI_conversion_complete_coordinate_triangle_bijection':True,'repaired_SI_OBJ_exact_coordinate_and_triangle_readback':True,'boundary_vertices':len(points),'triangles':len(triangles),'rotor_vertices':len(rv),'rotor_triangles':len(rf),'outer_boundary_coordinates_triangles_markers_unchanged':True,'volume_m3':volume,'source_unit_m_per_uncalibrated_unit_assumed':.001,'actual_935_housing_defined':False,'scale_verified':False,'CFD_accepted':False,'manufacturing_authorized':False,'output_sha256':{name:sha(out/name) for name in ['boundary.npz','boundary.obj','fluid.smesh','rotor-si.obj']}}
save(out/'receipt.json',r);print(json.dumps(r),flush=True)
