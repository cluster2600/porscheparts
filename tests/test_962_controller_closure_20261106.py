"""Portable refusal checks plus independent saved macOS probe review."""
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "twins/962-cylinder-head-f0/source/controller_closure_20261106/probe_owned_groups.py"
DATA = ROOT / "twins/962-cylinder-head-f0/derived/engineering/controller-closure-20261106"
spec = importlib.util.spec_from_file_location("owned_group_probe", SOURCE)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class ControllerClosureTests(unittest.TestCase):
    def test_terminal_handshake_never_signals_reaped_pid(self):
        with patch.object(probe.os, "fork", return_value=12345), patch.object(
            probe, "reap", return_value=0
        ), patch.object(probe.os, "kill") as kill, patch.object(probe.os, "killpg") as killpg:
            result = probe.trial("already-exited")
        self.assertTrue(result["reaped"])
        self.assertIn("error", result)
        kill.assert_not_called()
        killpg.assert_not_called()

    def test_lost_child_relationship_never_signals_numeric_pid(self):
        with patch.object(probe.os, "fork", return_value=12345), patch.object(
            probe, "reap", side_effect=ChildProcessError("ownership lost")
        ), patch.object(probe.os, "kill") as kill, patch.object(probe.os, "killpg") as killpg:
            result = probe.trial("already-exited")
        self.assertTrue(result["ownership_lost"])
        self.assertFalse(result["reaped"])
        kill.assert_not_called()
        killpg.assert_not_called()

    def test_saved_results_bind_source_and_do_not_qualify_controller(self):
        result = json.loads((DATA / "probe002.json").read_text())
        self.assertEqual(result["source_sha256"], hashlib.sha256(SOURCE.read_bytes()).hexdigest())
        self.assertFalse(result["controller_qualified"])
        self.assertFalse(result["engineering_phase_accepted"])
        self.assertFalse(result["manufacturing_authorized"])
        self.assertEqual([r["mode"] for r in result["results"]],
                         ["already-exited", "live-term", "ignore-term"])
        self.assertEqual([[s["errno"] for s in r["signals"]] for r in result["results"]],
                         [[1, 1], [None, 1], [None, None]])
        self.assertEqual([r["returncode"] for r in result["results"]], [0, -15, -9])
        for r in result["results"]:
            self.assertTrue(r["reaped"])
            self.assertTrue(r["group_absent"])
            self.assertTrue(r["note_exit"])
            self.assertNotIn("error", r)
            self.assertNotIn("cleanup_error", r)
            self.assertEqual(len(set(r["certificate"].values())), 1)

    def test_failed_first_attempt_is_retained_as_failure(self):
        result = json.loads((DATA / "probe001.json").read_text())
        self.assertIn("AttributeError", result["results"][0]["error"])
        self.assertTrue(result["results"][0]["reaped"])
        self.assertIsNone(result["results"][0]["group_absent"])
        self.assertFalse(result["controller_qualified"])
