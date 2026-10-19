"""Small source/binding tests only; no CAD, sampling or render execution."""
import ast,copy,hashlib,importlib.util,json,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent;s=importlib.util.spec_from_file_location('_new_section_checks',HERE/'extract.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def fixture():
 points=[m.FOOT.copy(),[m.FOOT[0],m.FOOT[1],m.FOOT[2]+.1]];edges=[dict(edge_index=0,curve_type='test',points_xyz_mm=points)];old=dict(sections=[dict(role='before'),dict(role='after')],diagnostic_context={'known':'closed'},section_plane=m.plane())
 data=dict(cached_sections=copy.deepcopy(old['sections']),closed_reference_context=copy.deepcopy(old['diagnostic_context']),section_plane=m.plane(),candidate_BREP_sha256=m.CANDIDATE,taper_section=dict(role='taper',native_solids=1,edges=edges,edge_count=1,sampled_positions_sha256=m.coordinate_sha(edges),maximum_native_edge_tolerance_mm=1e-7),native_volume_methods=dict(adaptive_exact_binary64_equal_to_closed_reference=True,Gmsh_getMass_mm3=None),reference_ray_is_old_C1_only=True,new_ray_hits_computed=False,global_thickness_claimed=False,candidate_qualified=False)
 return data,old
class Tests(unittest.TestCase):
 def test_valid_new_profile(self):m.check_new(*fixture())
 def test_no_cached_profile_relabelling(self):
  d,o=fixture();d['cached_sections'][1]['role']='taper'
  with self.assertRaises(ValueError):m.check_new(d,o)
 def test_foreign_plane(self):
  d,o=fixture();d['section_plane']['origin_mm']=[0.,0.,0.]
  with self.assertRaises(ValueError):m.check_new(d,o)
 def test_foreign_candidate(self):
  d,o=fixture();d['candidate_BREP_sha256']='other'
  with self.assertRaises(ValueError):m.check_new(d,o)
 def test_coordinate_bytes_tampered(self):
  d,o=fixture();d['taper_section']['sampled_positions_sha256']='wrong'
  with self.assertRaises(ValueError):m.check_new(d,o)
 def test_nonfinite_drawing_point(self):
  d,o=fixture();d['taper_section']['edges'][0]['points_xyz_mm'][0][0]=float('nan')
  with self.assertRaises(ValueError):m.check_new(d,o)
 def test_no_new_ray_or_thickness_claim(self):
  for key in ('new_ray_hits_computed','global_thickness_claimed','candidate_qualified'):
   d,o=fixture();d[key]=True
   with self.assertRaises(ValueError):m.check_new(d,o)
 def test_actual_native_body_AST_preserved(self):
  old=ast.parse(m.OLD_PATH.read_text());e=next(n for n in old.body if isinstance(n,ast.FunctionDef)and n.name=='export');loop=next(n for n in e.body if isinstance(n,ast.For)and ast.unparse(n.target)=='(role, body)')
  new=ast.parse((HERE/'extract.py').read_text());f=next(n for n in new.body if isinstance(n,ast.FunctionDef)and n.name=='native_section');body=[n for n in f.body if not isinstance(n,ast.ImportFrom)][1:-1]
  self.assertEqual(ast.dump(ast.Module(body=body,type_ignores=[]),include_attributes=False),ast.dump(ast.Module(body=loop.body,type_ignores=[]),include_attributes=False))
 def test_no_old_CAD_import_or_reconstruction(self):
  tree=ast.parse((HERE/'extract.py').read_text());run=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='run')
  calls=[ast.unparse(n.func)for n in ast.walk(run)if isinstance(n,ast.Call)];self.assertEqual(calls.count('BRepTools.Read_s'),1);self.assertEqual(calls.count('native_section'),1);self.assertNotIn('STEPControl_Reader',ast.unparse(run));self.assertNotIn('BRepFilletAPI',ast.unparse(tree))
 def test_volume_evaluate_entire_authority_is_unchanged(self):
  self.assertEqual(m.sha(m.VOLUME_PATH),m.VOLUME_SHA)
  old=next(n for n in ast.parse(m.VOLUME_PATH.read_text()).body if isinstance(n,ast.FunctionDef)and n.name=='evaluate')
  import inspect
  actual=ast.parse(inspect.getsource(m.VOLUME.evaluate)).body[0]
  self.assertEqual(ast.dump(old,include_attributes=False),ast.dump(actual,include_attributes=False))
 def test_same_solid_and_exact_original_overloads_without_native(self):
  solid=object();calls=[]
  class Props:
   def Mass(self):return m.ADAPTIVE_REFERENCE
  class Mock:
   @staticmethod
   def VolumeProperties_s(actual,props,*args):
    calls.append((actual,args));return 0. if type(args[0])is float else None
  rows=m.volume_measurements(solid,Mock,Props)
  self.assertTrue(all(actual is solid for actual,_ in calls));self.assertEqual([args for _,args in calls],[(False,False,False),(True,False,False),(1e-10,True,False)])
  self.assertTrue(rows['adaptive_exact_binary64_equal_to_closed_reference']);self.assertEqual([r['mass_binary64_hex']for r in rows['methods']],[m.ADAPTIVE_REFERENCE.hex()]*3);self.assertIsNone(rows['Gmsh_getMass_mm3'])
 def test_wrong_adaptive_reference_refuses(self):
  d,o=fixture();d['native_volume_methods']['adaptive_exact_binary64_equal_to_closed_reference']=False
  with self.assertRaises(ValueError):m.check_new(d,o)
 def test_no_closed_Gmsh_volume_fabricated(self):
  d,o=fixture();d['native_volume_methods']['Gmsh_getMass_mm3']=1.
  with self.assertRaises(ValueError):m.check_new(d,o)
if __name__=='__main__':unittest.main(verbosity=2)
