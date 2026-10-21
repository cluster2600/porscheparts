"""Small standard-library source/closure guards; no scientific import/render."""
import ast,importlib.util,json,tempfile,unittest
from pathlib import Path
H=Path(__file__).resolve().parent;s=importlib.util.spec_from_file_location('_taper_image_source_only',H/'render.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Tests(unittest.TestCase):
 def test_pending_refuses_before_any_data_or_science(self):
  with self.assertRaisesRegex(ValueError,'NOT ARMED'):m.closed_data(dict(launch_ready=False))
 def test_missing_ROOT_profile_closure_refuses(self):
  with self.assertRaisesRegex(ValueError,'NOT ARMED'):m.closed_data(dict(launch_ready=True,root_GO_sha256='future',profile_ROOT_review_sha256=None))
 def test_no_native_import_or_call(self):
  t=ast.parse((H/'render.py').read_text());self.assertFalse(any(isinstance(n,ast.ImportFrom)and(n.module or'').startswith('OCP')for n in ast.walk(t)));self.assertNotIn('BRepTools.Read',ast.unparse(t));self.assertNotIn('BRepAlgoAPI',ast.unparse(t))
 def test_ray_only_original_panel_and_shared_axes(self):
  s=(H/'render.py').read_text();self.assertIn('axes[0].plot',s);self.assertNotIn('axes[1].plot',s);self.assertIn('xlim=old.ZOOM[0],ylim=old.ZOOM[1]',s);self.assertIn("sections=[data['cached_sections'][1],data['taper_section']]",s)
 def test_fixed_metadata_and_postimport_gate(self):
  s=(H/'render.py').read_text();self.assertIn("'svg.hashsalt':'carrier-preserved-taper-profile-20261017'",s);self.assertIn("'CreationDate':None,'ModDate':None",s);self.assertIn("paths<=set(p['runtime_sha256'])",s)
if __name__=='__main__':unittest.main(verbosity=2)
