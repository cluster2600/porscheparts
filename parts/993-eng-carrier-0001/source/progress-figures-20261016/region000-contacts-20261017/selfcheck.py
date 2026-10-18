"""Small archive/AST checks; no scientific geometry or renderer import."""
import ast
import hashlib
import json
from pathlib import Path
import struct
import unittest
import zipfile

HERE = Path(__file__).resolve().parent
DATA = json.loads((HERE / 'data/figure-data.json').read_text())
TREE = ast.parse((HERE / 'render.py').read_text())


def function(tree, name):
    return ast.dump(next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name), include_attributes=False)


class RetainedIntervalFigureChecks(unittest.TestCase):
    def test_scale_bar_exact_reference(self):
        original = ast.parse((HERE / 'reference/first-layer-render.py.txt').read_text())
        self.assertEqual(function(TREE, 'scale_bar'), function(original, 'scale_bar'))
    def test_real_data_scope(self):
        self.assertEqual([DATA[k] for k in ('source_index', 'layer', 'z_mm', 'groups')], [0, 0, .03, 337])
        self.assertFalse(DATA['global_admission']); self.assertFalse(DATA['six_admissions_available'])
        self.assertEqual(DATA['method'], 'own_source_parametric_encoded_contact_1')
    def test_interval_arrays_complete(self):
        expected = {'Q_intervals_mm.npy': (129026, 2, 2), 'E_positive_intervals_mm.npy': (129023, 2, 2)}
        with zipfile.ZipFile(HERE / 'data/contact-intervals.npz') as archive:
            self.assertEqual(len(archive.namelist()), 7)
            for name, shape in expected.items():
                with archive.open(name) as stream:
                    self.assertEqual(stream.read(8), b'\x93NUMPY\x01\x00')
                    header = ast.literal_eval(stream.read(struct.unpack('<H', stream.read(2))[0]).decode())
                    self.assertEqual(header['descr'], '<f8'); self.assertEqual(header['shape'], shape)
    def test_npz_exact_stream_extraction(self):
        self.assertEqual(hashlib.sha256((HERE / 'data/contact-intervals.npz').read_bytes()).hexdigest(),
                         'feb09a6e971a2d8513726e552bfee1cbb2580cbaf7cea528a76fd452862a18b4')
    def test_three_exact_omissions(self):
        self.assertEqual([o['q_witness_index'] for o in DATA['omissions']], [31219, 43904, 51179])
        self.assertEqual([o['provenance'][1] for o in DATA['omissions']], [115663, 126546, 53968])
        self.assertEqual(DATA['Q_anchored_segments'] - DATA['E_parametric_anchored_vectors'], 3)
    def test_all_paths_retained(self):
        calls = [n for n in ast.walk(TREE) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'LineCollection']
        self.assertEqual([n.args[0].id for n in calls], ['q', 'e'])
        self.assertTrue(all(any(k.arg == 'rasterized' and isinstance(k.value, ast.Constant) and k.value.value is True for k in n.keywords) for n in calls))
    def test_no_geometry_import(self):
        imports = [n.module for n in ast.walk(TREE) if isinstance(n, ast.ImportFrom)]
        self.assertFalse(any(n and any(s in n for s in ('pyslm', 'shapely', 'audit_support', 'exact_contact')) for n in imports))
    def test_fixed_export_metadata(self):
        source = (HERE / 'render.py').read_text()
        self.assertIn("'svg.hashsalt': 'carrier-original000-anchored-intervals-figure19-20261017'", source)
        self.assertIn('metadata.update(Date=None)', source)
        self.assertIn('metadata.update(CreationDate=None, ModDate=None)', source)


if __name__ == '__main__': unittest.main()
