import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TWIN = ROOT / "catalog/twins/twin-993-m64-60-piston-gallery-f0.json"
PART = ROOT / "catalog/parts/993-eng-piston-cp1-gallery-f0-0001.json"
REPORT = ROOT / "parts/993-eng-piston-cp1-gallery-f0-0001/evidence/engineering-screen.json"
MATERIAL_PROMPT = ROOT / "twins/993-m64-60-piston-gallery-f0/simready/material-prompt.txt"
PHYSICS_PROMPT = ROOT / "twins/993-m64-60-piston-gallery-f0/simready/physics-prompt.txt"


class PistonDigitalTwinF0Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.twin = json.loads(TWIN.read_text(encoding="utf-8"))
        self.part = json.loads(PART.read_text(encoding="utf-8"))
        self.report = json.loads(REPORT.read_text(encoding="utf-8"))

    def test_twin_uses_the_editable_piston_master(self) -> None:
        self.assertEqual(self.twin["fidelity"], "F1_envelope")
        self.assertEqual(self.twin["geometry"]["master_format"], "build123d")
        self.assertEqual(
            self.twin["geometry"]["master_file"],
            self.part["geometry"]["master_file"],
        )
        self.assertEqual(
            self.twin["components"][0]["geometry_file"],
            self.part["geometry"]["derived_files"][0],
        )

    def test_all_required_piston_interfaces_fail_closed(self) -> None:
        interfaces = {item["interface_id"]: item for item in self.twin["interfaces"]}
        self.assertEqual(
            set(interfaces),
            {
                "IF_PISTON_CYLINDER_RUNNING_CLEARANCE",
                "IF_RING_PACK_AND_GROOVES",
                "IF_PIN_BOSS_AND_ROD_SMALL_END",
                "IF_CROWN_CHAMBER_AND_VALVES",
                "IF_OIL_JET_AND_CLOSED_GALLERY",
            },
        )
        self.assertTrue(all(item["status"] == "missing_data" for item in interfaces.values()))
        self.assertTrue(all(item["required_measurements"] for item in interfaces.values()))

    def test_math_evidence_is_linked_without_overstating_fidelity(self) -> None:
        self.assertEqual(self.twin["validation"]["status"], "concept")
        self.assertIn(
            "parts/993-eng-piston-cp1-gallery-f0-0001/evidence/engineering-screen.json",
            self.twin["validation"]["evidence"],
        )
        self.assertGreaterEqual(len(self.report["equations"]), 12)
        self.assertFalse(self.report["manufacturing_authorized"])
        self.assertFalse(self.report["engine_operation_authorized"])
        self.assertFalse(self.report["release_authorized"])

    def test_simready_prompts_preserve_the_evidence_boundary(self) -> None:
        material = MATERIAL_PROMPT.read_text(encoding="utf-8")
        physics = PHYSICS_PROMPT.read_text(encoding="utf-8")
        self.assertIn("Aheadd CP1", material)
        self.assertIn("not Porsche or MAHLE production geometry", material)
        self.assertIn("0.681318 kg", physics)
        self.assertIn("Do not author joints", physics)
        for prompt in (material, physics):
            self.assertLess(len(prompt.encode("utf-8")), 20_000)
            self.assertNotRegex(prompt.lower(), r"(api[_-]?key|access[_-]?token|password|secret)\s*[:=]")
            self.assertIn("unauthorized", prompt)


if __name__ == "__main__":
    unittest.main()
