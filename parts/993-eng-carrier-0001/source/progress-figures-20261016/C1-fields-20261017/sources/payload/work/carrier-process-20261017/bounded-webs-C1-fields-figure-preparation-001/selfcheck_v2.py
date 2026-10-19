"""Presentation-only002: inverse byte equality plus all original stdlib contracts."""
import ast
import importlib.util
import json
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('_C1_prior_tests',HERE/'selfcheck.py');base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
spec=importlib.util.spec_from_file_location('_C1_figure_v2',HERE/'figure_v2.py');candidate=importlib.util.module_from_spec(spec);spec.loader.exec_module(candidate)
# Run all original contract methods against the actual new module, with no scientific imports.
base.m=candidate
class OriginalContracts(base.Contracts):pass

class Presentation(unittest.TestCase):
    def test_inverse_byteexact(self):
        old=(HERE/'figure.py').read_text();new=(HERE/'figure_v2.py').read_text();changes=json.loads((HERE/'presentation-changes-002.json').read_text())['substitutions']
        for before,after in reversed(changes):
            self.assertEqual(new.count(after),1);new=new.replace(after,before)
        self.assertEqual(new.encode(),old.encode())
    def test_all_nonrender_functions_identical(self):
        trees=[ast.parse((HERE/n).read_text())for n in ['figure.py','figure_v2.py']]
        f=[{n.name:ast.dump(n,include_attributes=False)for n in t.body if isinstance(n,ast.FunctionDef)and n.name!='render'}for t in trees]
        self.assertEqual(*f)
    def test_zoom_band_clear_of_main_views(self):
        # Fixed camera/data span and equal-aspect panel dimensions from the actual001 receipt.
        # These are layout arithmetic, not a new geometry/field calculation.
        receipt=json.loads((HERE/'render-001/render-receipt.json').read_text());limits=receipt['checks'][0]
        ratio=(limits['ylim'][1]-limits['ylim'][0])/(limits['xlim'][1]-limits['xlim'][0])
        panel_width=(.88-.055)/(2+.14);panel_height=panel_width*17*ratio/12.4
        slot_height=(.78-.26)/(2+.17);upper_centre=.78-slot_height/2;lower_centre=.26+slot_height/2
        self.assertGreater(.475,lower_centre+panel_height/2+.025)
        self.assertLess(.475+.075,upper_centre-panel_height/2-.025)
        axes=json.loads((HERE/'presentation-changes-002.json').read_text())['proposed_zoom_axes']
        self.assertEqual(axes,[[.22+.43*c,.475,.14,.075]for c in range(2)])
    def test_footer_known_refusal(self):
        s=(HERE/'figure_v2.py').read_text();self.assertIn('échange STEP refusé',s);self.assertNotIn('échange STEP en contrôle',s)
    def test_original_exports_remain_bound(self):
        qa=json.loads((HERE/'root-QA-render001-transcription.json').read_text())
        self.assertTrue(qa['PNG_viewed_by_root']);self.assertFalse(qa['presentation002_render_authorized'])
        self.assertTrue(all(candidate.sha(HERE/'render-001'/n)==h for n,h in qa['exports_sha256'].items()))

if __name__=='__main__':unittest.main(verbosity=2)
