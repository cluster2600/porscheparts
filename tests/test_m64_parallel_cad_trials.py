import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/wholebody/run_parallel_cad_trials.py'
spec = importlib.util.spec_from_file_location('m64_parallel_cad', path)
batch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(batch)


class ParallelCADTest(unittest.TestCase):
    def test_bounded_unique_recipes_and_no_false_acceptance(self):
        recipes = batch.recipes()
        self.assertEqual(len(recipes), 9)
        self.assertEqual(len({tuple(sorted(r.items())) for r in recipes}), 9)
        gates = {key:True for key in ('positive_jacobians', 'native_CAD_model_unchanged_after_meshing',
            'positive_signed_tetra_volumes', 'one_connected_tetra_region', 'complete_tetra_boundary',
            'all_CAD_faces_meshed', 'minSICN_project_limit', 'reread_positive_jacobians',
            'reread_minSICN_project_limit', 'coarse_volume_error_limit', 'mesh_export_roundtrip')}
        report = dict(status='coarse_mesh_checks_passed_NOT_CAE_VALIDATED', gates=gates, volume_algorithm=1,
                      native_input_unchanged=True, baseline_unchanged=True, source_unchanged=True)
        self.assertTrue(batch.mesh_accepted(report))
        for update in ({'status':'failed'}, {'gates':{}}, {'gates':{'quality':False}},
                       {'gates':{'quality':1}}, {'source_unchanged':False}, {'volume_algorithm':None},
                       {'volume_algorithm':10}, {'gates':{k:v for k,v in gates.items() if k!='all_CAD_faces_meshed'}},
                       {'gates':{**gates, 'positive_jacobians':1}}):
            self.assertFalse(batch.mesh_accepted({**report, **update}))
        self.assertTrue(batch.mesh_accepted({**report, 'volume_algorithm':10,
            'gates':{**gates, 'surface_triangulations_unchanged_during_3D':True}}))
