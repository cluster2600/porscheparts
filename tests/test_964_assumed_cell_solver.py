"""Independent load/conformity and fail-closed controls; no vehicle validation."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "twins/964-chassis/assumed-cell-20261106"


def load(name):
    spec = importlib.util.spec_from_file_location("assumed_" + name, STUDY / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder, solver = load("build"), load("solve")
nonlinear = load("nonlinear_probe")


class AssumedCellSolverTests(unittest.TestCase):
    def setUp(self):
        self.parameters = json.loads((STUDY / "assumptions.json").read_text())
        self.model = builder.build(self.parameters)
        self.card = self.parameters["laminate"]

    def test_shared_breaks_have_at_least_two_elements_even_above_strip_width(self):
        self.assertEqual(solver.linspace_breaks([0, 40, 120], 120), [0, 20, 40, 80, 120])
        nodes, elements = solver.mesh(self.model, 120)
        # The floor and tunnel wall must share complete quadratic edge triples.
        def edges(component):
            found = set()
            for element in elements:
                if element["panel"]["component"] != component:
                    continue
                for i, j, m in ((0, 1, 4), (1, 2, 5), (2, 3, 6), (3, 0, 7)):
                    edge = tuple(sorted(element["nodes"][k] for k in (i, j, m)))
                    if all(nodes[k][1:] == [130, 0] for k in edge):
                        found.add(edge)
            return found
        floor, tunnel = edges("floor"), edges("tunnel")
        self.assertGreater(len(floor), 2)
        self.assertEqual(floor, tunnel)

    def test_torsion_loads_have_independent_analytic_resultant_and_moment(self):
        nodes, elements = solver.mesh(self.model, 120)
        forces, groups = solver.make_loads(self.model, nodes, elements, "torsion")
        resultant = [sum(f[k] for f in forces.values()) for k in range(3)]
        moment = [sum(solver.cross(nodes[n], f)[k] for n, f in forces.items()) for k in range(3)]
        # Uniform +/-1000 N over y[570,720] and y[-720,-570]:
        # Mx=1000*(645-(-645)), with no force resultant or other moment.
        for actual in resultant:
            self.assertAlmostEqual(actual, 0, places=8)
        for actual, expected in zip(moment, (1290000, 0, 0)):
            self.assertAlmostEqual(actual, expected, places=7)
        for group in groups.values():
            self.assertAlmostEqual(sum(group.values()), 1)

    def test_pressure_equivalent_loads_preserve_constant_and_linear_work(self):
        nodes, elements = solver.mesh(self.model, 120)
        forces, _ = solver.make_loads(self.model, nodes, elements, "bending")
        self.assertAlmostEqual(sum(f[2] for f in forces.values()), -10000, places=7)
        # Analytical integral of unit uniform pressure's affine virtual motion:
        # mean(x+2y)=1000 on the full 2000x1440 rectangular floor.
        work = sum(f[2] * (nodes[n][0] + 2 * nodes[n][1]) for n, f in forces.items())
        self.assertAlmostEqual(work, -10000000, places=5)

    def test_fixed_node_CLOAD_is_not_double_counted_as_support_reaction(self):
        # A clamped point directly takes 2N, the free structure takes another
        # 8N. DAT RF at the clamp is reaction10 plus applied(-2), hence8.
        nodes = {1: [0, 0, 0], 2: [100, 0, 0]}
        loads = {1: [0, 0, -2], 2: [0, 0, -8]}
        result = solver.force_balance(nodes, loads, [1], [0, 0, 8])
        self.assertEqual(result["physical_clamp_reaction_RF_minus_clamp_CLOAD_N"], [0, 0, 10])
        self.assertEqual(result["force_balance_residual_N"], [0, 0, 0])
        self.assertTrue(result["translational_force_balance_verified"])

    def test_missing_or_changed_upstream_hash_fails_before_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "upstream.json"
            source.write_text("original")
            output = Path(tmp) / "result"
            with patch.object(solver, "run_solver") as run:
                with self.assertRaisesRegex(ValueError, "Preflight input hash mismatch"):
                    solver.solve(self.model, self.card, output, 120, "torsion",
                                 input_hashes={str(source): "0" * 64})
                run.assert_not_called()
                self.assertFalse(output.exists())

    def test_midrun_source_mutation_retains_preflight_but_admits_no_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "upstream.json"
            source.write_text("original")
            output = Path(tmp) / "result"
            def altered_run(directory, memory, timeout):
                (directory / "model.dat").write_text(
                    "displacements (vx,vy,vz) for set NALL\n1 0 0 1\n")
                source.write_text("substituted")
                return 0
            with patch.object(solver, "run_solver", side_effect=altered_run):
                with self.assertRaisesRegex(ValueError, "Input changed while solver ran"):
                    solver.solve(self.model, self.card, output, 120, "torsion",
                                 input_hashes={str(source): solver.sha(source)})
            self.assertTrue((output / "preflight.json").exists())
            self.assertFalse((output / "result.json").exists())

    def test_nonpositive_orthotropic_compliance_is_rejected(self):
        invalid = deepcopy(self.card)
        invalid["poisson"]["nu12"] = 100
        with self.assertRaisesRegex(ValueError, "positive definite"):
            solver.validate_material(invalid)

    def test_nonlinear_probe_changes_only_step_and_static_controls(self):
        original = "*NODE\n1,0,0,0\n*STEP\n*STATIC\n*CLOAD\n1,3,-1\n*END STEP\n"
        result = nonlinear.changed_deck(original)
        self.assertEqual(result, "*NODE\n1,0,0,0\n*STEP,NLGEOM,INC=60\n*STATIC\n"
                         "0.1,1.,1.e-5,0.25\n*CLOAD\n1,3,-1\n*END STEP\n")
        with self.assertRaisesRegex(ValueError, "exactly"):
            nonlinear.changed_deck(original + "*STEP\n")

    def test_nonlinear_parser_selects_last_complete_matching_time(self):
        def block(time, displacement, force):
            return (f"displacements (vx,vy,vz) for set NALL and time {time}\n"
                    f"1 0 0 {displacement}\n"
                    f"forces (fx,fy,fz) for set CLAMP and time {time}\n"
                    f"1 0 0 {force}\n"
                    f"total force (fx,fy,fz) for set CLAMP and time {time}\n\n"
                    f"0 0 {force}\n")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "model.dat"
            path.write_text(block(.1, -2, 1000) + block(1, -12, 10000))
            u, rf, times = nonlinear.final_dat(path)
            self.assertEqual(times, [.1, 1])
            self.assertEqual(u["U"][1], [0, 0, -12])
            self.assertEqual(rf["RF"], [0, 0, 10000])
            path.write_text(block(.1, -2, 1000))
            with self.assertRaisesRegex(ValueError, "full load"):
                nonlinear.final_dat(path)
            path.write_text(block(.1, -2, 1000) +
                            "displacements (vx,vy,vz) for set NALL and time 1\n1 0 0 -12\n")
            with self.assertRaisesRegex(ValueError, "different times"):
                nonlinear.final_dat(path)


if __name__ == "__main__":
    unittest.main()
