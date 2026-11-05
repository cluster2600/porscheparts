"""Independent spatial redundancies catch contact-state and projection errors."""

import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "twins/964-chassis/owner-frame-data-20261105"
SPEC = importlib.util.spec_from_file_location("owner_frame_data", PACKET / "build.py")
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)


class FrameDataTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((PACKET / "source-data.json").read_text())

    def test_printed_spatial_redundancies_and_frozen_outputs(self):
        result, _ = BUILD.audit(self.data)
        self.assertEqual(len(result["checks"]), 18)
        for name, content in BUILD.products(self.data).items():
            self.assertEqual((PACKET / name).read_text(), content)

    def test_mixing_bolt_and_removed_contact_fails(self):
        self.data["ch"]["states"]["parts_on"]["points"]["9"]["height"] = 219
        with self.assertRaisesRegex(ValueError, "spatial check"):
            BUILD.audit(self.data)

    def test_direct_length_cannot_replace_longitudinal_projection(self):
        self.data["mi"]["longitudinal_projections"][0]["printed_value"] = 1232
        with self.assertRaisesRegex(ValueError, "spatial check"):
            BUILD.audit(self.data)

    def test_unknown_widths_and_registration_stay_unknown(self):
        result, rows = BUILD.audit(self.data)
        for point in "BC":
            self.assertTrue(all(r["half_width"] is None for r in rows if r["family"] == "Mi" and r["point"] == point))
        motor = next(r for r in rows if r["family"] == "Mi" and r["point"] == "I")
        self.assertEqual(motor["half_width"], 320)
        self.assertIsNone(result["donor_registration"])
        self.assertFalse(result["functional_geometry_admitted"])
        self.assertFalse(result["manufacturing_authorized"])

    def test_transverse_offset_is_required(self):
        _, rows = BUILD.audit(self.data)
        a = next(r for r in rows if r["family"] == "Mi" and r["point"] == "A")
        b = copy.copy(a)
        b["half_width"] = None
        with self.assertRaisesRegex(ValueError, "Unknown transverse"):
            BUILD.distance(a, b, False)

    def test_catalogue_coordinate_entries_match_the_checked_network(self):
        record = json.loads((ROOT / "catalog/measurements/MEAS-OWNER-964-FRAME-20261105.json").read_text())
        _, rows = BUILD.audit(self.data)
        entries = {v["value_id"]: v for v in record["declared_values"]}
        for row in rows:
            if row["family"] == "CH":
                state = "ON" if row["state"] == "parts_on" else "OFF"
                identifier = f'MNL-FD964-CH-{state}-{row["point"]}'
                xkey = "x_relative_to_point5"
            else:
                contact = row["state"].upper().split("_")[0]
                identifier = f'MNL-FD964-MI-{row["point"]}-{contact}'
                xkey = "x_relative_to_F"
            values = entries[identifier]["details"]["components"]
            self.assertEqual(values, {xkey: row["x"], "half_width": row["half_width"], "height": row["height"]})


if __name__ == "__main__":
    unittest.main()
