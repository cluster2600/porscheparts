import importlib.util
from pathlib import Path
import copy
import math
import unittest

P=Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/flowbench-intake/split_gas_c0_edge.py'
spec=importlib.util.spec_from_file_location('C0segmentation',P)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class NativeSegmentationTests(unittest.TestCase):
    def test_parameter_partition_not_missing_overlapping_or_nonfinite(self):
        bounds=[0.,.1,.2,.3,1.];spans=list(zip(bounds,bounds[1:]))
        self.assertTrue(module.complete_partition(bounds,spans))
        for bad in (spans[:-1],[(0.,.11),*spans[1:]],[(0.,float('nan')),*spans[1:]],
                    [spans[1],spans[0],*spans[2:]]):
            self.assertFalse(module.complete_partition(bounds,bad))
        self.assertFalse(module.parameter_equal(1.,1.+1e-8))
        self.assertTrue(module.parameter_equal(.25,math.nextafter(.25,math.inf)))

    def test_native_gates_do_not_accept_earlier_invalid_split(self):
        good={'input_unchanged':True,'parameter_partition_preserved':True,
            'local_edge_tolerances_not_increased':True,'valid_after_native_reread':True,
            'topology':{'solids':1,'faces':88,'edges':195,'vertices':120},
            'BOP':{'has_faulty':False,'has_errors':False,'has_warnings':False,'faults':[]}}
        self.assertTrue(module.native_checks_pass(good))
        for key in ('input_unchanged','parameter_partition_preserved',
                    'local_edge_tolerances_not_increased','valid_after_native_reread'):
            self.assertFalse(module.native_checks_pass({**good,key:False}))
        bad=copy.deepcopy(good);bad['topology']['edges']=194
        self.assertFalse(module.native_checks_pass(bad))
        bad=copy.deepcopy(good);bad['BOP']['faults']=['BOPAlgo_GeomAbs_C0']
        self.assertFalse(module.native_checks_pass(bad))
        self.assertFalse(module.native_checks_pass({}))


if __name__=='__main__':unittest.main()
