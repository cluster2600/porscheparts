#!/usr/bin/env python3
"""Verrouille les rendus produit sur la peau F43 issue du scan."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "twins/reference-917-engine/visible-product-policy-f49.json"
OUTER_BUILDER = ROOT / "twins/reference-917-engine/source/build_scan_contour_patch_reconstruction_f43.py"


class VisibleProductPolicyF49Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = json.loads(POLICY.read_text(encoding="utf-8"))

    def test_scan_skin_is_the_only_external_authority(self) -> None:
        authority = self.policy["authority"]
        self.assertEqual(authority["external_skin"], "F43 scan contour patch")
        self.assertEqual(authority["source_contours"], 44)
        self.assertEqual(authority["same_skin_required_for"], ["2V", "4V"])
        self.assertFalse(authority["global_anisotropic_scaling_allowed"])
        self.assertFalse(authority["global_ellipse_or_oval_envelope_allowed"])
        self.assertFalse(authority["synthetic_head_envelope_allowed"])

    def test_current_product_gallery_is_hash_locked_and_excludes_old_lineages(self) -> None:
        forbidden = tuple(self.policy["historical_lineages_forbidden_from_current_product_gallery"])
        self.assertEqual(forbidden, ("f39", "f42"))
        for item in self.policy["current_product_visuals"]:
            relative_path = item["path"]
            self.assertNotIn("/f39", relative_path)
            self.assertNotIn("/f42", relative_path)
            path = ROOT / relative_path
            self.assertTrue(path.is_file())
            self.assertEqual(path.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), item["sha256"])

    def test_round_geometry_cannot_define_the_external_skin(self) -> None:
        round_policy = self.policy["functional_round_geometry"]
        self.assertFalse(round_policy["may_define_external_skin"])
        self.assertIn("cylinder_bore", round_policy["allowed_only_for"])
        self.assertIn("valves", round_policy["allowed_only_for"])
        builder = OUTER_BUILDER.read_text(encoding="utf-8")
        for forbidden_call in ("addEllipse", "addDisk", "addCylinder", "addBox", "addCone"):
            self.assertNotIn(forbidden_call, builder)

    def test_policy_never_implies_release(self) -> None:
        release = self.policy["release_state"]
        self.assertTrue(release["geometry_baseline_only"])
        self.assertFalse(release["manufacturing_authorized"])
        self.assertFalse(release["engine_start_authorized"])


if __name__ == "__main__":
    unittest.main()
