"""Tests of the 935 head interface contract and its checker (#694).

The contract lists every interface of the scanned head with every value null. The checker compares an admitted
value with the twin's own number; it must not share code with the scripts that produced the twin. These tests
run on the committed JSON and on synthetic contracts only.
"""

import ast
import contextlib
import copy
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TWIN = ROOT / "twins" / "935-cylinder-head-cad-twin"
PARAMS = TWIN / "params"
CHECKER = TWIN / "source" / "check_interface_contract.py"

spec = importlib.util.spec_from_file_location("check_interface_contract_935", CHECKER)
ck = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ck)

BLOCKER_CODES = {"#692-identity", "#693-scale", "drawing", "contribution-0019"}


def load(name):
    return json.loads((PARAMS / name).read_text())


def quantities(contract):
    return [q for i in contract["interfaces"] for q in i["quantities"]]


class CommittedContractTests(unittest.TestCase):
    def setUp(self):
        self.contract = load("interface-contract.json")
        self.hypotheses = json.loads((TWIN / "hypotheses.json").read_text())
        self.by_id = {i["id"]: i for i in self.contract["interfaces"]}
        self.q = {q["id"]: q for q in quantities(self.contract)}

    def test_every_interface_the_issue_names_is_listed(self):
        required = {
            "deck_and_register": ["deck_flatness", "register_diameter", "register_depth", "clamping_face"],
            "stud_passages": ["x_minus_y_minus.passage_diameter", "x_plus_y_plus.axis_direction",
                              "x_minus_y_plus.nut_seat_level", "head_stud_designation"],
            "stud_pattern": ["cam_x_minus_y_minus.tapped_thread", "flange_y_plus_x_plus.tapped_depth"],
            "port_flange_y_minus": ["face_level", "face_flatness", "opening_shape", "bolt_spacing", "port_role"],
            "port_flange_y_plus": ["face_level", "face_flatness", "opening_shape", "bolt_spacing", "port_role"],
            "plug_bore_x_plus": ["thread_designation", "thread_length", "seat_face_squareness", "axis_direction"],
            "plug_bore_x_minus": ["thread_designation", "thread_length", "seat_face_squareness", "axis_direction"],
            "cam_housing_face": ["face_level", "pad_coplanarity", "sealing_outline"],
            "valve_cover_face": ["present_on_this_head", "face_level", "fastener_pattern"],
            "valve_y_minus": ["guide_bore_diameter", "seat_half_angle", "guide_interference", "role"],
            "valve_y_plus": ["guide_bore_diameter", "seat_half_angle", "guide_interference", "role"],
        }
        for iface, names in required.items():
            self.assertIn(iface, self.by_id)
            for name in names:
                self.assertIn(f"{iface}.{name}", self.q)
        self.assertEqual(len(self.contract["interfaces"]), len(self.by_id))

    def test_the_ten_studs_are_the_rods_that_pass_the_stud_test(self):
        frame, occ = load("frame.json"), load("occupancy-summary.json")
        accepted = {(s["group"], tuple(s["point_on_axis"])) for s in occ["studs"] if s["accepted"]}
        self.assertEqual(len(accepted), 10)
        studs = self.by_id["stud_pattern"]["studs"]
        listed = set()
        for s in studs:
            _, group, idx = s["frame_rod"]["key"]
            listed.add((group, tuple(frame["rods"][group][idx]["point_on_axis"])))
        self.assertEqual(listed, accepted)
        faces = [s["stands_on"] for s in studs]
        self.assertEqual(faces.count("cam_housing_face"), 6)
        self.assertEqual(faces.count("port_flange_y_minus"), 2)
        self.assertEqual(faces.count("port_flange_y_plus"), 2)
        for s in studs:
            for part in ("position_at_face", "axis_direction", "tapped_thread", "tapped_depth"):
                self.assertEqual(self.q[f"stud_pattern.{s['stud']}.{part}"]["hypothesis"], "H03-stud-tapped-holes")

    def test_the_four_passages_carry_h02_and_the_plug_threads_h06(self):
        passages = [q for q in self.q.values() if q["id"].startswith("stud_passages.")]
        self.assertEqual(len({q["id"].split(".")[1] for q in passages if q["id"].count(".") == 2}), 4)
        self.assertTrue(all(q["hypothesis"] == "H02-stud-passages" for q in passages))
        for side in ("x_plus", "x_minus"):
            for part in ("thread_designation", "thread_length", "thread_bore_diameter"):
                self.assertEqual(self.q[f"plug_bore_{side}.{part}"]["hypothesis"], "H06-spark-plug-threads")

    def test_every_value_is_null_unless_it_has_a_source_and_every_gap_has_a_blocker(self):
        register = {i["id"] for i in self.hypotheses["items"]}
        self.assertEqual(set(self.contract["blocker_codes"]), BLOCKER_CODES)
        for q in self.q.values():
            if q["value"] is not None:
                self.assertTrue(q["source"], q["id"])
                self.assertIsNotNone(q["uncertainty"], q["id"])
            # Nothing is measured yet: every field an admitted source would fill is null.
            for field in ("value", "uncertainty", "source", "threshold"):
                self.assertIsNone(q[field], f"{q['id']}.{field}")
            b = q["blocker"]
            self.assertTrue(b["fill_with"] and b["why"], q["id"])
            for field in ("fill_with", "requires", "compare_requires"):
                self.assertLessEqual(set(b[field]), BLOCKER_CODES, q["id"])
            if q["kind"] not in ("angle", "direction", "designation", "count"):
                self.assertIn("#693-scale", b["compare_requires"], q["id"])
            if q["hypothesis"] is not None:
                self.assertIn(q["hypothesis"], register, q["id"])
        for iface in self.contract["interfaces"]:
            self.assertLessEqual(set(iface["hypotheses"]), register, iface["id"])
            self.assertTrue(iface["contributor_request"], iface["id"])

    def test_no_twin_number_sits_in_a_value(self):
        params = ck.Params(TWIN)
        for q in self.q.values():
            ref = q["twin_nominal_not_evidence"]
            if ref is None:
                continue
            self.assertEqual(set(ref) - {"params", "key", "keys", "derive", "value_at_writing", "comparable",
                                         "standing", "also"}, set(), q["id"])
            self.assertTrue(ref["params"].startswith("params/"), q["id"])
            self.assertTrue(ref["standing"], q["id"])
            self.assertTrue(ck.same(params.number(ref), ref["value_at_writing"]), f"{q['id']}: twin number moved")
            self.assertIsNone(q["value"], q["id"])
        # A contract that copies a twin number into a value is refused.
        bad = copy.deepcopy(self.contract)
        q = bad["interfaces"][0]["quantities"][1]
        q.update(value=q["twin_nominal_not_evidence"]["value_at_writing"], uncertainty=0.01,
                 source="catalog/sources/contributed.json")
        with self.assertRaisesRegex(ck.ContractError, "twin's own number"):
            ck.check(bad, self.hypotheses, TWIN)

    def test_today_every_quantity_is_not_checkable_and_the_record_is_current(self):
        record = ck.check(self.contract, self.hypotheses, TWIN)
        s = record["summary"]
        self.assertEqual((s["pass"], s["fail"]), (0, 0))
        self.assertEqual(s["not_checkable"], s["quantities"])
        self.assertEqual(s["quantities"], len(self.q))
        self.assertEqual(s["interfaces"], len(self.contract["interfaces"]))
        self.assertEqual(s["not_checkable_reasons"], {ck.NOT_MEASURED: len(self.q)})
        self.assertEqual(s["twin_numbers_changed_since_writing"], [])
        committed = load("interface-contract-check.json")
        self.assertEqual(committed["summary"], s)
        self.assertEqual(committed["rows"], record["rows"])
        self.assertEqual(committed["contract_sha256"],
                         ck.sha256_bytes((PARAMS / "interface-contract.json").read_bytes()))

    def test_readme_links_the_contract_and_says_nothing_is_measured(self):
        readme = (TWIN / "README.md").read_text()
        n_if, n_q = len(self.contract["interfaces"]), len(self.q)
        n_twin = sum(q["twin_nominal_not_evidence"] is not None for q in self.q.values())
        flat = " ".join(readme.split())
        # assertTrue, not assertIn: a failure should not print the whole README.
        for text in ("(params/interface-contract.json)", "(params/interface-contract-check.json)",
                     "(source/check_interface_contract.py)", f"{n_if} interfaces and {n_q} quantities",
                     f"beside {n_twin} quantities", "Nothing is measured.",
                     "Every value, uncertainty and source is null.", f"Today all {n_q} are not checkable."):
            self.assertTrue(text in flat, f"README lacks {text!r}")


