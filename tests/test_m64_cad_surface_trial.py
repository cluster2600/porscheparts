import importlib.util
from pathlib import Path
import sys
import unittest

HERE=Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/wholebody'
sys.path.insert(0,str(HERE))
SPEC=importlib.util.spec_from_file_location('cad_surface_trial',HERE/'run_cad_surface_trial.py')
trial=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(trial)
from unify_coplanar_mesh_partition import protected_partition
from audit_partition_integrals import integral_gate


class SurfaceSelectionTests(unittest.TestCase):
    def test_hash_bound_face_union_and_complete_index(self):
        def rows(selected):
            return {'surface_quality_by_source_face_private':[{'source_face_index':i,
                'minSICN_below_0p1':int(i in selected)} for i in range(1,4919)]}
        original=rows(set(range(1,156))); residual=rows(set(range(1,27))|set(range(156,160)))
        union,remaining=trial.source_selection(original,residual)
        self.assertEqual(union,set(range(1,160))); self.assertEqual(len(remaining),30)
        with self.assertRaises(ValueError): trial.source_selection(original,rows(set(range(1,31))))
        residual['surface_quality_by_source_face_private'][0]['source_face_index']=2
        with self.assertRaises(ValueError): trial.source_selection(original,residual)

    def test_native_partition_rejects_unrelated_face_or_edge_changes(self):
        self.assertTrue(protected_partition([1243,1481],[1,2,3,4,5],{1,2,3,4,5},4917,10205))
        self.assertFalse(protected_partition([1243,1481,11],[1,2,3,4,5],{1,2,3,4,5},4917,10205))
        self.assertFalse(protected_partition([1243,1481],[1,2,3,4,6],{1,2,3,4,5},4917,10205))
        self.assertFalse(protected_partition([1243,1481],[1,2,3,4,5],{1,2,3,4,5},4918,10205))

    def test_integral_gate_keeps_threshold_and_requires_both_methods(self):
        rows=[dict(method=m,epsilon=e,shape=s,volume=1.,estimated_relative_error=1e-13)
              for m in ('Gauss','GaussKronrod') for e in (1e-10,1e-12) for s in ('source','candidate')]
        self.assertTrue(integral_gate(rows))
        self.assertFalse(integral_gate(rows[:-1]))
        rows[-1]['volume']=1.+2e-10
        self.assertFalse(integral_gate(rows))
        rows[-1]['volume']=float('nan')
        self.assertFalse(integral_gate(rows))


if __name__=='__main__': unittest.main()
