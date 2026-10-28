"""Small stdlib-only provenance/display-boundary tests; no STL body read or graphics import."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

H = Path(__file__).resolve().parent
R = H.parents[1]
spec = importlib.util.spec_from_file_location('_candidate_image', H / 'figure.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
context = json.loads((H / 'closed-context.json').read_text())
rows = [m.read(R / c[k]) for c in context.values() for k in ['root_review', 'owner_terminal']]
data = m.select_data(*rows)

class Checks(unittest.TestCase):
    def test_whole_selected_source_data(self):
        self.assertEqual(data, m.read(H / 'geometry-data.json'))
        self.assertEqual(len(data['whole_retained_native_laws']), 7)
        self.assertEqual(len(data['whole_retained_exact_function_proof']['edges']), 7)
    def test_closed_mass_and_generation_are_separate(self):
        self.assertEqual(data['native_mass_kg'], 1.2623644100871174)
        self.assertEqual(data['STL_triangles'], 637850)
        self.assertFalse(data['engineering_qualification_transferred'])
        self.assertTrue(data['snapshot_gate_flags_not_current_status'])
    def test_crop_contains_both_whole_source_endpoints(self):
        points = data['whole_source_physical_edges'][0]['endpoints']; box = data['source_edge431_display_box_mm']
        self.assertEqual(box, [[64.0, -15.18196820123, 3.0], [83.202665223312, -5.4, 13.756757217282]])
        for a in range(3):
            self.assertEqual(box[0][a], min(v['source_point_mm'][a] for v in points) - 1.0)
            self.assertEqual(box[1][a], max(v['source_point_mm'][a] for v in points) + 1.0)
    def test_foreign_native_owner_refused(self):
        x = copy.deepcopy(rows); x[0]['owner_terminal_sha256'] = '0' * 64
        with self.assertRaises(ValueError): m.select_data(*x)
    def test_unclosed_generation_refused(self):
        x = copy.deepcopy(rows); x[3]['actual_child_returncode'] = 1
        with self.assertRaises(ValueError): m.select_data(*x)
    def test_foreign_STL_refused(self):
        x = copy.deepcopy(rows); x[3]['STL_sha256'] = '0' * 64
        with self.assertRaises(ValueError): m.select_data(*x)
    def test_foreign_master_refused(self):
        x = copy.deepcopy(rows); x[3]['master_BREP_sha256'] = '0' * 64
        with self.assertRaises(ValueError): m.select_data(*x)
    def test_partial_triangle_roster_refused(self):
        x = copy.deepcopy(rows); x[2]['new_STL_triangles'] -= 1
        with self.assertRaises(ValueError): m.select_data(*x)
    def test_mass_change_refused(self):
        x = copy.deepcopy(rows); x[5]['mass_kg'] += .001
        with self.assertRaises(ValueError): m.select_data(*x)
    def test_changed_source_datum_identity_refused(self):
        x = copy.deepcopy(data['whole_source_physical_edges']); x[0]['endpoints'][0]['vertex_index_zero_based'] = 301
        with self.assertRaises(ValueError): m.display_box(x, 1.0)
    def test_nonfinite_and_arbitrary_crop_refused(self):
        x = copy.deepcopy(data['whole_source_physical_edges']); x[0]['endpoints'][0]['source_point_mm'][0] = float('nan')
        with self.assertRaises(ValueError): m.display_box(x, 1.0)
        with self.assertRaises(ValueError): m.display_box(data['whole_source_physical_edges'], 2.0)
    def test_literal_loader_and_whole_raster(self):
        m.literal_sources(R, dict(loader_original='parts/993-eng-carrier-0001/source/progress-figures-20261016/surface-remesh-20261017/figure.py', raster_original='parts/993-eng-carrier-0001/source/progress-figures-20261016/surface-remesh-20261017/raster_unlit.py', raster_copy=str((H / 'raster_unlit.py').relative_to(R))))
    def test_exact_loader_early_refusals_without_numpy(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / 'tiny.stl'
            for raw in [b'', b'0'*80 + struct.pack('<I', 0), b'0'*80 + struct.pack('<I', 1), b'0'*80 + struct.pack('<I', 1) + b'0'*51]:
                p.write_bytes(raw)
                with self.assertRaises(ValueError): m.read_binary(p)
        self.assertNotIn('numpy', sys.modules)
    def test_fresh_output_existing_and_symlink_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / 'existing'; p.mkdir()
            with self.assertRaises(ValueError): m.fresh(p)
            q = Path(folder) / 'link'; q.symlink_to(p)
            with self.assertRaises(ValueError): m.fresh(q / 'new')
    def test_no_old_quality_or_native_calls(self):
        tree = ast.parse((H / 'figure.py').read_text())
        names = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
        self.assertNotIn('quality', names)
        imports = {a.name.split('.')[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        self.assertFalse(imports & {'OCP', 'build123d', 'gmsh', 'trimesh'})
        self.assertFalse({'numpy', 'matplotlib', 'vispy'} & set(sys.modules))

if __name__ == '__main__':
    unittest.main()
