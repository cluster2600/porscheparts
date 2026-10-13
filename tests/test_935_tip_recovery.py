import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'twins/935-horizontal-cooling-system-f0/source'))
try:
    import numpy as np
    from recover_tip_sections import correct
    from complete_candidate_rotor import local_profile, world_profile
except ImportError:
    correct = None


@unittest.skipIf(correct is None, 'Numerical mesh dependencies unavailable')
class TipRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.stations = [84,100,102,104,106,108,110,112,114]
        angle = np.linspace(0, 2*np.pi, 128, endpoint=False)
        self.cross = np.column_stack((np.zeros(128), 4*np.cos(angle), 2*np.sin(angle)))
        blades = []
        for i in range(9):
            phase = i*2*np.pi/9
            rows = []
            for station in self.stations:
                points = self.cross.copy(); points[:,0] = station
                rows.append(world_profile(points, phase).tolist())
            blades.append({'id':f'blade-{i:02d}', 'blade_id':f'blade-{i:02d}', 'phase_radians':phase,
                'stations_source_units':self.stations, 'profiles':rows,
                'provenance':[{'classification':'registered_acquired_reference_section' if 100 <= s <= 104 else 'constant_profile_root_or_tip_design'} for s in self.stations]})
        self.reference = {'blades':blades, 'regions':copy.deepcopy(blades)}
        self.acquired = {}
        for station, scale in [(110,.8),(112,.4),(113.75,.1)]:
            points = self.cross.copy(); points[:,1:] *= scale; points[:,0] = station
            self.acquired[station] = world_profile(points, blades[3]['phase_radians'])

    def test_preserves_other_blades_and_existing_acquired_data(self):
        before = copy.deepcopy(self.reference)
        result = correct(self.reference, 'blade-03', self.acquired)
        self.assertEqual(self.reference, before)
        for i, blade in enumerate(result['blades']):
            if i != 3:
                self.assertEqual(blade, before['blades'][i])
        blade = result['blades'][3]
        for station in [84,100,102,104]:
            self.assertEqual(blade['profiles'][blade['stations_source_units'].index(station)],
                             before['blades'][3]['profiles'][self.stations.index(station)])
        self.assertEqual(max(blade['stations_source_units']), 113.75)
        self.assertEqual(result['regions'], result['blades'])

    def test_interpolation_is_labelled_and_not_constant_extrapolation(self):
        blade = correct(self.reference, 'blade-03', self.acquired)['blades'][3]
        index = blade['stations_source_units'].index(106)
        profile = local_profile(blade['profiles'][index], blade['phase_radians'])
        self.assertAlmostEqual(np.ptp(profile[:,1]), 8*(1-.2*2/6))
        self.assertEqual(blade['provenance'][index]['classification'], 'own_acquired_anchor_interpolation_tip_repair')
        self.assertEqual(blade['provenance'][index]['anchor_stations_source_units'], [104,110])

    def test_invalid_acquired_plane_and_nonfinite_points_fail(self):
        for value in (105., float('nan')):
            points = copy.deepcopy(self.acquired)
            points[110][0] = value
            with self.assertRaises(ValueError):
                correct(self.reference, 'blade-03', points)

    def test_new_sections_cannot_replace_an_existing_acquired_station(self):
        points = dict(self.acquired); points[104] = points.pop(110)
        with self.assertRaisesRegex(ValueError, 'beyond'):
            correct(self.reference, 'blade-03', points)

    def test_repaired_arcs_are_used_and_never_labelled_measured(self):
        profile = self.cross.copy(); profile[:,0] = 106; profile[:,2] *= 1.5
        profile = world_profile(profile, self.reference['blades'][3]['phase_radians'])
        links = [{'a':[106,0,0], 'b':[106,0,1], 'length_source_units':1}]
        repaired = {106:{'profile':profile, 'links':links}}
        blade = correct(self.reference, 'blade-03', self.acquired, repaired)['blades'][3]
        i = blade['stations_source_units'].index(106)
        local = local_profile(blade['profiles'][i], blade['phase_radians'])
        self.assertAlmostEqual(np.ptp(local[:,2]), 6)
        self.assertEqual(blade['provenance'][i]['repairs'], links)
        self.assertEqual(blade['provenance'][i]['classification'], 'own_observed_arcs_with_local_gap_chords')
        self.assertIs(blade['provenance'][i]['gap_surfaces_are_measured'], False)

    def test_repair_cannot_replace_acquired_or_terminal_sections(self):
        for station in (100,110,113.75,114):
            with self.assertRaisesRegex(ValueError, 'between'):
                correct(self.reference, 'blade-03', self.acquired, {station:{'profile':self.acquired[110],'links':[]}})


class TipEvidenceTests(unittest.TestCase):
    def test_frozen_execution_sources_and_conditional_status(self):
        record = json.loads((ROOT/'docs/research/935-horizontal-cooling/tip-correction-20261013.json').read_text())
        for path, expected in record['source_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(), expected, path)
        for flag in ('scale_verified','historical_interfaces_verified','manufacturing_authorized','physical_validation','vast_rental_used','CFD_recomputed'):
            self.assertIs(record[flag], False)
        self.assertTrue(record['tip_recovery']['untargeted_blades_unchanged'])
        self.assertTrue(record['tip_recovery']['every_observed_cut_endpoint_retained'])
        self.assertIs(record['tip_recovery']['terminal_cap_is_measured'], False)
        self.assertIs(record['fea']['mesh_convergence_established'], False)
        self.assertEqual([r['pitch_mm'] for r in record['fea']['cases']], [1.5,1.35,1.2])
        self.assertEqual([r['voxel_assumed_mm'] for r in record['geometry']['cases']], [1.2,.6,.3])
        self.assertTrue(record['geometry']['volume_and_inertia_below_one_percent'])


if __name__ == '__main__':
    unittest.main()
