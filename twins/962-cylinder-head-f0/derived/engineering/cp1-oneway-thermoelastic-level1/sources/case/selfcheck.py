"""Prepared stdlib/AST guards only. Never calls native, converter main, or actual161 CSV conversion."""

import ast
import csv
from fractions import Fraction
import hashlib
import io
import json
import math
from pathlib import Path
import unittest

PREP = Path(__file__).resolve().parent
SOURCE_SHA = "3bf2ff5ccd9a4e22352ac9128e53f9a71093a9734069f77305b7883c4e4b3bfa"
ADAPTER_SHA = "c4eaca5d669c274adfb2907155ea351e0d72d2aa516a8ab1806f470f686636de"
DECK_SHA = "98eb61ad8f924229de1a2ee62f250dd8c2ffbe3b2c48248aa78bef1a2674b86a"


def load_pure():
    source = (PREP / "prepare_transfer.py").read_bytes()
    if hashlib.sha256(source).hexdigest() != SOURCE_SHA:
        raise ValueError("Frozen preparation source changed")
    wanted = {"need", "expected_files", "parse_rows", "join_rows", "phase_join", "table_text", "spatial_tokens", "assemble"}
    tree = ast.parse(source)
    definitions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in wanted]
    if {n.name for n in definitions} != wanted:
        raise ValueError("Exact pure-function set required")
    ns = dict(csv=csv, io=io, math=math, STEPS=80, BIRTH_STEP=40, HISTORY_TOL_K=1e-10,
              AXES=(tuple(i / 8 for i in range(17)), tuple(i / 4 for i in range(5)), tuple(i / 4 for i in range(5))),
              SUPPORTS=((0, (0., 0., 0.), (0, 1, 2)), (32, (1., 0., 0.), (1, 2)), (137, (0., 1., 0.), (2,))))
    exec(compile(ast.Module(body=definitions, type_ignores=[]), str(PREP / "prepare_transfer.py"), "exec"), ns)
    return ns


def sections(text):
    stack, result = [], {}
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            name = line[1:-1]
            if name:
                stack.append(name)
                result.setdefault("/".join(stack), {})
            else:
                stack.pop()
        elif "=" in line:
            key, value = line.split("=", 1)
            result["/".join(stack)][key.strip()] = value.strip().strip("'")
    return result


