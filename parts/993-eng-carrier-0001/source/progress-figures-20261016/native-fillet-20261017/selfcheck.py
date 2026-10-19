"""Small read-only picture checks, without CAD or plotting imports."""
import copy
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('_actual_fillet_picture',HERE/'figure.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def data():
    edges=[dict(points_xyz_mm=[[m.X,-13.8,12.3],[m.X,-13.0,13.0]])]
    return dict(section_X_mm=m.X,sections=[dict(role=role,edges=copy.deepcopy(edges),
        sampled_positions_sha256=m.coordinate_sha(edges),maximum_native_edge_tolerance_mm=1e-7)for role in ['before','after']])
class Tests(unittest.TestCase):
    def test_two_actual_ordered_sections(self):m.check(data())
    def test_plane_and_source_order(self):
        for edit in ['plane','order']:
            d=data()
            if edit=='plane':d['section_X_mm']+=1
            else:d['sections'].reverse()
            with self.assertRaises(ValueError):m.check(d)
    def test_sample_bits(self):
        d=data();d['sections'][0]['edges'][0]['points_xyz_mm'][0][1]+=.001
        with self.assertRaisesRegex(ValueError,'bits'):m.check(d)
    def test_actual_plane_residual(self):
        d=data();a=d['sections'][0];a['edges'][0]['points_xyz_mm'][0][0]+=.001;a['sampled_positions_sha256']=m.coordinate_sha(a['edges'])
        with self.assertRaisesRegex(ValueError,'plane tolerance'):m.check(d)
    def test_empty_and_nonfinite_rejected(self):
        for bad in [[],[[m.X,-13.8,float('nan')],[m.X,-13.,13.]]]:
            d=data();a=d['sections'][0];a['edges'][0]['points_xyz_mm']=bad;a['sampled_positions_sha256']=m.coordinate_sha(a['edges'])
            with self.assertRaises(ValueError):m.check(d)
    def test_freshness_and_dangling_symlink(self):
        with tempfile.TemporaryDirectory(dir=HERE)as t:
            root=Path(t);m.fresh(root/'new');p=root/'old';p.touch()
            with self.assertRaises(ValueError):m.fresh(p)
            p=root/'link';p.symlink_to(root/'absent')
            with self.assertRaises(ValueError):m.fresh(p)
    def test_no_native_or_plotting_at_module_load(self):
        for name in ['numpy','OCP','matplotlib']:self.assertNotIn(name,sys.modules)
if __name__=='__main__':unittest.main()
