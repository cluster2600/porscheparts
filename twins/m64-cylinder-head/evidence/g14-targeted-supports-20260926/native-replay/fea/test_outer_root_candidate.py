"""Private outer-root entry guards; no real mesh or solver execution."""
import inspect
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import outer_root_candidate as c


class OuterRootTrust(unittest.TestCase):
    def test_actual_chain_interfaces_and_coexistence(self):
        _, row, proof = c.inputs(c.IDENT)
        self.assertEqual(row['journal_width_mm'],8)
        self.assertTrue(proof['outer_mirror']['accepted'])
        self.assertFalse(proof['outer_mirror']['negative_FE_executed'])
        self.assertGreater(proof['functional_tool_checks']['mount_tool_access_-1']['baseline_overlap_mm3'],500)
        self.assertEqual(row['journal_diameter_mm'],12.58)
        self.assertTrue(proof['combined_geometry']['pairwise_no_intersection'])
        self.assertFalse(proof['mounting_and_maintenance_qualified'])

    def test_modified_receipt_or_rejected_candidate_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory)/'receipt.json'
            changed.write_text(c.CAD.read_text()+' ')
            with self.assertRaises(ValueError): c.inputs(c.IDENT,changed)
        row = json.loads(c.CAD.read_text())['variants'][0]
        row['cad_accepted'] = False
        with self.assertRaises(ValueError): c.core.accepted(row,{},row['baseline_step_sha256'])

    def test_changed_coexistence_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory)/'combined.json'
            changed.write_text(c.COMBINED.read_text()+' ')
            with self.assertRaises(ValueError): c.combined_gate(json.loads(c.CAD.read_text()),changed)

    def test_missing_native_reference_prevents_any_output_or_worker(self):
        with tempfile.TemporaryDirectory() as directory:
            args = SimpleNamespace(reference=Path(directory)/'missing.json',output=Path(directory)/'never-created')
            with patch.object(c.subprocess,'Popen') as spawn:
                with self.assertRaises(FileNotFoundError): c.run(args)
                spawn.assert_not_called()
            self.assertFalse(args.output.exists())

    def test_negative_mirror_is_not_a_solver_candidate(self):
        with self.assertRaises(ValueError): c.inputs(c.ALL_IDS[1])

    def test_worker_and_numeric_audit_are_unchanged(self):
        self.assertEqual(inspect.getsource(c.worker),inspect.getsource(c.prior.worker))
        self.assertIs(c.audit,c.prior.audit)
        self.assertEqual(c.THREAD_ENV,c.prior.THREAD_ENV)
        self.assertEqual(c.IDS,(c.IDENT,))


if __name__ == '__main__':
    unittest.main()
