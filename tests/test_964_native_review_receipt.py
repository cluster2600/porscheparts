"""Retained native media must match the receipt without implying acceptance."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "twins/964-chassis/monocoque/omniverse/native-review-20261029"


class NativeReviewReceiptTests(unittest.TestCase):
    def test_retained_media_and_observations_match_hashes(self):
        session = json.loads((REVIEW / "session.json").read_text())
        for name, expected in session["files_sha256"].items():
            with self.subTest(path=name):
                self.assertEqual(hashlib.sha256((REVIEW / name).read_bytes()).hexdigest(), expected)
        capture = json.loads((REVIEW / "rtx/capture.json").read_text())
        for name, expected in capture["media_sha256"].items():
            self.assertEqual(hashlib.sha256((REVIEW / "rtx" / name).read_bytes()).hexdigest(), expected)

    def test_native_execution_does_not_claim_finished_review(self):
        session = json.loads((REVIEW / "session.json").read_text())
        self.assertTrue(session["qualification"]["rtx_execution_verified"])
        for field, value in session["qualification"].items():
            if field != "rtx_execution_verified":
                self.assertIs(value, False, field)
        self.assertTrue(session["guard"]["provider_absence_verified"])
        self.assertFalse(session["kit"]["save_reopen_verified"])
        self.assertFalse(session["kit"]["whole_body_viewport_verified"])
        self.assertFalse(session["authorization"]["final_invoice_obtained"])
        probe = json.loads((REVIEW / "video-probe.json").read_text())["streams"][0]
        self.assertEqual(probe["nb_read_frames"], "120")
        self.assertEqual(probe["avg_frame_rate"], "24/1")


if __name__ == "__main__":
    unittest.main()
