#!/usr/bin/env python3
"""Tests fail-closed des preuves AdditiveFOAM F42.2 executees."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "twins/reference-917-engine/evidence/f42-2-additivefoam-live"
MANIFEST = EVIDENCE / "917-head-f42-2-publication-manifest.json"
RESULTS = [
    EVIDENCE / "917-head-f42-2-results-host-a.json",
    EVIDENCE / "917-head-f42-2-results-host-b.json",
]
PROVENANCE = [
    EVIDENCE / "917-head-f42-2-provenance-host-a.json",
    EVIDENCE / "917-head-f42-2-provenance-host-b.json",
]
COMPARISON = EVIDENCE / "917-head-f42-2-cross-host.json"
PROCESSING_ROOT = ROOT / "twins/reference-917-engine/source"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class F422AdditiveFoamLiveEvidenceTests(unittest.TestCase):
    def test_both_hosts_have_all_runs_and_pass_numerical_screens(self) -> None:
        for path in RESULTS:
            report = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(report["phase"], "F42")
            self.assertEqual(len(report["measurements"]), 33)
            self.assertEqual(
                sum(item["resolution"] == "nominal" for item in report["measurements"]),
                27,
            )
            self.assertTrue(all(item["completed"] for item in report["measurements"]))
            self.assertTrue(all(item["finite"] for item in report["measurements"]))
            self.assertEqual(report["temperature_limit_policy"]["cap_hit_count"], 0)
            self.assertTrue(report["gates"]["temperature_cap_free"])
            self.assertTrue(report["gates"]["resolution_convergence_complete"])
            self.assertTrue(report["gates"]["doe_response_ranking_permitted"])
            self.assertFalse(report["gates"]["metal_print_authorized"])
            self.assertFalse(report["gates"]["engine_start_authorized"])

    def test_cross_host_reproducibility_passes_but_is_not_second_physics(self) -> None:
        report = json.loads(COMPARISON.read_text(encoding="utf-8"))
        self.assertEqual(report["phase"], "F42.2")
        self.assertEqual(report["comparison_count"], 33)
        self.assertTrue(report["case_set_identical"])
        self.assertTrue(report["gates"]["all_33_runs_reproduced_within_tolerance"])
        self.assertTrue(all(item["passes"] for item in report["comparisons"]))
        self.assertFalse(report["gates"]["second_independent_physics_method_completed"])
        self.assertFalse(report["gates"]["metal_print_authorized"])
        self.assertFalse(report["gates"]["engine_start_authorized"])

    def test_path_free_provenance_binds_33_solver_runs(self) -> None:
        labels = set()
        for path in PROVENANCE:
            report = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(report["phase"], "F42.2")
            self.assertEqual(len(report["solver_results"]), 33)
            self.assertTrue(report["gates"]["doe_solver_executed"])
            self.assertTrue(report["privacy"]["absolute_paths_removed"])
            self.assertTrue(report["privacy"]["instance_identifiers_removed"])
            labels.add(report["provenance"]["hardware_label"])
        self.assertEqual(len(labels), 2)

    def test_publication_manifest_binds_artifacts_and_processing_sources(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["phase"], "F42.2")
        for artifact in manifest["artifacts"].values():
            path = EVIDENCE / artifact["file"]
            self.assertTrue(path.is_file())
            self.assertEqual(artifact["sha256"], sha256(path))
        for filename, expected in manifest["processing_sources"].items():
            self.assertEqual(expected, sha256(PROCESSING_ROOT / filename))
        self.assertTrue(manifest["gates"]["all_33_runs_reproduced_within_tolerance"])
        self.assertFalse(manifest["gates"]["contains_private_geometry"])
        self.assertFalse(manifest["gates"]["metal_print_authorized"])

    def test_images_are_nonempty_png_files(self) -> None:
        for name in (
            "917-head-f42-2-results-host-a.png",
            "917-head-f42-2-results-host-b.png",
            "917-head-f42-2-cross-host.png",
        ):
            path = EVIDENCE / name
            self.assertEqual(path.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
            self.assertGreater(path.stat().st_size, 100_000)

    def test_public_text_contains_no_private_runtime_locator(self) -> None:
        for path in EVIDENCE.iterdir():
            if path.suffix not in {".json", ".md"}:
                continue
            text = path.read_text(encoding="utf-8")
            for forbidden in (
                "/workspace/",
                "/private/tmp/",
                "/Users/",
                "ssh1.vast.ai",
                "ssh2.vast.ai",
                "49794326",
                "49799404",
                "49805287",
            ):
                self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
