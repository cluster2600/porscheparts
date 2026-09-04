#!/usr/bin/env python3
"""Tests du manifeste public et sans chemins privés F42.2."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "twins/reference-917-engine/source/sanitize_additivefoam_f42_run.py"


def load_module():
    spec = importlib.util.spec_from_file_location("sanitize_additivefoam_f42_run", SOURCE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class F42LpbfSanitizationTests(unittest.TestCase):
    def test_private_paths_are_removed_but_hashes_are_preserved(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            results = Path(directory) / "results.json"
            results.write_text('{"phase":"F42"}\n', encoding="utf-8")
            manifest = {
                "generated_at": "2026-09-04T00:00:00Z",
                "specification": {"path": "/workspace/private/spec.json", "sha256": "a" * 64},
                "configured_cases": [{"case_id": "P380", "case_path": "/workspace/private/case"}],
                "solver_results": {
                    "P380:nominal": {
                        "completed": True,
                        "fatal_error": False,
                        "return_code": 0,
                        "run_log": "/workspace/private/run.log",
                        "run_log_sha256": "b" * 64,
                        "layer_log_checks": [
                            {
                                "path": "/workspace/private/layer.log",
                                "sha256": "c" * 64,
                                "solver_end_marker": True,
                            }
                        ],
                    }
                },
            }
            payload = module.sanitize(manifest, results, {"hardware_label": "host"})
            serialized = json.dumps(payload, sort_keys=True)
            self.assertNotIn("/workspace", serialized)
            self.assertNotIn("case_path", serialized)
            self.assertEqual(payload["specification_sha256"], "a" * 64)
            self.assertEqual(
                payload["solver_results"]["P380:nominal"]["run_log_sha256"],
                "b" * 64,
            )
            self.assertTrue(payload["privacy"]["absolute_paths_removed"])


if __name__ == "__main__":
    unittest.main()