class IndependenceTests(unittest.TestCase):
    def test_the_checker_imports_the_standard_library_only(self):
        tree = ast.parse(CHECKER.read_text())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom):
                imported.add((node.module or "").split(".")[0])
        self.assertLessEqual(imported, {"__future__", "argparse", "hashlib", "json", "math", "sys", "pathlib"})
        producers = {p.stem for p in (TWIN / "source").glob("*.py")} - {CHECKER.stem}
        self.assertFalse(imported & producers)
        source = CHECKER.read_text()
        self.assertNotIn("sys.path", source)
        self.assertNotIn("importlib", source)

    def test_the_checker_runs_in_isolated_mode(self):
        run = subprocess.run([sys.executable, "-I", str(CHECKER), "--help"], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr[-300:])


def synthetic_twin(root: Path) -> Path:
    twin = root / "twin"
    (twin / "params").mkdir(parents=True)
    (twin / "params" / "fits.json").write_text(json.dumps({
        "bore": 10.1,
        "angle": 45.5,
        "axis": [0.0, 0.0, 1.0],
        "rods": [{"name": "a", "base": [0.0, 0.0, 0.0]}, {"name": "b", "base": [3.0, 4.0, 0.0]}],
        "label": "flat",
    }))
    (twin / "hypotheses.json").write_text(json.dumps({"items": [{"id": "H06-spark-plug-threads"}]}))
    return twin


