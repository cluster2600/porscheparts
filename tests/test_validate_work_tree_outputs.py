import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import validate_work_tree_outputs as gate  # noqa: E402


class WorkTreeOutputGateTests(unittest.TestCase):
    def test_solver_output_is_recognised(self):
        for path in (
            "work/simulation/x/case/100/U",
            "work/simulation/x/case/0.5/p",
            "work/simulation/x/case/postProcessing/pIn/0/surfaceFieldValue.dat",
            "work/simulation/x/case/processor3/0/U",
            "work/simulation/x/case/constant/polyMesh/points",
            "work/simulation/x/case/simpleFoam.log",
            "work/simulation/x/case/log.blockMesh",
        ):
            self.assertIsNotNone(gate.solver_output_reason(path), path)

    def test_case_decks_and_records_are_allowed(self):
        for path in (
            "work/simulation/x/case/0/U",
            "work/simulation/x/case/system/controlDict",
            "work/simulation/x/case/constant/transportProperties",
            "work/simulation/x/parameters.json",
            "work/simulation/x/RUN_RECORD.md",
            "work/simulation/x/results/bench_results.json",
            "twins/y/evidence/checkMesh.log",
        ):
            self.assertIsNone(gate.solver_output_reason(path), path)

    def test_repository_passes_and_register_is_consistent(self):
        self.assertEqual(gate.check_register(), [])
        tracked = [p for p in gate.tracked_paths() if gate.solver_output_reason(p)]
        self.assertEqual(tracked, [])
        register = json.loads(gate.REGISTER.read_text())
        self.assertEqual(len(register["files"]), 52)
        self.assertTrue(all(f["path"].startswith("work/simulation/993-fan-baseline/") for f in register["files"]))


if __name__ == "__main__":
    unittest.main()
