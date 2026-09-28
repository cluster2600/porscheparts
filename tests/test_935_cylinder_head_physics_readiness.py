import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "twins/reference-935-cylinder-head/source/build_physics_readiness.py"
CONTRACT = ROOT / "twins/reference-935-cylinder-head/reengineering-contract.json"
INPUTS = ROOT / "twins/reference-935-cylinder-head/engineering-inputs.template.json"


def load_module():
    spec = importlib.util.spec_from_file_location("head_physics_readiness", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


class CylinderHeadPhysicsReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.inputs = json.loads(INPUTS.read_text(encoding="utf-8"))

    def build_pipeline_fixture(self, root: Path) -> Path:
        pipeline = root / "pipeline"
        write_json(
            pipeline / "reports/mesh-preparation.json",
            {
                "source_sha256": self.contract["asset"]["source_sha256"],
                "topology": {
                    "head_with_studs": {"boundary_edges": 99876, "watertight": False}
                },
            },
        )
        write_json(pipeline / "cad/interface-proxy.json", {"status": "F1_interface_proxy"})
        write_json(
            pipeline / "cad/valves/valve-variants-f1.json",
            {"status": "F1_hypothesis_only"},
        )
        write_json(
            pipeline / "cfd/cfd-stubs.json",
            {
                "domains": {
                    "low_B": {
                        "status": "provisional_cfd_stub",
                        "surface": {"watertight": True},
                        "gmsh": {"status": "generated"},
                    },
                    "high_B": {
                        "status": "provisional_cfd_stub",
                        "surface": {"watertight": True},
                        "gmsh": {"status": "generated"},
                    },
                }
            },
        )
        return pipeline

    def evidence(self, root: Path, name: str, content: str = "evidence") -> dict:
        path = root / name
        path.write_text(content, encoding="utf-8")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        return {"path": str(path), "sha256": digest}

    def test_empty_engineering_inputs_fail_closed_at_f0(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pipeline = self.build_pipeline_fixture(root)
            input_path = root / "engineering-inputs.json"
            write_json(input_path, self.inputs)
            report = self.module.evaluate(pipeline, CONTRACT, input_path)

        self.assertEqual(report["report_status"], "passed")
        self.assertEqual(report["highest_verified_level"], "F0_reference")
        self.assertEqual(report["generated_geometry_level"], "F1_hypothesis_artifacts")
        self.assertFalse(report["manufacturing_release"]["authorized"])
        self.assertTrue(
            all(item["status"] == "blocked" for item in report["physics_model_readiness"])
        )

    def test_three_consistent_physical_controls_validate_scale_only(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pipeline = self.build_pipeline_fixture(root)
            inputs = json.loads(json.dumps(self.inputs))
            measurement = self.evidence(root, "measurement.json")
            inputs["scale_calibration"]["mm_per_obj_unit"] = 1.0
            for control in inputs["scale_calibration"]["controls"]:
                control["physical_mm"] = control["scan_obj_units"]
                control["uncertainty_mm"] = 0.05
                control["evidence"] = measurement
            input_path = root / "engineering-inputs.json"
            write_json(input_path, inputs)
            report = self.module.evaluate(pipeline, CONTRACT, input_path)

        gates = {item["id"]: item for item in report["gates"]}
        self.assertEqual(gates["scale_calibration"]["status"], "passed")
        self.assertEqual(report["highest_verified_level"], "F0_reference")
        self.assertFalse(report["manufacturing_release"]["authorized"])

    def test_four_valve_branch_requires_independent_geometry(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            evidence = self.evidence(root, "geometry.step")
            data = json.loads(json.dumps(self.inputs["architecture_comparison"]))
            for key in ("parametric_cad", "chamber_and_port_geometry", "valve_layout_and_lift"):
                data["baseline_2v"][key] = evidence
            ready, findings = self.module.architecture_ready(data, root)

        self.assertFalse(ready)
        self.assertEqual(findings["baseline_2v"]["observed_valve_count"], 2)
        self.assertIn("missing", findings["concept_4v"]["evidence"]["parametric_cad"])

    def test_contract_keeps_four_valve_and_supplier_components_explicit(self):
        architectures = {
            item["id"]: item for item in self.contract["architecture_variants"]
        }
        strategy = self.contract["component_strategy"]

        self.assertEqual(architectures["2v_scan_baseline"]["valves_per_cylinder"], 2)
        self.assertEqual(architectures["4v_concept"]["valves_per_cylinder"], 4)
        self.assertIn("not_lpbf", strategy["intake_valve"]["manufacturing"])
        self.assertIn("not_lpbf", strategy["exhaust_valve"]["manufacturing"])
        self.assertIn("not_additive", strategy["valve_spring"]["manufacturing"])

    def test_tampered_evidence_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            evidence = self.evidence(root, "measurement.json", "first")
            (root / "measurement.json").write_text("changed", encoding="utf-8")
            ready, finding = self.module.evidence_ready(evidence, root)

        self.assertFalse(ready)
        self.assertIn("mismatch", finding)


if __name__ == "__main__":
    unittest.main()
