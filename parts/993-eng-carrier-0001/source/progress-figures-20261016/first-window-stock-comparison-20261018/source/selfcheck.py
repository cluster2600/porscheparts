"""Small source/closed-metadata Figure32 fixtures only; no arrays, STL or renderer."""
import ast
import copy
import difflib
import importlib.util
import json
from pathlib import Path
import unittest

H=Path(__file__).resolve().parent;R=H.parents[1]
spec=importlib.util.spec_from_file_location('_comparison_fixture_stdlib',H/'figure.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def records():
    context=json.loads((H/'closed-context.json').read_text())
    return {k:[json.loads((R/v['ROOT']).read_text()),json.loads((R/v['owner']).read_text())]for k,v in context.items()}


class Fixtures(unittest.TestCase):
    def test_six_loader_IO_helpers_literal(self):
        old=(R/'work/carrier-functional-law-candidate-image-preparation-004/figure.py').read_text();new=(H/'figure.py').read_text()
        def fn(text,n):return ast.get_source_segment(text,next(x for x in ast.parse(text).body if isinstance(x,ast.FunctionDef)and x.name==n))
        for n in ['require','sha','read','write','fresh','read_binary']:self.assertEqual(fn(old,n),fn(new,n))

    def test_whole_raster_unchanged(self):
        self.assertEqual((H/'raster_unlit.py').read_bytes(),(R/'work/carrier-functional-law-candidate-image-preparation-004/raster_unlit.py').read_bytes())

    def test_whole_file_inverse(self):
        delta=(H/'figure-from-Figure30.ndiff').read_text().splitlines(True)
        self.assertEqual(''.join(difflib.restore(delta,1)),(R/'work/carrier-functional-law-candidate-image-preparation-004/figure.py').read_text())
        self.assertEqual(''.join(difflib.restore(delta,2)),(H/'figure.py').read_text())

    def test_actual_closed_data_entire(self):
        self.assertEqual(m.select_data(records()),json.loads((H/'geometry-data.json').read_text()))

    def test_mass_is_two_distinct_native_results(self):
        d=m.select_data(records());self.assertEqual([c['native_mass_kg']for c in d['cases']],[1.2623644100871174,1.2678353778376648])
        self.assertEqual(d['native_mass_difference_g'],(1.2678353778376648-1.2623644100871174)*1000)
        self.assertTrue(d['inset_is_cut_profile_parameter_not_wall_thickness']);self.assertFalse(d['old_FEA_transferred'])

    def test_both_actual_mirrored_boxes(self):
        d=m.select_data(records());left,right=[x['XY_mm']for x in d['display_boxes']]
        self.assertEqual(left[0][0],-right[1][0]);self.assertEqual(left[1][0],-right[0][0])
        self.assertEqual([p[1]for p in left],[p[1]for p in right])

    def test_other_branch_change_refuses(self):
        ledgers=copy.deepcopy(records()['stock_native'][0]['all12_actual_source_window_branch_rows'])
        ledgers['outer-window-stock']['rows'][0]['inset_mm']=2.8
        with self.assertRaises(ValueError):m.display_boxes(ledgers)

    def test_missing_first_window_refuses(self):
        ledgers=copy.deepcopy(records()['stock_native'][0]['all12_actual_source_window_branch_rows'])
        ledgers['base-without-ribs']['rows']=ledgers['base-without-ribs']['rows'][1:]
        with self.assertRaises(ValueError):m.display_boxes(ledgers)

    def test_foreign_old_STL_refuses(self):
        r=records();r['old_generation'][1]['STL_sha256']='0'*64
        with self.assertRaises(ValueError):m.select_data(r)

    def test_foreign_stock_master_refuses(self):
        r=records();r['stock_generation'][0]['CAD_source']['sha256']='0'*64
        with self.assertRaises(ValueError):m.select_data(r)

    def test_unclosed_generation_refuses(self):
        r=records();r['stock_generation'][1]['owned_group_empty']=False
        with self.assertRaises(ValueError):m.select_data(r)

    def test_old_law_or_qualification_transfer_refuses(self):
        for k in ['old_complete7_law_inherited','candidate_qualified']:
            r=records();r['stock_native'][0][k]=True
            with self.assertRaises(ValueError):m.select_data(r)

    def test_marker_before_authoring_and_PNG_first(self):
        text=(H/'figure.py').read_text();body=text[text.index('def render('):]
        self.assertLess(body.index("write(output/'render-started.json'"),body.index('    import numpy'))
        self.assertIn("for suffix in ['png','svg','pdf']",body)
        self.assertIn("if suffix=='png':write(output/'PNG-ready.json'",body)

    def test_common_framing_without_rendered_other_faces(self):
        text=(H/'figure.py').read_text()
        self.assertIn('framed=np.concatenate([vertices,meshes[1-i][0]])',text)
        self.assertIn('raster.raster(framed,faces,color,30.,0.,bounds=common_box)',text)
        self.assertIn("pictures[0].shape==pictures[1].shape",text)


if __name__=='__main__':unittest.main()
