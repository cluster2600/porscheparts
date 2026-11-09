"""Portable checks of a held source rebind, with no solver/controller launch."""
import ast
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "twins/962-cylinder-head-f0/source/controller_rebind_20261107/prepare.py"
spec = importlib.util.spec_from_file_location("held_owner_rebind", SOURCE)
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


class ControllerRebindTests(unittest.TestCase):
    def test_rejects_changed_source_before_rebinding(self):
        raw = b"answer = 1\n"
        with self.assertRaisesRegex(ValueError, "hash"):
            prepare.rebind(raw + b"# changed\n", prepare.digest(raw), [("1", "2")])

    def test_rejects_ambiguous_and_preexisting_replacements(self):
        for raw in (b"a = 1\nb = 1\n", b"a = 1\nb = 2\n"):
            with self.subTest(raw=raw), self.assertRaisesRegex(ValueError, "Nonunique"):
                prepare.rebind(raw, prepare.digest(raw), [("1", "2")])

    def test_held_generation_preserves_lifecycle_and_deadlines(self):
        files = prepare.render()
        self.assertEqual(set(files), {"run_owner_once.py", "run_fixed_adapter.py",
            "stopped_exec_wrapper.py", "check_toy_sessions.py", "source-choice.json", "bindings.json"})
        published = ROOT / "twins/962-cylinder-head-f0/derived/engineering/controller-rebind-20261107"
        for name in ("bindings.json", "source-choice.json"):
            self.assertEqual((published / name).read_bytes(), files[name])
        report = json.loads(files["bindings.json"])
        choice = json.loads(files["source-choice.json"])
        for record in (report, choice):
            for flag in ("runtime_execution_authorized", "independent_source_review_complete",
                         "engineering_phase_accepted", "manufacturing_authorized"):
                self.assertIs(record[flag], False)
        self.assertEqual(choice["normal_TERM_KILL_whole_seconds"], [40, 48, 56, 60])
        self.assertNotIn("admission.json", files)
        old = ast.parse(prepare.SOURCES["run_owner_once.py"][0].read_text())
        new = ast.parse(files["run_owner_once.py"])
        for name in ("main", "sample", "exit_events", "limits", "inclusive_bytes"):
            before = next(n for n in old.body if isinstance(n, ast.FunctionDef) and n.name == name)
            after = next(n for n in new.body if isinstance(n, ast.FunctionDef) and n.name == name)
            self.assertEqual(ast.dump(before), ast.dump(after), name)
        assignments = {n.targets[0].id: n.value for n in new.body
                       if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)}
        expected = {"normal_seconds": 40, "TERM_absolute_seconds": 48,
                    "KILL_reap_absolute_seconds": 56, "whole_seconds": 60,
                    "TERM_grace_seconds": 8, "KILL_grace_seconds": 8,
                    "RSS_query_seconds": 5, "thread_environment": 1, "retries": 0}
        controls = {k.arg: k.value for k in assignments["CONTROLS"].keywords}
        for name, value in expected.items():
            self.assertEqual(ast.literal_eval(controls[name]), value)
        transport = ast.parse(files["check_toy_sessions.py"])
        argv = next(n.value for n in transport.body if isinstance(n, ast.Assign)
                    and isinstance(n.targets[0], ast.Name) and n.targets[0].id == "ARGV")
        self.assertEqual(ast.literal_eval(argv), [str(prepare.SOLVER), "-in", "-smt2"])
        for name, pin in report["outputs"].items():
            self.assertEqual(pin, {"sha256": prepare.digest(files[name]), "bytes": len(files[name])})
