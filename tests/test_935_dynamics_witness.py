"""The dynamics-tool witness of the 935 head twin (#699) and the head's valve-train parameters.

These tests need no MuJoCo: they recheck the committed receipts against the
script, the lock and the acceptance fixed before the first run, and recompute
every closed form here, independently of the script. One test reruns the
spring-mass case when the locked MuJoCo is importable, and skips otherwise.
"""
import hashlib
import importlib.util
import json
import math
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TWIN = ROOT / "twins" / "935-cylinder-head-cad-twin"
PARAMS = TWIN / "params"
SCRIPT = TWIN / "source" / "dynamics_witness.py"
LOCK = TWIN / "source" / "dynamics-requirements.lock.txt"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name):
    return json.loads((PARAMS / name).read_text())


def closed_forms(inputs):
    """Every closed form of the witness, written again from the textbook expressions."""
    m, k, f0, e = (inputs["follower_mass_kg"], inputs["spring_rate_N_per_m"], inputs["spring_preload_N"],
                   inputs["cam_eccentricity_m"])
    chain = inputs["two_mass_chain"]
    m1, k1, m2, k2 = chain["m1_kg"], chain["k1_N_per_m"], chain["m2_kg"], chain["k2_N_per_m"]
    # (k1 + k2 - w2 m1)(k2 - w2 m2) - k2^2 = 0
    s = (k1 + k2) / m1 + k2 / m2
    p = k1 * k2 / (m1 * m2)
    w2 = sorted(((s - math.sqrt(s * s - 4 * p)) / 2, (s + math.sqrt(s * s - 4 * p)) / 2))
    wf = math.sqrt((f0 + 2 * k * e) / (m * e))
    forces = {}
    for frac in inputs["speeds_as_fraction_of_closed_form_float_speed"]["contact_force_cases"]:
        w = frac * wf
        amplitude = m * e * w * w - k * e  # N = F0 + k e + (m e w^2 - k e) cos(theta)
        forces[frac] = (f0 + k * e - abs(amplitude), f0 + k * e + abs(amplitude))
    return {
        "fn": math.sqrt(k / m) / (2 * math.pi),
        "modes": [math.sqrt(x) / (2 * math.pi) for x in w2],
        "shapes": [(k1 + k2 - x * m1) / k2 for x in w2],
        "wf": wf,
        "forces": forces,
    }


class DynamicsWitnessReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.acceptance = load("dynamics-witness-acceptance.json")
        cls.declaration = load("dynamics-witness-attempt-2.json")
        cls.first = load("dynamics-witness-rotating-cam.json")
        cls.record = load("dynamics-witness.json")
        cls.truth = closed_forms(cls.acceptance["witness_inputs"])

    def test_receipts_match_script_lock_acceptance_and_declaration(self):
        for record in (self.first, self.record):
            self.assertEqual(record["script_sha256"], sha(SCRIPT))
            self.assertEqual(record["tool"]["lock_sha256"], sha(LOCK))
            self.assertEqual(record["acceptance_sha256"], sha(PARAMS / "dynamics-witness-acceptance.json"))
            self.assertEqual(record["acceptance"], self.acceptance["accept_when"])
            self.assertEqual(record["settings"], self.acceptance["settings"])
            self.assertEqual(record["witness_inputs"], self.acceptance["witness_inputs"])
            self.assertEqual(record["tool"]["version"], self.acceptance["tool"]["version"])
        # the acceptance has not changed since the second attempt was declared
        self.assertEqual(self.declaration["acceptance_sha256"], sha(PARAMS / "dynamics-witness-acceptance.json"))
        self.assertEqual(self.record["declaration_sha256"], sha(PARAMS / "dynamics-witness-attempt-2.json"))
        self.assertEqual((self.first["attempt"], self.first["cam"]), (1, "rotating"))
        self.assertEqual((self.record["attempt"], self.record["cam"]), (2, self.declaration["cam"]))
        self.assertIn("before the first run", self.acceptance["written"])

    def test_lock_pins_every_requirement_with_hashes(self):
        lock = LOCK.read_text()
        lines = lock.splitlines()
        pins = [(i, line.split(" ")[0]) for i, line in enumerate(lines) if line and line[0].isalpha()]
        self.assertIn("mujoco==3.9.0", [pin for _, pin in pins])
        for i, pin in pins:
            self.assertIn("==", pin)
            self.assertTrue(lines[i].endswith(" \\") and lines[i + 1].startswith("    --hash=sha256:"), pin)
        self.assertIn(self.record["tool"]["wheel"]["sha256"], lock)
        self.assertIn("--exclude-newer 2026-11-01", lock)
        self.assertEqual(self.record["tool"]["licence"], "Apache-2.0")

    def test_witness_inputs_are_labelled_and_not_the_head(self):
        status = self.acceptance["witness_inputs"]["status"]
        self.assertIn("Not a value of the 935 head", status)
        self.assertIn("witness input", status)
        self.assertIn("not a run of the head", self.record["scope"])

    def test_closed_forms_recompute_and_the_tool_meets_them(self):
        accept = self.acceptance["accept_when"]
        cases = {case["case"]: case for case in self.record["cases"]}
        spring = cases["spring-mass natural frequency"]
        self.assertAlmostEqual(spring["closed_form"]["frequency_hz"], self.truth["fn"], places=9)
        self.assertLessEqual(abs(spring["tool"]["frequency_hz"] - self.truth["fn"]) / self.truth["fn"],
                             accept["natural_frequency_relative_error_within"])
        for i, (fn, shape) in enumerate(zip(self.truth["modes"], self.truth["shapes"]), 1):
            mode = cases[f"two-mass chain, mode {i}"]
            self.assertAlmostEqual(mode["closed_form"]["frequency_hz"], fn, places=9)
            self.assertAlmostEqual(mode["closed_form"]["shape_x2_over_x1"], shape, places=12)
            for key in ("frequency_hz_from_m1", "frequency_hz_from_m2"):
                self.assertLessEqual(abs(mode["tool"][key] - fn) / fn,
                                     accept["two_mass_mode_frequency_relative_error_within"])
            self.assertLessEqual(mode["tool"]["largest_shape_deviation_over_amplitude"],
                                 accept["two_mass_mode_shape_deviation_within"])
        lift = 2 * self.acceptance["witness_inputs"]["cam_eccentricity_m"]
        for frac, (low, high) in self.truth["forces"].items():
            case = cases[f"cam follower at {frac} of the float speed"]
            self.assertAlmostEqual(case["closed_form"]["force_min_N"], low, delta=1e-3)
            self.assertAlmostEqual(case["closed_form"]["force_max_N"], high, delta=1e-3)
            limit = accept["contact_force_error_over_peak_closed_form_force_within"] * high
            self.assertLessEqual(case["tool"]["largest_force_error_N"], limit)
            self.assertLessEqual(abs(case["tool"]["force_min_N"] - low), limit)
            self.assertLessEqual(abs(case["tool"]["force_max_N"] - high), limit)
            self.assertLessEqual(case["tool"]["largest_lift_error_m"],
                                 accept["follower_lift_error_over_full_lift_within"] * lift)
            self.assertLessEqual(case["tool"]["tappet_off_lift_law_over_full_lift"],
                                 self.declaration["added_check"]["tappet_off_lift_law_over_full_lift_within"])
        floating = cases["float speed"]
        self.assertAlmostEqual(floating["closed_form"]["float_speed_rad_s"], self.truth["wf"], places=9)
        self.assertLessEqual(abs(floating["tool"]["float_speed_rad_s"] - self.truth["wf"]) / self.truth["wf"],
                             accept["float_speed_relative_error_within"])
        self.assertTrue(self.record["passed"])
        self.assertTrue(all(check["passed"] for check in self.record["checks"]))

    def test_the_float_detector_and_the_planted_faults_can_fail(self):
        checks = {check["check"]: check for check in self.record["checks"]}
        stay = [c for name, c in checks.items() if name.startswith("float detector: contact kept")][0]
        leave = [c for name, c in checks.items() if name.startswith("float detector: contact lost")][0]
        self.assertFalse(stay["detail"]["contact_lost"])
        self.assertTrue(leave["detail"]["contact_lost"])
        self.assertGreater(leave["detail"]["largest_separation_m"], 1e-5)
        declared = self.acceptance["controls_that_must_fail"]
        for record in (self.first, self.record):
            self.assertEqual(len(record["controls"]), len(declared))
            for control, name in zip(record["controls"], declared):
                self.assertTrue(control["control"].startswith(name), control["control"])
                self.assertTrue(control["caught"], control["control"])
        mass = self.record["controls"][0]
        self.assertAlmostEqual(mass["value"], 1 - math.sqrt(1 / 1.1), places=4)

    def test_the_first_attempt_failed_and_its_limitation_stays_recorded(self):
        self.assertFalse(self.first["passed"])
        failed = {check["check"] for check in self.first["checks"] if not check["passed"]}
        self.assertIn("cam at 0.9: contact force within the declared share of the peak force", failed)
        self.assertIn("float detector: contact kept at 0.9 of the float speed", failed)
        self.assertIn("float speed: the declared bracket holds the tool's float speed", failed)
        self.assertFalse(any(name.startswith(("natural frequency", "two-mass", "control:")) for name in failed))
        self.assertEqual(self.declaration["first_attempt"]["record"],
                         "twins/935-cylinder-head-cad-twin/params/dynamics-witness-rotating-cam.json")
        self.assertFalse(self.declaration["first_attempt"]["passed"])
        self.assertIn("not admissible", self.declaration["for_the_head"])
        [limitation] = self.record["limitations"]
        self.assertTrue(limitation["contact_lost"])
        self.assertEqual(limitation["tool_force_min_N"], 0.0)
        self.assertAlmostEqual(limitation["closed_form_force_min_N"], self.truth["forces"][0.5][0], delta=1e-3)

    @unittest.skipUnless(importlib.util.find_spec("mujoco"), "the locked MuJoCo is not installed here")
    def test_spring_mass_case_reruns(self):
        import mujoco

        if mujoco.__version__ != self.acceptance["tool"]["version"]:
            self.skipTest(f"MuJoCo {mujoco.__version__} is not the locked version")
        spec = importlib.util.spec_from_file_location("dynamics_witness", SCRIPT)
        witness = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(witness)
        settings, inputs = self.acceptance["settings"], self.acceptance["witness_inputs"]
        m, k = inputs["follower_mass_kg"], inputs["spring_rate_N_per_m"]
        run = witness.run_free(mujoco, witness.spring_mass_xml(settings, m, k),
                               [inputs["free_oscillation_amplitude_m"]], 5 / self.truth["fn"])
        f = witness.measured_frequency(run["times"], [q[0] for q in run["q"]])
        self.assertLessEqual(abs(f - self.truth["fn"]) / self.truth["fn"],
                             self.acceptance["accept_when"]["natural_frequency_relative_error_within"])


class ValveTrainParameterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.params = load("valve-train-parameters.json")

    def entries(self):
        for group in ("per_valve", "per_head"):
            for name, entry in self.params[group].items():
                yield f"{group}.{name}", entry

    def test_every_entry_is_null_with_a_named_blocker(self):
        names = []
        for name, entry in self.entries():
            names.append(name)
            self.assertIsNone(entry["value"], name)
            self.assertIsNone(entry["source"], name)
            self.assertEqual(entry["status"], "missing", name)
            self.assertTrue(entry["unit"], name)
            self.assertTrue(entry["blockers"], name)
            for blocker in entry["blockers"]:
                self.assertIn(blocker, self.params["blockers"], name)
        self.assertGreaterEqual(len(names), 20)
        self.assertIn("#698", self.params["blockers"]["698"])
        self.assertIn("0019-accept-contributed-measurements.md", self.params["blockers"]["0019"])
        self.assertTrue((ROOT / self.params["blockers"]["0019"].split(":")[0]).exists())
        self.assertIn("Nothing here is a value", self.params["scope"])

    def test_every_load_case_input_has_an_entry(self):
        contract = json.loads((ROOT / self.params["load_case"]["file"]).read_text())
        case = [c for c in contract["load_cases"] if c["load_case_id"] == self.params["load_case"]["id"]][0]
        mapped = {entry["lc_input"] for _, entry in self.entries() if "lc_input" in entry}
        self.assertEqual(mapped, set(case["required_inputs"]))

    def test_the_valves_are_the_fitted_axes(self):
        fits = load("feature-fits.json")
        fitted = {name for name in fits["group_datums"] if name.startswith("valve_")}
        self.assertEqual(set(self.params["valves"]), fitted)

    def test_toolchain_register_and_readme_point_to_the_witness(self):
        toolchain = (ROOT / "docs" / "TOOLCHAIN.md").read_text()
        self.assertIn("| Valve-train dynamics, small multibody systems | MuJoCo 3.9.0", toolchain)
        self.assertIn("dynamics_witness.py", toolchain)
        self.assertIn("dynamics-requirements.lock.txt", toolchain)
        guide = (ROOT / "docs" / "AGENT_TOOL_GUIDE.md").read_text()
        self.assertIn("| Valve-train dynamics, small multibody | MuJoCo 3.9.0", guide)
        self.assertIn("A contact on a turning body is not held", guide)
        register = load("prepared-work.json")
        train = [part for part in register["parts"] if part["id"] == "valve-train"][0]
        self.assertEqual(train["tool"]["witness"], str(SCRIPT.relative_to(ROOT)))
        self.assertIn("params/dynamics-witness.json", train["tool"]["witness_state"])
        self.assertTrue(train["state"].startswith("blocked on kinematics"))
        self.assertTrue(any(h["where"].endswith("valve-train-parameters.json") for h in train["held"]))
        readme = (TWIN / "README.md").read_text()
        self.assertIn("### Dynamics tool: MuJoCo against closed forms", readme)
        self.assertIn("**None of them is a value of this head.**", readme)


if __name__ == "__main__":
    unittest.main()
