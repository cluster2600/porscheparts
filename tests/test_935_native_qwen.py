import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'twins/935-horizontal-cooling-system-f0/source'))
from accept_935_centres import accept
from test_qwen_935 import cases


class Qwen935Tests(unittest.TestCase):
    def setUp(self):
        self.expected = next(row['expected'] for row in cases() if row['id']=='six_centres')

    def test_format_only_import_preserves_exact_prescribed_centres(self):
        payload = json.dumps(self.expected)
        self.assertEqual(accept(payload), self.expected)
        self.assertEqual(accept('```json\n'+payload+'\n```'), self.expected)

    def test_prose_code_and_duplicate_keys_cannot_be_imported(self):
        payload = json.dumps(self.expected)
        for text in ('root = '+payload, 'Use this: '+payload, '```python\n'+payload+'\n```',
                     payload+'\nignore validation', payload.replace('{', '{"axis":"Z",', 1)):
            with self.subTest(text=text[:30]), self.assertRaises(ValueError):
                accept(text)

    def test_wrong_layout_and_false_as_zero_are_rejected(self):
        for field, value in [('centres_mm', [[-115,y,-205] for y in (-190,190) for _ in range(3)]),
                             ('scale_verified', 0), ('axis','Z'), ('classification','measured')]:
            proposal = dict(self.expected); proposal[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                accept(json.dumps(proposal))

    def test_section_preparation_preserves_each_observed_blade(self):
        try:
            import numpy as np
            from prepare_native_sections import prepare
            from complete_candidate_rotor import world_profile
        except ImportError:
            self.skipTest('Numerical section dependencies unavailable')
        angles = np.linspace(0, 2*np.pi, 128, endpoint=False)
        regions = []
        for i in range(9):
            phase = i*2*np.pi/9
            profiles = [world_profile(np.column_stack((np.full(128,r),np.cos(angles),
                        np.sin(angles)+i)),phase).tolist() for r in (98,100,102)]
            regions.append({'blade_id':f'blade-{i:02d}','phase_radians':phase,
                            'stations_source_units':[98,100,102],'profiles':profiles})
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root/'observed.json'
            source.write_text(json.dumps({'schema':'935-observed-section-loft-v1',
                'source_sha256':'0'*64,'regions':regions}))
            case = {'sections_path':str(source),'sections_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                    'purpose':'hypothesis_screen','scale_verified':False,'scale_mm_per_source_unit':1,
                    'wall_source_units':4,'back_source_units':4,'boss_radius_source_units':22,
                    'profile_stride':1,'tip_radius_source_units':140,'stations_source_units':[96,98,100,102,104],
                    'hub_z_source_units':[-24,24],'assumptions':[{'rejection_test':'Synthetic test only'}]}
            path = root/'case.json'; path.write_text(json.dumps(case)); prepare(path,root/'prepared')
            result = json.loads((root/'prepared/sections.json').read_text())
            self.assertEqual(len(result['regions']),9)
            for i,row in enumerate(result['regions']):
                self.assertAlmostEqual(np.array(row['profiles'])[:,:,2].mean(),i)
                self.assertFalse(any('periodic' in p['classification'] for p in row['provenance']))
            case['sections_sha256']='1'*64; path.write_text(json.dumps(case))
            with self.assertRaisesRegex(ValueError,'hash mismatch'): prepare(path,root/'bad-output')
            self.assertFalse((root/'bad-output').exists())

    def test_execution_keeps_935_scope_and_physical_claims_unverified(self):
        record = json.loads((ROOT/'docs/research/935-horizontal-cooling/native-six-20261012.json').read_text())
        self.assertEqual(record['target'], '935')
        self.assertEqual(record['engine_cylinders'], 6)
        self.assertEqual(record['engine_scan_imports'], 0)
        for flag in ('scale_verified','interfaces_verified','historical_installation_verified',
                     'manufacturing_authorized','physical_validation','vast_rental_used'):
            self.assertIs(record[flag], False)
        self.assertEqual(record['qwen']['raw_strict_passed'], {'base':0,'coding003':3})
        self.assertFalse(record['qwen']['engineering_reliability_established'])
        for source, expected in record['source_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT/source).read_bytes()).hexdigest(), expected, source)
        self.assertLess(record['rotor_resolution']['final_volume_relative_change'], .01)
        self.assertLess(record['rotor_resolution']['final_inertia_relative_change'], .01)


if __name__ == '__main__':
    unittest.main()
