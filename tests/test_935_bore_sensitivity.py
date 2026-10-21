import importlib.util
import hashlib
import json
import math
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('bore_sensitivity', ROOT/'twins/935-horizontal-cooling-system-f0/source/prepare_bore_sensitivity.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


class BoreSensitivityTests(unittest.TestCase):
    def setUp(self):
        nodes = []
        for radius in (10, 10.4):
            for i in range(12):
                a = i*math.pi/6
                nodes.append(f'{len(nodes)+1},{radius*math.cos(a):.12g},{radius*math.sin(a):.12g},0')
        self.prefix = '*NODE\n'+'\n'.join(nodes)+'\n*ELEMENT,TYPE=C3D8,ELSET=ROTOR\n1,1,2,3,4,5,6,7,8\n'
        self.suffix = '*NSET,NSET=NALL,GENERATE\n1,24,1\n*MATERIAL,NAME=SCREEN\n*ELASTIC\n70000,.33\n*BOUNDARY\nBORE,1,3,0\n*STEP\n*DLOAD\nROTOR,CENTRIF,394784,0,0,0,0,0,1\n*END STEP\n'
        self.deck = self.prefix+'*NSET,NSET=BORE\n1,2,3\n'+self.suffix

    def test_only_bore_set_changes_and_band_has_fixed_width(self):
        a, audit = module.replace_bore(self.deck, 10, .1, 24)
        b, wider = module.replace_bore(self.deck, 10, .5, 24)
        self.assertTrue(a.startswith(self.prefix)); self.assertTrue(a.endswith(self.suffix))
        self.assertTrue(b.startswith(self.prefix)); self.assertTrue(b.endswith(self.suffix))
        self.assertEqual(audit['clamped_bore_nodes'], 12)
        self.assertEqual(wider['clamped_bore_nodes'], 24)
        self.assertEqual(audit['unchanged_non_bore_text_sha256'], wider['unchanged_non_bore_text_sha256'])

    def test_invalid_band_or_missing_node_coverage_rejected(self):
        for tolerance in (True, 0, -1, float('nan'), float('inf'), 5):
            with self.assertRaises(ValueError): module.replace_bore(self.deck, 10, tolerance, 24)
        with self.assertRaises(ValueError): module.replace_bore(self.deck, 10, .1, 23)

    def test_changed_element_or_ambiguous_bore_definition_rejected(self):
        for deck in (self.deck.replace('C3D8,','C3D8R,'), self.deck.replace('*NSET,NSET=BORE\n',''), self.deck+'*NSET,NSET=BORE\n1\n'):
            with self.assertRaises(ValueError): module.replace_bore(deck, 10, .1, 24)

    def test_execution_sources_are_pinned_and_no_qualification_is_promoted(self):
        r = json.loads((ROOT/'docs/research/935-horizontal-cooling/readme-chain-20261021.json').read_text())
        for path, expected in r['source_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(), expected, path)
        self.assertEqual(r['new_native_solves'], 2)
        self.assertEqual(sum(row['reused_identical_deck'] for row in r['cases']), 1)
        for flag in ('FEA_mesh_convergence_established','historical_interfaces_verified','scale_verified','physical_validation',
                     'manufacturing_authorized','vast_rental_used','source_lineages_mixed','CFD_recomputed','bending_locking_demonstrated_on_rotor'):
            self.assertIs(r[flag], False)


if __name__ == '__main__': unittest.main()
