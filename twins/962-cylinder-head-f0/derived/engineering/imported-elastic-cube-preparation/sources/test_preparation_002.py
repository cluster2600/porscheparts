"""Prepared stdlib-only elastic-case/format/held guards; no actual cube data read."""
import ast,copy,hashlib,json,math,struct,sys,tempfile,time,unittest
from fractions import Fraction as F
from pathlib import Path
PREP=Path(__file__).resolve().parent
SOURCE=PREP/'prepare_mesh.py'
SOURCE_SHA='d039e18b7194305e25d5b046a3b95128ad6513228fb80dec4853039203f662d3'
if hashlib.sha256(SOURCE.read_bytes()).hexdigest()!=SOURCE_SHA:raise ValueError('Frozen adapter source changed')
TREE=ast.parse(SOURCE.read_text());FN={n.name:n for n in TREE.body if isinstance(n,ast.FunctionDef)}
def selected(names,extra=None):
 ns=dict(math=math,struct=struct,F=F,Path=Path,hashlib=hashlib,json=json,time=time,sys=sys)
 if extra:ns.update(extra)
 exec(compile(ast.Module(body=[FN[n] for n in names],type_ignores=[]),str(SOURCE),'exec'),ns)
 return ns
class HeldElasticGuards(unittest.TestCase):
 def state(self):
  return dict(node_tags=list(range(1,16)),coordinates_mm=[[float(i),0.,0.] for i in range(15)],tetra_tags=list(range(101,141)),tetra_node_tags=[[1,2,3,4] for _ in range(40)],native_qualities={k:[1.]*40 for k in ['SICN','Jacobian','native_volume_mm3']},independent_signed_volume_mm3=[1.]*40)
 def test_exact_fictitious_elastic_reference_and_shear_energy(self):
  c=json.loads((PREP/'affine-card.json').read_text());E=F(c['material']['young_modulus_MPa']);nu=F(str(c['material']['poisson_ratio']));A=[[F(x) for x in row] for row in c['affine_gradient_A']]
  self.assertEqual(A,[[F(x) for x in row] for row in c['exact_constant_strain']]);self.assertEqual(A,[list(x) for x in zip(*A)])
  mu=E/(2*(1+nu));lam=E*nu/((1+nu)*(1-2*nu));tr=sum(A[i][i] for i in range(3));stress=[[2*mu*A[i][j]+(lam*tr if i==j else 0) for j in range(3)] for i in range(3)]
  self.assertEqual(stress,[[F(x) for x in row] for row in c['exact_constant_stress_MPa']]);self.assertEqual(stress[0][1],F(100,3));self.assertEqual(stress[1][2],50)
  U=sum(A[i][j]*stress[i][j] for i in range(3) for j in range(3))*F(343,2)
  self.assertEqual(U,F(2523451,28800));self.assertEqual(F(c['exact_total_elastic_energy_N_mm']),U);self.assertEqual(F(c['exact_boundary_work_N_mm']),2*U)
  self.assertFalse(c['material']['thermal_constants_required_or_added']);self.assertEqual(c['quadrature']['qp_ids'],[0]);self.assertEqual(c['expected_geometry']['genuine_free_displacement_DOFs'],21)
 def test_format_roundtrip_checks_all52_elements_and_coordinate_signed_zero(self):
  ns=selected(['need','bits','ascii22','verify_ascii']);state=self.state();state['coordinates_mm'][0][0]=-0.0
  ref=dict(node_tags=state['node_tags'],coordinates_mm=state['coordinates_mm'],tetrahedron_tags=state['tetra_tags'],positive_tetrahedra_node_tags=state['tetra_node_tags'],triangle_tags=list(range(201,213)),outward_triangles_node_tags=[[1,2,3]]*12)
  text=ns['ascii22'](ref);self.assertTrue(ns['verify_ascii'](text,ref))
  changed=text.replace('1 -0 0 0','1 0 0 0',1)
  with self.assertRaisesRegex(ValueError,'coordinate bits'):ns['verify_ascii'](changed,ref)
  lines=text.splitlines();lines[79]=lines[79].replace('1 2 3 4','1 3 2 4');changed='\n'.join(lines)+'\n'
  with self.assertRaises(ValueError):ns['verify_ascii'](changed,ref)
 def test_complete_typed_arrays_reject_shapes_duplicate_tags_nonfinite_and_badindices(self):
  ns=selected(['need','bits','typed']);self.assertEqual(len(ns['typed'](self.state())),8)
  for mutate in [lambda s:s['node_tags'].__setitem__(1,1),lambda s:s['tetra_tags'].pop(),lambda s:s['coordinates_mm'][0].__setitem__(0,float('nan')),lambda s:s['tetra_node_tags'][0].__setitem__(0,999),lambda s:s['native_qualities']['SICN'].pop(),lambda s:s['node_tags'].__setitem__(0,True)]:
   data=self.state();mutate(data)
   with self.assertRaises(ValueError):ns['typed'](data)
 def test_saved_reopen_difference_is_not_accepted_as_exact_source(self):
  ns=selected(['need','bits','typed','reference']);s=self.state();payload={k:copy.deepcopy(s) for k in ['before','after_geometry_flag','after','saved_reopen']}
  payload['saved_reopen']['coordinates_mm'][1][2]=-0.0
  with self.assertRaisesRegex(ValueError,'saved-reopen'):ns['reference'](payload,{})
 def test_held_adapter_refuses_before_source_or_geometry_reads(self):
  with tempfile.TemporaryDirectory() as temp:
   p=Path(temp).resolve()/'held.json';p.write_text(json.dumps({'adapter_launch_authorized':False}));h=hashlib.sha256(p.read_bytes()).hexdigest();ns=selected(['need','sha','main'])
   with self.assertRaisesRegex(ValueError,'HELD'):ns['main'](p,h)
 def test_deck_reuses_threeDOF_material_sampler_and_exact_owned_runner(self):
  deck=(PREP/'imported-cube_002.i').read_text()
  self.assertEqual(hashlib.sha256((PREP/'run_cube.py').read_bytes()).hexdigest(),'65bdce7e329f584c69e3eff1b18205b143811b6cc3d5c354df1d7dd2bb877b31')
  self.assertIn('type = FileMeshGenerator',deck);self.assertNotIn('GeneratedMesh',deck);self.assertEqual(deck.count('boundary = all_boundary'),3)
  for item in ['youngs_modulus = 210000','poissons_ratio = 0.26',"save_in = 'rx ry rz'",'type = RankTwoTensorMaterialADConverter','type = ElementMaterialSampler',"variable = 'disp_x disp_y disp_z rx ry rz'",'order = FIRST','element_order = FIRST','side_order = FIRST','gmres hypre boomeramg V 1 0 30','line_search = none']:
   self.assertIn(item,deck)
  self.assertNotIn('eigenstrain',deck);self.assertNotIn('yield_stress',deck);self.assertIn('preset = false',deck)
  for item in ['nl_rel_tol = 1e-11','nl_abs_tol = 1e-10','l_tol = 1e-11','l_abs_tol = 1e-12']:
   self.assertIn(item,deck)
if __name__=='__main__':unittest.main()
