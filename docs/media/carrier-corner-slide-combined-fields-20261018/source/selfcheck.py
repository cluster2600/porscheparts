"""Small current metadata/source checks, no arrays or plotting imports."""
import ast,copy,difflib,importlib.util,json,sys,tempfile,unittest
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1];O=H.with_name('carrier-corner-slide-combined-FEA-figure-preparation-001')
spec=importlib.util.spec_from_file_location('_current24af_field_metadata',H/'figure.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def read(p):return json.loads(p.read_text())
class Checks(unittest.TestCase):
 def data(self):
  d=read(O/'data-closed-cases.json');row=d['cases'][0];return row['paths'],row['docs'],d['source_files_sha256'],d['root_review']['results']['combined-rigid']
 def test_01_full_source_inverse(self):
  d=read(H/'source-changes.json');s=(H/'figure.py').read_text();back=s
  for row in reversed(d['substitutions']):self.assertEqual(back.count(row['after']),row.get('count',1));back=back.replace(row['after'],row['before'])
  self.assertEqual(back,(R/d['original']).read_text());self.assertEqual(''.join(difflib.restore(d['whole_ndiff'],2)),s)
 def test_02_five_math_helpers_literal_exact(self):
  d=read(H/'source-changes.json');old=(R/d['original']).read_text();new=(H/'figure.py').read_text()
  fn=lambda s:{n.name:ast.get_source_segment(s,n)for n in ast.parse(s).body if isinstance(n,ast.FunctionDef)}
  for name in d['five_math_functions_unchanged']:self.assertEqual(fn(old)[name],fn(new)[name])
  m.literal_functions(R,read(H/'pending-plan.json')['literal_functions'])
 def test_03_full_IP_loading_math_literal_exact(self):
  d=read(H/'source-changes.json');old=(R/d['original']).read_text();new=(H/'figure.py').read_text()
  a="    for row in rows:\n        with np.load(";b="    vm_scale=max("
  self.assertEqual(old[old.index(a):old.index(b)],new[new.index(a):new.index(b)])
 def test_04_actual_whole_case(self):m.validate_case(*self.data())
 def test_05_wrong_current_root_peak_refused(self):
  row,docs,hashes,root=self.data();root=copy.deepcopy(root);root['VM_MPa']=0
  with self.assertRaises(ValueError):m.validate_case(row,docs,hashes,root)
 def test_06_wrong_field_byte_refused(self):
  row,docs,hashes,root=self.data();hashes[row['field']]='0'*64
  with self.assertRaises(ValueError):m.validate_case(row,docs,hashes,root)
 def test_07_old_candidate_or_changed_rosters_refused(self):
  for key,value in [('candidate_version','first-window-stock-alone-v1')]:
   row,docs,hashes,root=self.data();docs=copy.deepcopy(docs);docs['assessment'][key]=value
   with self.assertRaises(ValueError):m.validate_case(row,docs,hashes,root)
  row,docs,hashes,root=self.data();docs=copy.deepcopy(docs);docs['loads']['actual_eye_node_counts']=[2278,2274]
  with self.assertRaises(ValueError):m.validate_case(row,docs,hashes,root)
 def test_08_all_ties_and_boundary_global_distinction(self):
  ties=[dict(VM_MPa=200),dict(VM_MPa=200)];r=m.maxima_record(200,80,3,ties);self.assertEqual(r['all_global_IP_ties'],ties);self.assertEqual(r['displayed_boundary_element_VM_max_MPa'],80)
 def test_09_unarmed_refuses_before_arrays(self):
  p=H/'pending-plan.json'
  with self.assertRaisesRegex(ValueError,'NON-ARMED'):m.verify(p,m.sha(p),True)
 def test_10_current_crops_counts_and_same_size(self):
  p=read(H/'pending-plan.json');d=read(O/'data-closed-cases.json')
  for i,role in enumerate(['rigid','spring']):
   box=p['display_zoom_XY_mm'][role];peak=d['cases'][i]['docs']['peaks']['all_global_maximum_ties'][0]['reference_undeformed_IP_xyz_mm'];self.assertEqual([box[1][j]-box[0][j]for j in [0,1]],[50,52]);self.assertTrue(all(box[0][j]<peak[j]<box[1][j]for j in [0,1]))
   self.assertEqual(d['cases'][i]['docs']['peaks']['nodes'],160005);self.assertEqual(d['cases'][i]['docs']['peaks']['C3D10_elements'],85958)
 def test_11_original_resources_and_English_scope(self):
  p=read(H/'pending-plan.json');l=read(H/'pending-launch.json');self.assertEqual(len(p['runtime_sha256']),219);self.assertEqual((p['outer_seconds'],p['inner_seconds'],p['CPU_soft_hard_seconds']),(180,150,[140,141]));self.assertEqual(l['command'][1],'-B');self.assertNotIn('-I',l['command'])
  text=(H/'figure.py').read_text();self.assertIn('Stress convergence has not been established',text);self.assertIn('85 958 C3D10',text);self.assertIn('deformation_amplification=1',text);self.assertIn('decimation=False',text)
 def test_12_no_arrays_plotting_CAD_imported(self):self.assertFalse(set(sys.modules)&{'numpy','matplotlib','PIL','OCP','gmsh'})
if __name__=='__main__':unittest.main()
