import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/wholebody/trial_adaptive_native_mesh.py'
spec = importlib.util.spec_from_file_location('adaptive_native', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class AdaptiveMeshTest(unittest.TestCase):
    def test_sizes_and_face_binding_fail_closed(self):
        self.assertEqual(module.point_size(.01), .0075)
        self.assertEqual(module.point_size(.001), .005)
        self.assertEqual(module.point_size(1.), .05)
        for value in (0., -1., float('nan'), float('inf')):
            with self.assertRaises(ValueError): module.point_size(value)
        diagnostic = {'surface_quality_by_source_face_private':[
            {'source_face_index':3, 'minSICN_below_0p1':1},
            {'source_face_index':4, 'minSICN_below_0p1':0}]}
        binding = {'descriptor_bijection_verified':True, 'matches_private':[
            {'source_face_index':3, 'gmsh_face_tag':90}]}
        self.assertEqual(module.selected_faces(diagnostic, binding), [90])
        for bad in ({**binding, 'descriptor_bijection_verified':False},
                    {**binding, 'matches_private':[]},
                    {**binding, 'matches_private':binding['matches_private']*2}):
            with self.assertRaises(ValueError): module.selected_faces(diagnostic, bad)
