"""CG retry trust tests only; no numerical execution or original artifact mutation."""
import copy
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import outer_cg_retry as retry


class RetryTrust(unittest.TestCase):
    def test_only_original_failed_execution_and_exact_identity(self):
        proof = {'runtime': 'pinned'}
        identity = dict(id=retry.outer.IDS[0], mesh_mm=2., step_sha256='step', proof=proof)
        summary = dict(identity, status='failed', returncode=1, result=None,
                       numerically_qualified=False, mesh_convergence_qualified=False)
        retry.failed_case_gate(summary, identity, proof)
        for field, value in [('status','completed'), ('mesh_mm',1.), ('numerically_qualified',True), ('proof',{})]:
            changed = copy.deepcopy(summary); changed[field] = value
            with self.assertRaises(ValueError):
                retry.failed_case_gate(changed, identity, proof)

    def test_missing_original_stops_before_output_or_process(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with patch.object(retry,'ORIGINAL',root/'missing'), patch.object(retry.subprocess,'Popen') as spawn:
                with self.assertRaises(FileNotFoundError):
                    retry.run(SimpleNamespace(output=root/'must-not-exist',check=False))
                spawn.assert_not_called()
            self.assertFalse((root/'must-not-exist').exists())


if __name__ == '__main__':
    unittest.main()
