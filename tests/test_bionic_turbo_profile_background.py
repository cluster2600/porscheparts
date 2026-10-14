import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'twins/bionic-turbo-f1/cfd'))
from profile_background import simplify,validate_profile,mesh_text

class BackgroundTests(unittest.TestCase):
    def test_simplification_preserves_corners_and_rejects_bad_stations(self):
        np.testing.assert_array_equal(simplify([[0,3],[1,2],[2,1],[3,2]]),[[0,3],[2,1],[3,2]])
        for a in ([[0,1],[0,2]],[[0,1],[1,float('nan')]],[[0,-1],[1,2]]):
            with self.assertRaises(ValueError):simplify(a)

    def test_recheck_includes_an_interior_kink_not_only_band_endpoints(self):
        bands=[dict(z_low_mm=0,z_high_mm=1,rotor_upper_mm=1,stator_lower_mm=5) for _ in range(359)]
        report=dict(bands=bands)
        self.assertGreater(validate_profile([[0,3],[1,3]],[report,report],1),1)
        with self.assertRaises(ValueError):validate_profile([[0,3],[.5,4.5],[1,3]],[report,report],1)
        with self.assertRaises(ValueError):validate_profile([[.1,3],[1,3]],[report,report],1)

    def test_mesh_has_square_core_arcs_caps_and_direct_zone(self):
        text,info=mesh_text([[-4,32],[-3.75,32],[-3.5,32],[33,20]],100,[-15,47],.45)
        self.assertEqual(info['sectors'],128);self.assertEqual(text.count('hex ('),info['blocks'])
        self.assertIn('arc ',text);self.assertIn('rotorZone',text)
        self.assertGreater(info['expected_cells'],info['expected_rotating_cells']);self.assertGreater(info['expected_rotating_cells'],0)
        self.assertIn(-3.75,info['stations_z_mm']);self.assertIn(33,info['stations_z_mm'])
        with self.assertRaises(ValueError):mesh_text([[-4,32],[33,20]],25,[-15,47],.45)

class ConstrainedProfileTests(unittest.TestCase):
    def test_full_band_constraints_and_fixed_terminations(self):
        from profile_background_v2 import constrained_profile
        reports=[dict(bands=[dict(z_low_mm=(i-38)*.1,z_high_mm=(i-37)*.1,rotor_upper_mm=5.,stator_lower_mm=40.) for i in range(359)]) for _ in range(2)]
        spec=dict(retained_radial_clearance_mm=1.,nodes_z_radius_mm=[[-4,32],[33,20]])
        nodes,clearance=constrained_profile(reports,spec)
        np.testing.assert_array_equal(nodes[0],[-4,32]);np.testing.assert_array_equal(nodes[-1],[33,20])
        self.assertGreaterEqual(clearance,1)
        reports[1]['bands'][100]['stator_lower_mm']=6
        with self.assertRaises(ValueError):constrained_profile(reports,spec)

class PhysicalMeshPreparationTests(unittest.TestCase):
    def test_only_global_refinement_changes_not_surfaces_or_gaps(self):
        from prepare_profile_mesh import snappy_dictionary
        text='refinementSurfaces {domain {level (1 1);}} refinementRegions {box {levels ((1e15 1)); gapLevel (4 1 3);}}'
        changed=snappy_dictionary(text)
        self.assertEqual(changed.replace('levels ((1e15 0));','levels ((1e15 1));'),text)
        for bad in ('',text+text):
            with self.assertRaises(ValueError):snappy_dictionary(bad)

    def test_rejected_or_unmatched_background_cannot_prepare_physical_mesh(self):
        import json,tempfile
        from prepare_profile_mesh import prepare
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);parent=root/'parent';bg=root/'background';parent.mkdir();bg.mkdir()
            (parent/'case-manifest.json').write_text('{}');(bg/'manifest.json').write_text('{}')
            (bg/'report.json').write_text(json.dumps(dict(mesh_gate_passed=False)))
            audit=root/'audit.json';audit.write_text('{}')
            with self.assertRaises(ValueError):prepare(parent,bg,audit,root/'new')
            self.assertFalse((root/'new').exists())
