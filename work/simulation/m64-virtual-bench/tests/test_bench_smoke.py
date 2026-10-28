"""Smoke test for the M64/60 virtual test bench (0D, deterministic).

Run:  python3 -m unittest discover -s simulation/m64-virtual-bench/tests
  or: python3 simulation/m64-virtual-bench/tests/test_bench_smoke.py

Checks: end-to-end run, calibration anchors reproduced, physics
bookkeeping closes (heat split, energy ordering), output files written,
and byte-identical determinism across two full runs.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
SOURCE = BENCH / "source"
sys.path.insert(0, str(SOURCE))

from bench import cooling_air, dyno, fuel  # noqa: E402


def _load_runner():
    spec = importlib.util.spec_from_file_location(
        "run_bench", SOURCE / "run_bench.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class BenchSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner = _load_runner()
        cls.rows, cls.part, cls.dev, cls.v = cls.runner.build()

    def test_sweep_grid_complete_and_sorted(self):
        self.assertGreaterEqual(len(self.rows), 24)
        rpms = [r["rpm"] for r in self.rows]
        self.assertEqual(rpms, sorted(rpms))
        self.assertIn(4050.0, rpms)
        self.assertIn(5750.0, rpms)

    def test_calibration_anchors_exact(self):
        at = {r["rpm"]: r for r in self.rows}
        self.assertAlmostEqual(at[5750.0]["power_kw"], 300.0, delta=1e-9)
        self.assertAlmostEqual(at[4050.0]["torque_nm"], 540.0, delta=1e-9)

    def test_deviation_table_rows_bounded(self):
        labels = {d["label"]: d for d in self.dev}
        self.assertIn("peak_power", labels)
        self.assertIn("peak_torque", labels)
        for d in self.dev:
            if d["label"] in ("peak_power", "peak_torque",
                              "power_at_public_peak_rpm",
                              "torque_at_public_torque_rpm",
                              "cooling_air_flow_at_6100"):
                self.assertLess(abs(d["rel_error_percent"]), 5.0, d["label"])

    def test_heat_split_closes(self):
        self.assertAlmostEqual(cooling_air.SPLIT_SUM, 1.0, delta=1e-12)
        for r in self.rows:
            total = (r["q_cooling_air_kw"] + r["q_oil_kw"]
                     + r["q_exhaust_kw"]
                     + cooling_air.SPLIT_RADIATED * r["p_chem_kw"])
            self.assertAlmostEqual(total, r["p_chem_kw"], delta=1e-9)

    def test_energy_ordering_and_finite_outputs(self):
        for r in self.rows + self.part:
            self.assertLess(r["p_wheel_kw"], r["p_brake_crank_kw"])
            self.assertGreater(r["m_dot_air_kg_s"], 0.0)
            self.assertGreater(r["m_dot_fuel_kg_s"], 0.0)
            self.assertLessEqual(r["eta_brake"], 0.5)
            self.assertGreaterEqual(r["oil_flow_required_l_min"], 14.4 - 1e-9)
            for key in ("cooling_air_dt_implied_k", "bsfc_g_kwh"):
                self.assertGreater(r[key], 0.0)

    def test_partload_monotone_in_throttle(self):
        by_thr = {}
        for r in self.part:
            if r["rpm"] == 3000.0:
                by_thr[r["thr"]] = r["power_kw"]
        self.assertEqual(sorted(by_thr), [0.25, 0.50, 0.75, 1.0])
        seq = [by_thr[t] for t in (0.25, 0.50, 0.75, 1.0)]
        self.assertEqual(seq, sorted(seq))

    def test_full_run_writes_outputs_deterministically(self):
        import bench.common as common
        orig = self.runner.RESULTS
        try:
            with tempfile.TemporaryDirectory() as td:
                results_dir = Path(td) / "results"
                self.runner.RESULTS = results_dir
                run1 = self.runner.build()
                w1 = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in self.runner.write_outputs(*run1)}
                run2 = self.runner.build()
                w2 = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in self.runner.write_outputs(*run2)}
                self.assertEqual(set(w1), {
                    "bench_results.json", "sweep_wot.csv",
                    "sweep_partload.csv", "deviation_table.csv",
                    "report.md"})
                self.assertEqual(w1, w2)
                js = json.loads(
                    (results_dir / "bench_results.json").read_text())
                self.assertEqual(js["dataset_id"], "M64-VIRTUAL-BENCH-0002")
        finally:
            self.runner.RESULTS = orig

    def test_inputs_gap_register_exists_with_asks(self):
        md = (BENCH / "inputs-gap.md").read_text(encoding="utf-8")
        for acq in ("M64-ACQ-BENCH-02", "M64-ACQ-BENCH-04",
                    "M64-ACQ-BENCH-05", "M64-ACQ-0003"):
            self.assertIn(acq, md)


if __name__ == "__main__":
    unittest.main(verbosity=2)
