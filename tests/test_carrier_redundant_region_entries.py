import ast
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
try:
    import shapely
    import pyslm.support.support as support
except ImportError:
    shapely=support=None
SOURCE=Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/process-skins-20261016'
AVAILABLE=(shapely is not None and hasattr(shapely,'constrained_delaunay_triangles')
    and hasattr(support,'_triangulate_exact_projected_domain'))

@unittest.skipUnless(AVAILABLE,'Patched PySLM and constrained-triangulation runtime required')
class RedundantRegionEntryTests(unittest.TestCase):
    def test_both_entries_copy_replayable_flat_policy_and_reject_tampering(self):
        for kind in ['prism','legacy']:
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as tmp:
                target=Path(tmp);tree=ast.parse((SOURCE/f'generate_{kind}_region_v6.py').read_text())
                names=ast.literal_eval(next(n.value for n in ast.walk(tree) if isinstance(n,ast.Assign)
                    and any(isinstance(a,ast.Name) and a.id=='names' for a in n.targets)))
                self.assertTrue({'chart_progress.py','redundant_strip_interfaces.py','continuous_redundant_interfaces.py'}<=set(names))
                for name in names:shutil.copy2(SOURCE/name,target/name)
                audit=SOURCE.parent/'process-scanpath-audit-20261016'
                for name in ['exact_contacts.py','exact_contacts_both.py','exact_zero_face_coverage.py','exact_polygon_coverage.py',
                    'exact_intended_holes.py','exact_band_union.py','exact_convex_union.py','exact_convex_halfplanes.py']:
                    shutil.copy2(audit/name,target/name)
                shutil.copy2(SOURCE.parent/'design-20261016/classify_mesh_contacts.py',target/'classify_mesh_contacts.py')
                script="import sys;sys.path.insert(0,sys.argv[1]);import continuous_redundant_interfaces as p;from shapely.geometry import box;d=box(0,10,5,11);r,c=p.repair(d,d,{'upper':[[[0,10],[5,10]]],'lower':[[[0,11],[5,11]]]},.2);assert c['combinatorial_construction_source_sha256']==p.CONSTRUCTOR_SHA256;assert c['intervals'][0]['exact_intended_band_union_confinement']['passed']"
                result=subprocess.run([sys.executable,'-B','-c',script,tmp],cwd='/',capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)
                with (target/'redundant_strip_interfaces.py').open('a') as handle:handle.write('\n# changed\n')
                result=subprocess.run([sys.executable,'-B','-c',script,tmp],cwd='/',capture_output=True,text=True)
                self.assertNotEqual(result.returncode,0);self.assertIn('dependency changed',result.stderr)

if __name__=='__main__':unittest.main()
