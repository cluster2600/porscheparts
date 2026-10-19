"""Source/metadata fixtures only; no mesh parsing, arrays or plotting."""
import ast,copy,hashlib,importlib.util,json
from pathlib import Path
import unittest
H=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('_corner_STL_metadata',H/'render.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def read(p):return json.loads(Path(p).read_text())
class Checks(unittest.TestCase):
 def test_whole_source_inverse(self):
  rec=read(H/'source-changes.json');text=(H/'render.py').read_text()
  for row in reversed(rec['replacements']):
   self.assertEqual(text.count(row['after']),row['count']);text=text.replace(row['after'],row['before'])
  self.assertEqual(text.encode(),Path(rec['original_path']).read_bytes())
 def test_three_literal_helpers(self):
  rec=read(H/'source-changes.json');old=Path(rec['original_path']).read_text();new=(H/'render.py').read_text()
  for name in ['sha','read','reused']:
   fn=lambda t:ast.get_source_segment(t,next(n for n in ast.parse(t).body if isinstance(n,ast.FunctionDef)and n.name==name))
   self.assertEqual(fn(old),fn(new))
 def test_current_closed_metadata(self):m.verify(read(H/'pending-plan.json'),hash_inputs=False)
 def test_foreign_mesh_or_scope_refused(self):
  original=read(H/'pending-plan.json')
  for key,value in [('STL_sha256',['old','wrong']),('camera_degrees',[20.,0.]),('masses_kg',[1.,1.]),('section_X_mm',50.),('BREP_sha256',['old','old'])]:
   with self.subTest(key=key):
    p=copy.deepcopy(original);p[key]=value
    with self.assertRaises(AssertionError):m.verify(p,hash_inputs=False)
 def test_pending_controls_and_budgets(self):
  p,l,c=[read(H/n)for n in ['pending-plan.json','pending-launch-plan.json','pending-command.json']]
  for obj in [p,l,c]:self.assertFalse(obj['launch_ready']);self.assertIsNone(obj['root_GO']);self.assertIsNone(obj['root_GO_sha256'])
  self.assertEqual(c['argv'][4],str(H/'pending-launch-plan.json'));self.assertEqual(c['argv'][6],m.sha(H/'pending-launch-plan.json'))
  self.assertEqual(l['command'][-1],str(H/'render.py'));self.assertEqual(l['total_wall_budget_seconds'],180)
  self.assertEqual(p['bounds'],dict(outer=180,inner=150,CPU=[140,141],threads=1,workers=0))
 def test_complete_mesh_and_original_camera_body(self):
  text=(H/'render.py').read_text();self.assertIn('tri = vertices[faces]',text)
  self.assertIn("raster.raster(np.concatenate([vertices,meshes[1-i][0]]),faces,colors,30.,0.,bounds=box)",text)
  self.assertIn("sections.append(segments[:,:,1:])",text)
  self.assertIn("for suffix in ['png','svg']",text)
  self.assertNotIn('os.nice(',text);self.assertNotIn('import OCP',text)
if __name__=='__main__':unittest.main()
