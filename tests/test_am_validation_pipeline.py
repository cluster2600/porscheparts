import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/validate_am_pipeline.py"
POLICY = ROOT / "catalog/manufacturing/am-validation-policy.json"


def load_module():
    spec = importlib.util.spec_from_file_location("validate_am_pipeline", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AmValidationPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()
        cls.policy = json.loads(POLICY.read_text(encoding="utf-8"))

    def test_every_lpbf_or_dmls_candidate_is_tracked(self) -> None:
        self.assertEqual(self.module.validate(self.policy), [])
        self.assertEqual(set(self.policy["tracked_part_ids"]), set(self.module.am_parts()))

    def test_new_untracked_candidate_fails_closed(self) -> None:
        policy = copy.deepcopy(self.policy)
        policy["tracked_part_ids"].pop()
        self.assertTrue(any("untracked_am_parts" in item for item in self.module.validate(policy)))

    def test_release_cannot_skip_required_stages(self) -> None:
        policy = copy.deepcopy(self.policy)
        piston = policy["part_overrides"]["993-ENG-PISTON-CP1-GALLERY-F0-0001"]
        piston["stages"]["11_engineering_release"]["status"] = "passed"
        self.assertTrue(
            any("engineering release precedes required stages" in item for item in self.module.validate(policy))
        )

    def test_completed_stage_needs_existing_evidence(self) -> None:
        policy = copy.deepcopy(self.policy)
        piston = policy["part_overrides"]["993-ENG-PISTON-CP1-GALLERY-F0-0001"]
        piston["stages"]["08_omniverse_simready_asset"]["evidence"] = ["missing.usd"]
        self.assertTrue(any("missing evidence" in item for item in self.module.validate(policy)))


if __name__ == "__main__":
    unittest.main()