class Guards(unittest.TestCase):
    def test_exact161_phase_names_and_source_identity_index(self):
        ns = load_pure()
        files = ns["expected_files"]()
        self.assertEqual(len(files), 161)
        self.assertEqual(files[0], (0, "end", "thermal_end_0000.csv"))
        self.assertEqual(files[-1], (80, "end", "thermal_end_0080.csv"))
        self.assertEqual(files[79:81], [(40, "begin", "thermal_begin_0040.csv"), (40, "end", "thermal_end_0040.csv")])
        index = json.loads((PREP / "thermal-input-index.json").read_text())
        self.assertEqual([(x["step"], x["phase"], x["filename"]) for x in index["selected"]], files)
        self.assertTrue(index["additional_initial_BEGIN_alias"]["same_hash_as_selected_END0000"])

    def test_ID_order_nonfinite_coordinate_and_signed_zero_refusals(self):
        ns = load_pure()
        header = "id,temperature,x,y,z\n"
        for body in ("0,400,0,0,0\n0,400,1,0,0\n", "1,400,0,0,0\n0,400,1,0,0\n", "0,nan,0,0,0\n"):
            with self.assertRaises(ValueError):
                ns["parse_rows"](header + body)
        row = ns["parse_rows"](header + "0,400,-0,0,0\n")
        with self.assertRaises(ValueError):
            ns["join_rows"](row, {0: (0., 0., 0.)}, {0})
        with self.assertRaises(ValueError):
            ns["join_rows"]({}, {0: (0., 0., 0.)}, {0})

    def test_asymmetric_birth_reference_includes25shared_and_distinct_END(self):
        ns = load_pure()
        positions = [(x, y, z) for z in ns["AXES"][2] for y in ns["AXES"][1] for x in ns["AXES"][0]]
        # Deliberately non-lexicographic IDs, with the three observed support associations.
        required = {0: (0., 0., 0.), 32: (1., 0., 0.), 137: (0., 1., 0.)}
        geometry = dict(required)
        free = iter(i for i in range(425) if i not in required)
        for p in positions:
            if p not in required.values():
                geometry[next(free)] = p
        old = {t for t, p in geometry.items() if p[0] <= 1.}
        def rows(step):
            active = old if step < 40 else set(geometry)
            return {tag: dict(position=geometry[tag], temperature=(400. if tag in old else 350.) + step * 1e-8,
                              token=format((400. if tag in old else 350.) + step * 1e-8, ".17g"))
                    for tag in sorted(active)}
        samples = {(0, "end"): rows(0)}
        for step in range(1, 81):
            begin = {k: dict(v) for k, v in samples[(step - 1, "end")].items()}
            if step == 40:
                begin.update({tag: dict(position=geometry[tag], temperature=350., token="350")
                              for tag in set(geometry) - old})
                begin = dict(sorted(begin.items()))
            samples[(step, "begin")] = begin
            samples[(step, "end")] = rows(step)
        tables, mapping = ns["assemble"](samples)
        self.assertEqual((mapping["old_node_count"], mapping["born_reference_DOF_count"], mapping["shared_node_count"]), (225, 225, 25))
        birth = tables["born-begin40.grid"].split("DATA\n")[1].split()
        self.assertEqual(len(birth), 225)
        self.assertEqual(sum(float(v) > 399 for v in birth), 25)
        self.assertEqual(sum(float(v) == 350 for v in birth), 200)
        self.assertNotEqual(birth[0], tables["born-end.grid"].split("DATA\n")[1].split()[0])
        bad = dict(samples)
        bad[(40, "begin")] = samples[(40, "end")]
        with self.assertRaises(ValueError):
            ns["assemble"](bad)

    def test_X_fastest_complete_table_and_no_clamping_padding(self):
        ns = load_pure()
        text = ns["table_text"]((("X", (0., 1.)), ("Y", (0., 1.)), ("Z", (0.,))), ["0", "1", "10", "11"])
        self.assertEqual(text.split("DATA\n")[1].split(), ["0", "1", "10", "11"])
        with self.assertRaises(ValueError):
            ns["table_text"]((("X", (0., 0.)), ("Y", (0.,)), ("Z", (0.,))), ["0", "1"])
        with self.assertRaises(ValueError):
            ns["table_text"]((("X", (0., 1.)), ("Y", (0.,)), ("Z", (0.,))), ["0"])

    def test_six_supports_remove_rigid_modes_and_allow_uniform_expansion(self):
        ns = load_pure()
        matrix = []
        for _, p, components in ns["SUPPORTS"]:
            x, y, z = map(Fraction, p)
            rows = ((1, 0, 0, 0, z, -y), (0, 1, 0, -z, 0, x), (0, 0, 1, y, -x, 0))
            for component in components:
                matrix.append(list(map(Fraction, rows[component])))
                self.assertEqual(p[component], 0.)  # u=alpha*DeltaT*(x,y,z) satisfies every support.
        for column in range(6):
            pivot = next((i for i in range(column, 6) if matrix[i][column]), None)
            self.assertIsNotNone(pivot)
            matrix[column], matrix[pivot] = matrix[pivot], matrix[column]
            divisor = matrix[column][column]
            matrix[column] = [v / divisor for v in matrix[column]]
            for i in range(column + 1, 6):
                factor = matrix[i][column]
                matrix[i] = [a - factor * b for a, b in zip(matrix[i], matrix[column])]

    def test_prescribed_Aux_birth_scope_order_and_complete_capture(self):
        deck = (PREP / "thermoelastic-birth.i").read_bytes()
        self.assertEqual(hashlib.sha256(deck).hexdigest(), DECK_SHA)
        s = sections(deck.decode())
        self.assertNotIn("Variables/temperature", s)
        self.assertNotIn("Variables/born_reference_temperature", s)
        self.assertEqual(s["AuxVariables/born_reference_temperature"]["block"], "3")
        self.assertEqual(s["ICs/born_reference"]["block"], "3")
        self.assertEqual(s["ICs/born_reference"]["function"], "born_begin40")
        self.assertEqual(s["Materials/old_thermal"]["stress_free_temperature"], "400")
        self.assertEqual(s["Materials/born_thermal"]["stress_free_temperature"], "born_reference_temperature")
        self.assertEqual(s["Mesh"]["add_subdomain_ids"], "3")
        birth = s["MeshModifiers/birth"]
        self.assertEqual(birth["reinitialize_variables"].split(), ["disp_x", "disp_y", "disp_z", "temperature", "born_reference_temperature"])
        self.assertEqual(birth["restore_overridden_dofs"].split(), ["true", "true", "true", "true", "false"])
        self.assertEqual((birth["force_preaux"], birth["execution_order_group"], birth["blocks_to"]), ("true", "-100", "3"))
        self.assertEqual({v["variable"] for k, v in s.items() if k.startswith("AuxKernels/")}, {"temperature"})
        for name in ("begin", "reference_begin", "begin_fields"):
            self.assertEqual(s["VectorPostprocessors/" + name]["force_preaux"], "true")
            self.assertEqual(s["VectorPostprocessors/" + name]["execution_order_group"], "-50")
        self.assertEqual(s["Kernels/inactive_placeholder"]["block"], "1")
        self.assertEqual([k for k, v in s.items() if v.get("type") == "ADTimeDerivative"], ["Kernels/inactive_placeholder"])
        self.assertEqual(len(s["VectorPostprocessors/end_fields"]["property"].split()), 30)
        self.assertEqual(s["Outputs"]["exodus"], "true")

    def test_adapter_preserves_owned_cleanup_and_selected_limits(self):
        adapter = (PREP / "run_mac.py").read_bytes()
        self.assertEqual(hashlib.sha256(adapter).hexdigest(), ADAPTER_SHA)
        tree = ast.parse(adapter)
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
        popen = [n for n in calls if isinstance(n.func, ast.Attribute) and n.func.attr == "Popen"]
        self.assertEqual(len(popen), 1)
        self.assertTrue(any(k.arg == "start_new_session" and isinstance(k.value, ast.Constant) and k.value.value is True for k in popen[0].keywords))
        self.assertTrue(any(isinstance(n.func, ast.Attribute) and n.func.attr == "killpg" for n in calls))
        self.assertIn('RSS_scope="sampled_owned_leader_only"', adapter.decode())
        held = json.loads((PREP / "held-preparation.json").read_text())
        self.assertEqual(held["coupon_resources"], dict(wall_seconds=100, sampled_RSS_stop_bytes=2 * 1024**3, sampled_output_stop_bytes=512 * 1024**2))
        self.assertEqual(len(held["runtime_sha256s"]), 19)
        self.assertEqual(len(held["runtime_symlinks"]), 13)

    def test_source_contract_hold_and_newborn_reference_displacement_gate(self):
        frozen = json.loads((PREP / "case-contract.json").read_text())
        card = json.loads((PREP / "card.json").read_text())
        self.assertEqual(frozen["card"], card)
        self.assertEqual(frozen["card_sha256"], hashlib.sha256((PREP / "card.json").read_bytes()).hexdigest())
        self.assertFalse(frozen["native_execution_authorized"])
        self.assertIsNone(frozen["independent_3D_assessment_source"])
        self.assertEqual(card["birth"]["old_constant_stress_free_temperature_K"], 400.)
        self.assertTrue(frozen["acceptance_requirements"]["born_BEGIN40_displacement_reference_required"])
        self.assertFalse(card["time"]["source_off_cooling_history_present"])
        self.assertEqual(card["time"], dict(dt_s=.005, steps=80, birth_step=40, birth_time_s=.2, end_time_s=.4,
                                           source_off_cooling_history_present=False, thermal_selected_level=1))
        self.assertEqual(frozen["capture"]["quadrature_fields"]["rows_per_phase_total"], 124928)
        self.assertEqual(frozen["temperature_table_files"], ["old-end.grid", "born-end.grid", "born-begin40.grid"])
        s = sections((PREP / "thermoelastic-birth.i").read_text())
        self.assertEqual({k:s["Executioner"][k] for k in ("dt", "end_time", "solve_type", "nl_rel_tol", "nl_abs_tol", "nl_max_its")},
                         dict(dt="0.005", end_time="0.4", solve_type="NEWTON", nl_rel_tol="1e-11", nl_abs_tol="1e-10", nl_max_its="30"))
        held = json.loads((PREP / "held-preparation.json").read_text())
        self.assertEqual(held["planned_transfer"]["table_value_counts"], {"old-end.grid":18225,"born-end.grid":9225,"born-begin40.grid":225})
        self.assertEqual(held["unchanged_assessment_absolute_SI_limits"], dict(temperature_K=1e-10, displacement_m=1e-12,
                           QP_coordinate_m=2e-13, strain=1e-10, stress_Pa=.1, force_N=1e-7, moment_Nm=1e-7))


    def test_explicit_temperature_IC_scopes_and_no_generated_overlap(self):
        from copy import deepcopy
        s = sections((PREP / "thermoelastic-birth.i").read_text())
        self.assertNotIn("initial_condition", s["AuxVariables/temperature"])
        self.assertEqual(s["ICs/old_temperature"], dict(type="FunctionIC", variable="temperature", function="400", block="2"))
        self.assertEqual(s["ICs/born_temperature"], dict(type="FunctionIC", variable="temperature", function="born_begin40", block="3"))
        self.assertEqual(s["ICs/born_reference"]["function"], "born_begin40")
        def overlaps(parts):
            assignments = []
            for path, values in parts.items():
                if path.startswith(("Variables/", "AuxVariables/")) and "initial_condition" in values:
                    assignments.append((path, path.split("/")[-1], set(values.get("block", "*").split())))
                if path.startswith("ICs/") and "variable" in values:
                    self.assertNotIn("state", values)  # Fixed case uses default current-state ICs only.
                    assignments.append((path, values["variable"], set(values.get("block", "*").split())))
            return [(a[0], b[0]) for i, a in enumerate(assignments) for b in assignments[i+1:]
                    if a[1] == b[1] and ("*" in a[2] or "*" in b[2] or a[2] & b[2])]
        self.assertEqual(overlaps(s), [])
        inline = [(p, v["initial_condition"]) for p, v in s.items() if p.startswith(("Variables/", "AuxVariables/")) and "initial_condition" in v]
        self.assertEqual(inline, [("Variables/inactive_placeholder", "0")])
        bad = deepcopy(s); bad["AuxVariables/temperature"]["initial_condition"] = "400"
        self.assertTrue(overlaps(bad))
        bad = deepcopy(s); bad["ICs/duplicate_birth"] = deepcopy(bad["ICs/born_temperature"])
        self.assertTrue(overlaps(bad))



if __name__ == "__main__":
    unittest.main()
