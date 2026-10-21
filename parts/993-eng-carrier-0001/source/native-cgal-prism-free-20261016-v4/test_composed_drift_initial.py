import json,tempfile,unittest
from pathlib import Path
from audit_composed_drift_initial import validate_execution

class LegacyExecutionBinding(unittest.TestCase):
    def test_refusal_is_not_accepted_implicitly(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'execution.json';d=dict(status='rejected_or_failed',returncode=2,identities_unchanged=True,owned_scope_inactive=True,inputs_sha256={},copied_sources_sha256={});p.write_text(json.dumps(d))
            with self.assertRaises(AssertionError):validate_execution(p)
            validate_execution(p,allow_geometry_complete_legacy_refusal=True)
    def test_other_return_codes_and_changed_inputs_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'execution.json'
            for code,unchanged in [(124,True),(1,True),(2,False)]:
                p.write_text(json.dumps(dict(status='rejected_or_failed',returncode=code,identities_unchanged=unchanged,owned_scope_inactive=True,inputs_sha256={},copied_sources_sha256={})))
                with self.assertRaises(AssertionError):validate_execution(p,allow_geometry_complete_legacy_refusal=True)

if __name__=='__main__':unittest.main()
