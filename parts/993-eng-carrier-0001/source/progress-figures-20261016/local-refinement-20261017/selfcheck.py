"""Selection/count/position invariants on tiny stdlib fixtures; no real geometry."""
import copy
import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('_mesh_figure_fixture',HERE/'render.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def fixture():
    points={1:[0.,0.,0.],2:[1.,0.,0.],3:[0.,1.,0.],4:[0.,0.,1.],
        5:[.2,.2,.2],6:[.3,.2,.2],7:[4.,4.,4.],8:[5.,5.,5.]}
    elements=[(11,[1,2,3,4]),(12,[5,6,7,8])]
    region=dict(id='fixture',bounds_mm=[[.1,.1,.1],[.4,.4,.4]],target_h_mm=.7)
    return points,elements,region

class Tests(unittest.TestCase):
    def test_all_six_whole_edges_plus_nonselected_inside_edge(self):
        p,t,r=fixture();before=copy.deepcopy(p);v=m.select(p,t,r)
        self.assertEqual(v['selected_cells'],[dict(element_id=11,corner_ids=[1,2,3,4])])
        self.assertEqual(v['centroid_selected_six_edge_incidences'],6);self.assertEqual(len(v['edges']),7)
        self.assertEqual(v['whole_inside_edges'],[[5,6]]);self.assertEqual(v['whole_inside_edge_incidences'],1)
        self.assertEqual(v['measured_h_mm'],math.sqrt(2));self.assertEqual(p,before);m.check_record(v)
        self.assertTrue(any(not m.inside(x,r['bounds_mm'])for row in v['points']for x in [row[1:]]))
    def test_shared_edges_deduplicated_by_ID_only_all_incidences_kept(self):
        p,t,r=fixture();t.append((13,[1,2,3,4]));v=m.select(p,t,r)
        self.assertEqual(v['centroid_selected_six_edge_incidences'],12);self.assertEqual(len(v['edges']),7);m.check_record(v)
    def test_edge_omission_duplicate_and_count_refused(self):
        v=m.select(*fixture())
        for change in ('missing','duplicate','incidences'):
            bad=copy.deepcopy(v)
            if change=='missing':bad['edges'].pop()
            elif change=='duplicate':bad['edges'].append(bad['edges'][0])
            else:bad['centroid_selected_six_edge_incidences']-=1
            with self.assertRaises(ValueError):m.check_record(bad)
    def test_one_ULP_coordinate_change_refused(self):
        v=m.select(*fixture());v['points'][1][1]=math.nextafter(v['points'][1][1],math.inf)
        with self.assertRaises(ValueError):m.check_record(v)
    def test_JSON_binary64_roundtrip_exact(self):
        v=m.select(*fixture());self.assertEqual(m.check_record(json.loads(json.dumps(v))),m.check_record(v))
    def test_pending002_refuses_before_any_scientific_import(self):
        with tempfile.TemporaryDirectory()as d:
            p=Path(d)/'pending.json';p.write_text(json.dumps(dict(source_root=d,launch_ready=False,files_sha256={'not-created':None})))
            with patch.object(m,'load',side_effect=AssertionError('no scientific import')):
                with self.assertRaises(ValueError):m.export(p,Path(d)/'output')
            self.assertFalse((Path(d)/'output').exists())
    def test_no_scientific_imports_on_module_load(self):
        import sys
        self.assertNotIn('numpy',sys.modules);self.assertNotIn('matplotlib',sys.modules)

if __name__=='__main__':unittest.main()