def synthetic_q(qid, kind, key=None, value=None, uncertainty=None, threshold=None, comparable=True,
                source="catalog/sources/contributed-935-head.json", derive=None):
    twin = None
    if key is not None:
        twin = {"params": "params/fits.json", "comparable": comparable, "standing": "synthetic"}
        if derive:
            twin.update(derive=derive, keys=key)
        else:
            twin["key"] = key
    return {
        "id": f"i.{qid}", "kind": kind, "unit": "mm", "datum": None,
        "value": value, "uncertainty": uncertainty, "source": source if value is not None else None,
        "threshold": threshold,
        "blocker": {"fill_with": ["contribution-0019"], "requires": [], "compare_requires": [], "why": "synthetic"},
        "hypothesis": None, "twin_nominal_not_evidence": twin,
    }


def synthetic_contract(qs):
    return {
        "schema": ck.CONTRACT_SCHEMA,
        "contract_id": "SYNTHETIC",
        "revision": "2026-11-22",
        "preconditions": [{"id": "#693-scale", "state": "open"}],
        "blocker_codes": {code: "synthetic" for code in BLOCKER_CODES},
        "interfaces": [{"id": "i", "hypotheses": [], "quantities": qs}],
    }


class SyntheticCheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.twin = synthetic_twin(Path(self.tmp.name))
        self.hyp = json.loads((self.twin / "hypotheses.json").read_text())

    def tearDown(self):
        self.tmp.cleanup()

    def rows(self, qs):
        return {r["id"].split(".", 1)[1]: r for r in ck.check(synthetic_contract(qs), self.hyp, self.twin)["rows"]}

    def test_pass_and_fail_on_a_filled_contract(self):
        rows = self.rows([
            synthetic_q("d_pass", "diameter", ["bore"], 10.0, 0.02, 0.2),
            synthetic_q("d_fail", "diameter", ["bore"], 9.8, 0.02, 0.2),
            synthetic_q("a_pass", "angle", ["angle"], 45.0, 0.1, 1.0),
            synthetic_q("p_pass", "point", ["rods", {"name": "b"}, "base"], [3.0, 4.1, 0.0], 0.05, 0.2),
            synthetic_q("p_fail", "point", ["rods", {"name": "b"}, "base"], [3.0, 4.5, 0.0], 0.05, 0.2),
            synthetic_q("dir_pass", "direction", ["axis"], [0.0, 0.01, -1.0], 0.2, 1.0),
            synthetic_q("dir_fail", "direction", ["axis"], [0.0, 0.1, 1.0], 0.2, 1.0),
            synthetic_q("spacing", "length", [["rods", 0, "base"], ["rods", 1, "base"]], 5.15, 0.02, 0.2,
                        derive="distance"),
            synthetic_q("label_pass", "designation", ["label"], "flat", 0.0),
            synthetic_q("label_fail", "designation", ["label"], "taper", 0.0),
        ])
        want = {"d_pass": "pass", "d_fail": "fail", "a_pass": "pass", "p_pass": "pass", "p_fail": "fail",
                "dir_pass": "pass", "dir_fail": "fail", "spacing": "pass", "label_pass": "pass",
                "label_fail": "fail"}
        self.assertEqual({k: r["status"] for k, r in rows.items()}, want)
        self.assertAlmostEqual(rows["d_fail"]["deviation"], 0.3, places=6)
        self.assertAlmostEqual(rows["p_fail"]["deviation"], 0.5, places=6)
        self.assertAlmostEqual(rows["spacing"]["deviation"], 0.15, places=6)
        self.assertLess(rows["dir_pass"]["deviation"], 1.0)  # the sign of an axis does not count
        self.assertIn("caveat", rows["d_pass"])  # a length waits on #693
        self.assertNotIn("caveat", rows["a_pass"])  # an angle does not

    def test_not_checkable_for_each_missing_piece(self):
        rows = self.rows([
            synthetic_q("null", "diameter", ["bore"]),
            synthetic_q("no_twin", "diameter", None, 10.0, 0.02, 0.2),
            synthetic_q("not_same", "diameter", ["bore"], 10.0, 0.02, 0.2, comparable=False),
            synthetic_q("no_threshold", "diameter", ["bore"], 10.0, 0.02, None),
            synthetic_q("tight", "diameter", ["bore"], 10.0, 0.15, 0.2),
            synthetic_q("tolerance", "tolerance", None, [-0.01, 0.02], 0.005, None),
        ])
        for name, r in rows.items():
            self.assertEqual(r["status"], "not_checkable", name)
        self.assertEqual(rows["null"]["reason"], ck.NOT_MEASURED)
        self.assertEqual(rows["no_twin"]["reason"], "the twin holds no number for this quantity")
        self.assertEqual(rows["not_same"]["reason"], "the twin's number is not the same measurand")
        self.assertEqual(rows["no_threshold"]["reason"], "no acceptance threshold committed")
        self.assertEqual(rows["tight"]["reason"], "the threshold is less than twice the uncertainty")

    def test_contracts_that_cannot_be_checked_are_refused(self):
        cases = {
            "a value without a source": synthetic_q("q", "diameter", ["bore"], 10.0, 0.02, 0.2) | {"source": None},
            "a value without an uncertainty": synthetic_q("q", "diameter", ["bore"], 10.0, None, 0.2),
            "is the twin itself": synthetic_q("q", "diameter", ["bore"], 10.0, 0.02, 0.2,
                                              source="twins/935-cylinder-head-cad-twin/params/feature-fits.json"),
            "twin's own number": synthetic_q("q", "diameter", ["bore"], 10.1, 0.02, 0.2),
            "does not resolve": synthetic_q("q", "diameter", ["missing"], 10.0, 0.02, 0.2),
            "a diameter value is a number": synthetic_q("q", "diameter", ["bore"], "ten", 0.02, 0.2),
            "is not declared": synthetic_q("q", "diameter", ["bore"])
            | {"blocker": {"fill_with": ["a guess"], "requires": [], "compare_requires": [], "why": "x"}},
            "is not in hypotheses.json": synthetic_q("q", "diameter", ["bore"]) | {"hypothesis": "H99-invented"},
            "a source or an uncertainty without a value": synthetic_q("q", "diameter", ["bore"])
            | {"source": "catalog/sources/x.json"},
        }
        for message, q in cases.items():
            with self.subTest(message), self.assertRaisesRegex(ck.ContractError, message):
                ck.check(synthetic_contract([q]), self.hyp, self.twin)

    def test_the_command_line_writes_nothing_for_a_refused_contract(self):
        contract = synthetic_contract([synthetic_q("q", "diameter", ["bore"], 10.0, None, 0.2)])
        path = self.twin / "params" / "interface-contract.json"
        path.write_text(json.dumps(contract))
        out = self.twin / "params" / "check.json"
        args = ["--twin", str(self.twin), "--out", str(out)]
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(ck.main(args), 2)
        self.assertIn("a value without an uncertainty", err.getvalue())
        self.assertFalse(out.exists())
        path.write_text(json.dumps(synthetic_contract([synthetic_q("q", "diameter", ["bore"])])))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ck.main(args), 0)
        record = json.loads(out.read_text())
        self.assertEqual(record["summary"]["not_checkable"], 1)
        self.assertEqual(record["contract"], "params/interface-contract.json")


if __name__ == "__main__":
    unittest.main()
