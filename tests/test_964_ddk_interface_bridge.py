import copy
import csv
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "twins/964-chassis/ddk-interface-bridge-20261104"
SPEC = importlib.util.spec_from_file_location("ddk_bridge", FOLDER / "build.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DDKInterfaceBridgeTests(unittest.TestCase):
    def setUp(self):
        self.inputs = MODULE.read_inputs()

    def test_no_forum_dimension_becomes_an_anchor_or_tunnel(self):
        result = MODULE.build(self.inputs)
        self.assertEqual(result["coverage"]["selected_leads"], 15)
        self.assertEqual(result["coverage"]["distinct_original_posts"], 9)
        self.assertEqual(result["coverage"]["manual_point_identities"], 18)
        self.assertEqual(result["coverage"]["scan_search_regions"], 7)
        rows = list(csv.DictReader(io.StringIO(MODULE.crosswalk_csv(result))))
        self.assertEqual(len(rows), 19)
        self.assertEqual([float(r["span_mm"]) for r in rows if r["point"] == "P14"], [601.5, 616.6])
        for row in rows:
            self.assertEqual(row["exact_ddk_feature_match"], "false")
            self.assertTrue(all(row[k] == "" for k in ("x_mm", "y_mm", "z_mm", "axis", "mating_face")))
        self.assertTrue(all(not v for v in result["release_flags"].values()))
        self.assertIsNone(result["mass_policy"]["measured_vehicle_mass_kg"])
        self.assertEqual(result["mass_policy"]["accepted_component_masses"], [])

    def test_wrong_variant_and_missing_datum_stay_excluded(self):
        groups = {}
        for row in self.inputs["leads"]["leads"]:
            groups.setdefault(row["source_post"], []).append(row)
        for pid in ("58292", "568672", "216488"):
            self.assertEqual(groups[pid][0]["disposition"], "incompatible_context")
        self.assertEqual(len(groups["562973"]), 3)
        self.assertTrue(all(r["disposition"] == "unidentified_variant_and_datum" for r in groups["562973"]))
        self.assertEqual(len(groups["326009"]), 4)
        self.assertTrue(all(not r["accepted_as_load_input"] for r in groups["326009"]))

    def test_rejects_promotion_unknown_mapping_and_duplicate_claim(self):
        mutations = [
            lambda d: d["leads"]["leads"][0].update(accepted_as_cad_constraint=True),
            lambda d: d["leads"]["leads"][0].update(accepted_as_load_input=True),
            lambda d: d["leads"]["leads"][0].update(context_is_feature_identification=True),
            lambda d: d["leads"]["leads"][0].update(candidate_point_context=["P8"]),
            lambda d: d["leads"]["leads"][0].update(scan_search_context=["TunnelInterior"]),
            lambda d: d["leads"]["leads"][0].update(disposition="qualified"),
            lambda d: d["leads"]["leads"][0].update(source_post="missing"),
            lambda d: d["leads"]["leads"].append(copy.deepcopy(d["leads"]["leads"][0])),
            lambda d: d["leads"]["leads"][0]["facts"].update(author="must-not-publish"),
            lambda d: d["leads"]["leads"][0]["facts"].update(value=float("nan")),
            lambda d: d["interfaces"]["donor"].update(gearbox="G50_assumed"),
            lambda d: d["interfaces"]["points"]["P12"].update(xyz_mm=[1, 2, 3]),
            lambda d: d["boundaries"].update(physical_segmentation_validated=True),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index):
                data = copy.deepcopy(self.inputs)
                mutate(data)
                with self.assertRaises(ValueError):
                    MODULE.build(data)

    def test_private_dataset_must_match_before_comparing_facts(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "wrong.json"
            path.write_text('{"measurements": []}')
            with self.assertRaisesRegex(ValueError, "differs from the reviewed revision"):
                MODULE.verify_dataset(self.inputs["leads"], path)

    def test_outputs_and_all_source_hashes_reproduce(self):
        for name, content in MODULE.outputs().items():
            self.assertEqual((FOLDER / name).read_text(), content)
        report = json.loads((FOLDER / "bridge.json").read_text())
        for path, expected in report["input_sha256"].items():
            self.assertEqual(MODULE.digest(ROOT / path), expected)


if __name__ == "__main__":
    unittest.main()
