"""Independent geometry/kinematic controls for the explicit hypothesis study."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "twins/964-chassis/assumed-cell-20261106"


def module(name):
    spec = importlib.util.spec_from_file_location(name, STUDY / (name + ".py"))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


builder, auditor, usd = module("build"), module("geometry_audit"), module("export_usd")


class AssumedCellTests(unittest.TestCase):
    def setUp(self):
        self.parameters = json.loads((STUDY / "assumptions.json").read_text())

    def test_exact_union_has_independent_overlap_denominator(self):
        boxes = [{"min_mm": [0, 0, 0], "max_mm": [2, 2, 2]},
                 {"min_mm": [1, 1, 1], "max_mm": [3, 3, 3]}]
        self.assertEqual(auditor.union_volume(boxes), 8 + 8 - 1)
        self.assertEqual(auditor.union_volume(boxes + boxes), 15)

    def test_exact_union_counts_touching_boxes_once(self):
        boxes = [{"min_mm": [0, 0, 0], "max_mm": [2, 2, 2]},
                 {"min_mm": [2, 0, 0], "max_mm": [4, 2, 2]}]
        self.assertEqual(auditor.union_volume(boxes), 16)
        self.assertFalse(auditor.overlap(*boxes))

    def test_USD_boundary_preserves_cube_and_shared_face_union_volume(self):
        a = {"min_mm": [0, 0, 0], "max_mm": [2, 2, 2]}
        b = {"min_mm": [2, 0, 0], "max_mm": [4, 2, 2]}
        points, faces, volume = usd.boundary([a])
        self.assertEqual((len(points), len(faces), volume), (8, 6, 8))
        self.assertEqual(usd.boundary([a, b])[2], 16)

    def test_continuous_pull_finds_obstacle_between_sample_frames(self):
        core = {"min_mm": [0, 0, 0], "max_mm": [1, 1, 1]}
        wall = {"name": "thin_wall", "min_mm": [3, 0, 0], "max_mm": [3.01, 1, 1]}
        result = auditor.pull(core, [wall], 0, 1, 100)
        self.assertFalse(result["collision_free"])
        self.assertEqual(result["first_collision_mm"], 2)
        self.assertTrue(auditor.pull(core, [wall], 0, -1, 100)["collision_free"])

    def test_all_variants_preserve_admission_scope_and_connected_geometry(self):
        for variant in self.parameters["variants"]:
            with self.subTest(variant=variant):
                model = builder.build(self.parameters, variant)
                self.assertIsNone(model["donor_transform"])
                self.assertFalse(model["physical_interfaces_admitted"])
                self.assertEqual(model["status"], "assumed")
                self.assertTrue(auditor.audit(model)["connected_plate_union"])

    def test_tunnel_is_an_actual_through_reservation(self):
        result = auditor.audit(builder.build(self.parameters))
        trial = next(x for x in result["straight_pull_trials"] if x["core"] == "tunnel")
        clear = {x["direction"] for x in trial["directions"] if x["collision_free"]}
        self.assertEqual(clear, {"-X", "+X"})

    def test_closed_sill_cores_are_trapped(self):
        result = auditor.audit(builder.build(self.parameters))
        sills = [x for x in result["straight_pull_trials"] if "sill" in x["core"]]
        self.assertEqual(len(sills), 2)
        self.assertTrue(all(not x["any_axis_aligned_rigid_pull"] for x in sills))

    def test_wrong_physical_plate_thickness_rejected(self):
        model = builder.build(self.parameters)
        model["plate_boxes"][0]["max_mm"][2] += 1
        with self.assertRaises(AssertionError):
            auditor.audit(model)

    def test_disconnected_plate_rejected(self):
        model = deepcopy(builder.build(self.parameters))
        model["panels"][0]["at_mm"] += 10000
        for key in ("min_mm", "max_mm"):
            model["plate_boxes"][0][key][2] += 10000
        with self.assertRaisesRegex(AssertionError, "Disconnected"):
            auditor.audit(model)

    def test_invalid_tunnel_and_overlapping_crossmembers_rejected(self):
        for change in ({"tunnel_width": 1500}, {"seat_crossmember_x": [700, 700]}):
            parameters = deepcopy(self.parameters)
            parameters["dimensions_mm"].update(change)
            with self.subTest(change=change), self.assertRaises(AssertionError):
                builder.build(parameters)


if __name__ == "__main__":
    unittest.main()
