"""Prepared source assertions only; no prepared module, solver or assessor import."""

import ast
import hashlib
import json
from pathlib import Path
from unittest import TestCase, main

CASE = Path(__file__).resolve().parent
ENGINEERING = CASE.parent
DONOR = ENGINEERING / "cp1-assumed-thermal-birth-prep-001"
MAC = ENGINEERING / "cp1-assumed-thermal-birth-linear-macos-prep-001"
MAC_DONOR = ENGINEERING / "cp1-assumed-thermal-birth-macos-prep-001"


class SourceGuards(TestCase):
    def test_single_solver_keyword_and_exact_assessor_card_time_level(self):
        old = (DONOR / "thermal-birth.i").read_bytes()
        new = (CASE / "thermal-birth.i").read_bytes()
        self.assertEqual(hashlib.sha256(old).hexdigest(),
                         "62527f4e88d9cc55e506cc11c97c48de5ea56e2fd7218231143fc3aa88e92b20")
        self.assertEqual(old.count(b"solve_type = NEWTON"), 1)
        self.assertEqual(new.count(b"solve_type = LINEAR"), 1)
        self.assertEqual(new.replace(b"solve_type = LINEAR", b"solve_type = NEWTON"), old)
        expected = {
            "card.json": "4e07cbb997c831bac2c0abd43092148c5518b6c7aa04d7b3d287779f9e700986",
            "assess.py": "0548fcbf6eba737aaaf816abbfbfd0511b5b8fb266aa10c34a1f5817eef0e338",
            "time-level.i": "460a3332eac1ec0eddd1884657d2b8b0cdd96bd49443180d00651e44fb76a09a",
        }
        for name, digest in expected.items():
            with self.subTest(name=name):
                body = (CASE / name).read_bytes()
                self.assertEqual(body, (DONOR / name).read_bytes())
                self.assertEqual(hashlib.sha256(body).hexdigest(), digest)

    def test_reference_only_changes_deck_digest_and_solver_scope(self):
        old = json.loads((DONOR / "case-contract.json").read_text())
        new = json.loads((CASE / "case-contract.json").read_text())
        self.assertEqual(new["input_sha256"], {
            "thermal-birth.i": hashlib.sha256((CASE / "thermal-birth.i").read_bytes()).hexdigest()})
        self.assertTrue(new["scope"].startswith(old["scope"]))
        self.assertIn("LINEAR bypasses the original nonlinear convergence test", new["scope"])
        restored = json.loads(json.dumps(new))
        restored["input_sha256"] = old["input_sha256"]
        restored["scope"] = old["scope"]
        self.assertEqual(restored, old)
        self.assertEqual(new["selected_level_only"], 2)
        self.assertEqual(new["card"], json.loads((CASE / "card.json").read_text()))
        self.assertEqual(new["card"]["predeclared_tolerances"], old["card"]["predeclared_tolerances"])
        for name in ("native_execution_authorized", "head_execution_authorized", "manufacturing_authorized"):
            self.assertIs(new[name], False)
        for name in ("held-preparation.json",):
            held = json.loads((CASE / name).read_text())
            self.assertIs(held["native_execution_authorized"], False)
            self.assertIsNone(held["actual_contract"])
        mac = json.loads((MAC / "held-preparation.json").read_text())
        self.assertIs(mac["native_launch_authorized"], False)
        self.assertIs(mac["coupon_solve_authorized"], False)
        self.assertIsNone(mac["actual_contract"])

    def test_only_mac_case_pointer_and_mock_source_hash_change(self):
        old = (MAC_DONOR / "run_mac.py").read_text()
        new = (MAC / "run_mac.py").read_text()
        a = 'CASE = ENGINEERING / "cp1-assumed-thermal-birth-prep-001"'
        b = 'CASE = ENGINEERING / "cp1-assumed-thermal-birth-linear-prep-001"'
        self.assertEqual((old.count(a), new.count(b)), (1, 1))
        self.assertEqual(new.replace(b, a), old)
        trees = [ast.parse(x) for x in (old, new)]
        funcs = [{n.name: ast.dump(n, include_attributes=False) for n in t.body
                  if isinstance(n, ast.FunctionDef)} for t in trees]
        self.assertEqual(len(funcs[0]), 9)
        self.assertEqual(funcs[0], funcs[1])
        assignments = {n.targets[0].id: n.value for n in trees[1].body
                       if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)}
        self.assertEqual(ast.literal_eval(assignments["ENVIRONMENT"]), {
            "PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C", "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1", "VECLIB_MAXIMUM_THREADS": "1", "FI_PROVIDER": "tcp"})
        old_guard = (MAC_DONOR / "selfcheck.py").read_text()
        new_guard = (MAC / "selfcheck.py").read_text()
        old_sha = hashlib.sha256(old.encode()).hexdigest()
        new_sha = hashlib.sha256(new.encode()).hexdigest()
        self.assertEqual(new_guard.replace(new_sha, old_sha), old_guard)
        guard_trees = [ast.parse(x) for x in (old_guard, new_guard)]
        classes = [{n.name: ast.dump(n, include_attributes=False) for n in t.body
                    if isinstance(n, ast.ClassDef)} for t in guard_trees]
        self.assertEqual(classes[0], classes[1])
        held = json.loads((MAC / "held-preparation.json").read_text())
        old_held = json.loads((MAC_DONOR / "held-preparation.json").read_text())
        for key in ("coupon_resources", "runtime_sha256s", "runtime_symlinks"):
            self.assertEqual(held[key], old_held[key])


if __name__ == "__main__":
    main()
