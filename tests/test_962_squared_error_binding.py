"""Pin the VTK numeric squared-error input without claiming a Hausdorff guarantee."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "twins/962-cylinder-head-f0/source"))
from prepare_head_analysis_squared import CONTRACT, CONTRACT_SHA256, squared_error_setting


class SquaredErrorBindingTests(unittest.TestCase):
    def test_quarter_millimetre_input_uses_square_millimetres(self):
        self.assertEqual(squared_error_setting(.25), .0625)
        # Runtime geometry binding stays mandatory; this unit test needs only the frozen contract.
        raw = CONTRACT.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), CONTRACT_SHA256)
        contract = json.loads(raw)
        self.assertEqual(contract["preparation"]["numeric_absolute_squared_error_mm2"], squared_error_setting(contract["representation_deviation_budget_mm"]))
        self.assertEqual(contract["surface_gates"]["two_sided_continuous_distance_upper_bound_mm"], .25)
        self.assertFalse(contract["preparation"]["further_heuristic_parameter_tuning_authorized"])

    def test_invalid_distance_scales_are_rejected(self):
        for value in [0, -1, float("nan"), float("inf")]:
            with self.assertRaises(ValueError):
                squared_error_setting(value)


if __name__ == "__main__":
    unittest.main()
