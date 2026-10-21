import ast
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

try:
    import shapely
    import pyslm.support.support as native_support
except ImportError:
    shapely = native_support = None
SOURCE = Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/process-skins-20261016'
AVAILABLE = (shapely is not None and hasattr(shapely, 'constrained_delaunay_triangles')
    and hasattr(native_support, '_triangulate_exact_projected_domain'))


@unittest.skipUnless(AVAILABLE, 'Constrained-triangulation runtime required')
class IncrementalRegionEntryTests(unittest.TestCase):
    def test_private_repair_preserves_full_geometry_and_receipt(self):
        sys.path.insert(0, str(SOURCE))
        import continuous_combinatorial_interfaces as frozen
        import continuous_incremental_interfaces as incremental
        from shapely.geometry import box
        domain = box(0, 10, 5, 11)
        interfaces = dict(upper=[[[0, 11], [5, 11]]], lower=[[[0, 10], [5, 10]]])
        old_constructor = frozen._CONSTRUCTION
        a, ar = frozen.repair(domain, domain, interfaces, .2)
        b, br = incremental.repair(domain, domain, interfaces, .2)
        self.assertEqual(a.wkb, b.wkb)
        self.assertEqual(ar, br)
        self.assertIs(frozen._CONSTRUCTION, old_constructor)

    def test_generator_snapshots_include_entire_constructor_chain(self):
        required = {'continuous_incremental_interfaces.py', 'incremental_combinatorial_interfaces_ids.py',
            'incremental_combinatorial_interfaces.py', 'indexed_combinatorial_interfaces.py',
            'combinatorial_interfaces.py', 'continuous_combinatorial_interfaces.py'}
        for kind in ['prism', 'legacy']:
            tree = ast.parse((SOURCE/f'generate_{kind}_region_v5.py').read_text())
            names = next(n.value for n in ast.walk(tree) if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == 'names' for t in n.targets))
            copied = set(ast.literal_eval(names))
            self.assertTrue(required <= copied)
            self.assertIn(f'generate_{kind}_region_v5.py', copied)

    def test_flat_snapshot_from_another_cwd_and_dependency_tamper(self):
        tree = ast.parse((SOURCE/'generate_prism_region_v5.py').read_text())
        names = ast.literal_eval(next(n.value for n in ast.walk(tree) if isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == 'names' for t in n.targets)))
        audit = SOURCE.parent/'process-scanpath-audit-20261016'
        names_audit = ['exact_band_union.py', 'exact_contacts.py', 'exact_polygon_coverage.py',
            'exact_intended_holes.py', 'exact_convex_union.py', 'exact_convex_halfplanes.py',
            'exact_contacts_both.py', 'exact_zero_face_coverage.py']
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            for name in names:
                shutil.copy2(SOURCE/name, target/name)
            for name in names_audit:
                shutil.copy2(audit/name, target/name)
            shutil.copy2(SOURCE.parent/'design-20261016/classify_mesh_contacts.py', target/'classify_mesh_contacts.py')
            script = "import sys;sys.path.insert(0,sys.argv[1]);import continuous_incremental_interfaces as m;from shapely.geometry import box;d=box(0,10,5,11);r,p=m.repair(d,d,{'upper':[[[0,11],[5,11]]],'lower':[[[0,10],[5,10]]]},.2);assert p['intervals'][0]['exact_intended_band_union_confinement']['passed']"
            result = subprocess.run([sys.executable, '-B', '-c', script, tmp], cwd='/', capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            with (target/'incremental_combinatorial_interfaces_ids.py').open('a') as handle:
                handle.write('\n# changed\n')
            result = subprocess.run([sys.executable, '-B', '-c', script, tmp], cwd='/', capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('dependency changed', result.stderr)


if __name__ == '__main__':
    unittest.main()
