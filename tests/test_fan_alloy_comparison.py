"""Dimensional invariants and evidence coverage for conditional alloy screening."""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "twins/fan-alloy-comparison-f0/source/compare_alloys.py"
spec = importlib.util.spec_from_file_location("alloy_comparison", SOURCE)
comparison = importlib.util.module_from_spec(spec)
spec.loader.exec_module(comparison)


class AlloyScalingTests(unittest.TestCase):
    def test_thin_ring_analytic_centrifugal_stress_and_extension(self):
        # Independently check sigma = rho*omega^2*r^2 and dr = sigma*r/E.
        rho, young, radius, rpm = 1830., 44.1e9, .15, 8500.
        ref_sigma = 2670.*(10000.*math.pi/30.)**2*.1**2
        sigma = rho*(rpm*math.pi/30.)**2*radius**2
        factors = comparison.scale_factors(1.83,44.1,rpm,1.5)
        self.assertAlmostEqual(ref_sigma*factors["centrifugal_stress"],sigma)
        ref_dr = ref_sigma*.1/70e9
        self.assertAlmostEqual(ref_dr*factors["centrifugal_displacement"],sigma*radius/young)

    def test_uniform_scale_mass_inertia_and_frequency(self):
        f = comparison.scale_factors(2.67,70.,10000.,2.)
        self.assertEqual(f["mass"],8.)
        self.assertEqual(f["inertia"],32.)
        self.assertEqual(f["unprestressed_frequency"],.5)

    def test_double_rpm_preserves_mass_and_modes_and_quadruples_load(self):
        f = comparison.scale_factors(2.67,70.,20000.)
        self.assertEqual(f["mass"],1.)
        self.assertEqual(f["unprestressed_frequency"],1.)
        self.assertEqual(f["centrifugal_stress"],4.)
        self.assertEqual(f["centrifugal_displacement"],4.)

    def test_negative_zero_nan_and_infinity_rejected(self):
        for value in (-1.,0.,float("nan"),float("inf"),True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                comparison.scale_factors(value,70.,10000.)

    def test_magnesium_has_no_invented_tensile_allowable(self):
        cards = comparison.load_cards(SOURCE.parents[1]/"materials.json")
        mg = next(c for c in cards["materials"] if c["id"]=="we43")
        self.assertIsNone(mg["tensile_yield_comparator_MPa"])
        self.assertFalse(mg["process_qualified_for_part"])


class SolverReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.case = Path(self.temp.name)
        deck = "*NODE\n1,0,0,0\n2,1,0,0\n*ELEMENT,TYPE=C3D10\n1,1,2,1,2,1,2,1,2,1,2\n*END\n"
        (self.case/"rotor.inp").write_text(deck)
        self.digest = hashlib.sha256(deck.encode()).hexdigest()
        (self.case/"log.rotor").write_text("CalculiX Version 2.20\nJob finished\n")
        (self.case/"rotor.dat").write_text(
            " displacements (vx,vy,vz)\n1 3 4 0\n2 0 0 2\n"
            " stresses (sxx,syy,szz,sxy,sxz,syz)\n1 1 10 0 0 0 0 0\n1 2 0 0 0 10 0 0\n")

    def test_keeps_peak_integration_point_and_euclidean_displacement(self):
        result = comparison.static_results(self.case,self.digest)
        self.assertAlmostEqual(result["von_mises_max_MPa"],math.sqrt(300.))
        self.assertEqual(result["maximum_displacement_mm"],5.)

    def test_rejects_missing_displacements(self):
        p=self.case/"rotor.dat";p.write_text(p.read_text().replace("2 0 0 2\n",""))
        with self.assertRaisesRegex(ValueError,"coverage"):
            comparison.static_results(self.case,self.digest)

    def test_rejects_changed_deck(self):
        (self.case/"rotor.inp").write_text("changed")
        with self.assertRaisesRegex(ValueError,"changed"):
            comparison.static_results(self.case,self.digest)

    def test_rejects_failed_solver_even_with_completion_line(self):
        (self.case/"log.rotor").write_text("Version 2.20\n*ERROR\nJob finished\n")
        with self.assertRaisesRegex(ValueError,"failed"):
            comparison.static_results(self.case,self.digest)


class PublishedComparisonTests(unittest.TestCase):
    def test_provenance_and_unknowns_are_preserved(self):
        folder=SOURCE.parents[1]
        manifest=json.loads((folder/"results/manifest.json").read_text())
        for name,digest in manifest["files_sha256"].items():
            self.assertEqual(comparison.sha(folder/"results"/name),digest)
        result=json.loads((folder/"results/comparison.json").read_text())
        self.assertEqual(result["material_cards_sha256"],comparison.sha(folder/"materials.json"))
        self.assertEqual(result["fresh_solver_runs"],{"static":3,"unprestressed_modal":1})
        for name in ("safe_speed_rpm","fatigue_life_cycles","installed_airflow_m3_s"):
            self.assertIsNone(result[name])
        for name in ("mass_kg","maximum_stress_MPa"):
            self.assertIsNone(result["935"][name])
        self.assertFalse(result["manufacturing_authorized"])
        self.assertFalse(result["digital_twin_calibrated"])
        self.assertEqual(len(result["rpm_sweep"]),15)

if __name__ == "__main__":
    unittest.main()
