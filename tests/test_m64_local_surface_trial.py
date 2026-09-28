import importlib.util
from pathlib import Path
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/wholebody/run_local_surface_trial.py'
SPEC=importlib.util.spec_from_file_location('surface_trial',SOURCE)
trial=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(trial)


class SurfaceTrialTests(unittest.TestCase):
    def test_selection_uses_bound_source_identity_not_gmsh_tag_order(self):
        quality={'surface_quality_by_source_face_private':[
            {'source_face_index':i,'minSICN_below_0p1':int(i<=155)} for i in range(1,4919)]}
        binding={'descriptor_bijection_verified':True,'matches_private':[
            {'source_face_index':i,'gmsh_face_tag':9000-i} for i in range(1,4919)]}
        selected=trial.assignments(quality,binding)
        self.assertEqual(len(selected),155)
        self.assertEqual(selected[0],{'source_face_index':1,'gmsh_face_tag':8999,'algorithm':1})
        binding['matches_private'][1]['gmsh_face_tag']=8999
        with self.assertRaises(ValueError):trial.assignments(quality,binding)
        binding['descriptor_bijection_verified']=False
        with self.assertRaises(ValueError):trial.assignments(quality,binding)


if __name__=='__main__':unittest.main()
