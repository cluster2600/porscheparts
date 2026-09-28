"""Trust-boundary tests; no mesh, solve or platform emulation."""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import candidate as c


class G14Trust(unittest.TestCase):
    def test_real_cad_chain_has_explicit_journal_bands_not_spine_width(self):
        for ident in c.IDS:
            _, variant, proof = c.inputs(c.CAD, ident)
            self.assertEqual(variant['journal_width_mm'], 8 if ident.startswith('outer') else 11)
            self.assertTrue(proof['outer_mirror']['accepted'])

    def test_changed_receipt_fails_before_spawn_or_output(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'receipt.json'
            path.write_text(c.CAD.read_text()+' ')
            args = SimpleNamespace(cad=path, id=c.IDS[0], output=Path(directory)/'never-created',
                                   reference=c.native.HERE/'run-1/summary-0001.json')
            with patch.object(c.subprocess, 'Popen') as spawn:
                with self.assertRaisesRegex(ValueError, 'receipt or interface'):
                    c.run(args)
                spawn.assert_not_called()
            self.assertFalse(args.output.exists())

    def test_cad_rejection_incomplete_motion_or_nan_oil_cannot_pass(self):
        receipt = json.loads(c.CAD.read_text())
        interfaces = json.loads((c.CAD.parent/'interface-proof.json').read_text())
        base, interface = receipt['variants'][1], interfaces['variants'][1]
        for mutate in (lambda r:r.update(cad_accepted=False), lambda r:r.update(motion_samples_checked=143),
                lambda r:r['oil_paths']['intake'].update(residual_solid_mm3=float('nan'))):
            row = copy.deepcopy(base); mutate(row)
            with self.assertRaises(ValueError):
                c.accepted(row, interface, interface['baseline_step_sha256'])
        with self.assertRaises(ValueError):
            c.inputs(c.CAD, 'centre_spine70_t30')


if __name__ == '__main__':
    unittest.main()
