"""A live, drifted or unrelated native case cannot enter the read-only companion audit."""
import importlib.util
from pathlib import Path
import sys
import unittest

SOURCE = Path(__file__).resolve().parents[1]/"twins/962-cylinder-head-f0/source"
sys.path.insert(0, str(SOURCE))
spec = importlib.util.spec_from_file_location("checkpoint12", SOURCE/"audit_envelope_checkpoint12.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class BoundStoppedTrial(unittest.TestCase):
    def receipt(self):
        return dict(contract_sha256=module.CONTRACT_SHA256, source_import_exact=True,
            bound_inputs_unchanged=True, native_returncode=3, container_state={"Running": False})

    def test_stopped_exact_bound_trial(self):
        module.require_stopped_bound_trial(self.receipt())

    def test_live_or_missing_container_state_rejected(self):
        for state in [{"Running": True}, {}, None]:
            row = self.receipt(); row["container_state"] = state
            with self.assertRaises(ValueError):
                module.require_stopped_bound_trial(row)

    def test_unbound_or_wrong_trial_rejected(self):
        for field, value in [("source_import_exact", False), ("bound_inputs_unchanged", False),
                             ("contract_sha256", "wrong"), ("native_returncode", None),
                             ("native_returncode", True)]:
            row = self.receipt(); row[field] = value
            with self.assertRaises(ValueError):
                module.require_stopped_bound_trial(row)


if __name__ == "__main__":
    unittest.main()
