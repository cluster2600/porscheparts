"""Outer trust-boundary checks; no FE execution."""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import outer_candidate as c


class OuterTrust(unittest.TestCase):
    def test_real_cad_keeps_journals_and_discloses_historical_tool_obstruction(self):
        _, variant, proof = c.inputs(c.CAD, c.IDS[0])
        self.assertEqual(variant['journal_width_mm'], 8.)
        self.assertTrue(proof['outer_mirror']['accepted'])
        self.assertFalse(proof['mounting_and_maintenance_qualified'])
        self.assertGreater(proof['historical_tool_obstructions']['mount_tool_access_1']['baseline_overlap_mm3'], 0)

    def test_changed_input_stops_before_output_or_process(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'receipt.json'; path.write_text(c.CAD.read_text()+' ')
            args = SimpleNamespace(cad=path, id=c.IDS[0], output=Path(directory)/'never-created',
                                   reference=c.native.HERE/'run-1/summary-0001.json')
            with patch.object(c.subprocess, 'Popen') as spawn:
                with self.assertRaises(ValueError):
                    c.run(args)
                spawn.assert_not_called()
            self.assertFalse(args.output.exists())

    def test_rejected_or_changed_interface_cannot_pass_shared_gate(self):
        base = json.loads(c.CAD.read_text())['variants'][0]
        face = dict(id=base['id'], cad_accepted=True, step_sha256=base['step_sha256'],
            baseline_step_sha256=base['baseline_step_sha256'], journal_width_mm=8., journal_diameter_mm=12.58,
            first_1mm_unchanged=True, first_1mm_difference_mm3=base['first_1mm_difference_mm3'])
        for mutate in (lambda r:r.update(cad_accepted=False), lambda r:r.update(motion_samples_checked=143),
                       lambda r:r['journal_neighbourhood_difference'].pop('intake')):
            row = copy.deepcopy(base); mutate(row)
            with self.assertRaises(ValueError):
                c.prior.accepted(row, face, base['baseline_step_sha256'])


if __name__ == '__main__':
    unittest.main()
