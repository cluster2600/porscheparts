import copy
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


sys.dont_write_bytecode = True


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "benchmarks/openfoam-poiseuille-f25"
CONTRACT_PATH = BENCHMARK / "benchmark-contract-f25.json"
GENERATOR_PATH = BENCHMARK / "generate_cases.py"
ANALYZER_PATH = BENCHMARK / "analyze_results.py"
RUNNER_PATH = BENCHMARK / "run_local.sh"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class OpenFOAMPoiseuilleF25Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.generator = load_module("openfoam_poiseuille_f25_generator", GENERATOR_PATH)
        cls.analyzer = load_module("openfoam_poiseuille_f25_analyzer", ANALYZER_PATH)
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    def synthetic_repeat_reports(self):
        mesh_reports = []
        error_specs = (
            ("coarse", 0.0025, 4e-4, 8e-4),
            ("medium", 0.00125, 1e-4, 2e-4),
            ("fine", 0.000625, 2.5e-5, 5e-5),
        )
        expected_by_id = {mesh["id"]: mesh for mesh in self.contract["meshes"]}
        for mesh_id, spacing, l2_error, linf_error in error_specs:
            expected = expected_by_id[mesh_id]
            total = expected["cells_x"] * expected["cells_y"] * expected["cells_z"]
            mesh_reports.append(
                {
                    "mesh_id": mesh_id,
                    "cells": {
                        "x": expected["cells_x"],
                        "y": expected["cells_y"],
                        "z": expected["cells_z"],
                        "total": total,
                    },
                    "mesh_spacing_y_m": spacing,
                    "mesh_check": {
                        "passed": True,
                        "cell_count_matches": True,
                        "expected_cells": total,
                        "actual_cells": total,
                    },
                    "solver": {
                        "completed": True,
                        "openfoam_13_observed": True,
                        "simplefoam_delegation_observed": True,
                        "last_linear_residuals": {
                            "Ux": {"initial": 1.0, "final": 1e-9, "iterations": 2},
                            "Uy": {"initial": 0.0, "final": 0.0, "iterations": 0},
                            "p": {"initial": 0.1, "final": 1e-13, "iterations": 4},
                        },
                        "continuity": {
                            "local_sum": 1e-15,
                            "global": 0.0,
                            "cumulative": 0.0,
                        },
                    },
                    "velocity_error": {
                        "l2_absolute_m_s": l2_error,
                        "l2_relative": 1e-4,
                        "linf_absolute_m_s": linf_error,
                        "linf_relative": 2e-4,
                        "max_transverse_absolute_m_s": 0.0,
                    },
                    "mass_flow": {
                        "cell_integrated_volumetric_m3_s": 6.6e-6,
                        "streamwise_min_outward_volumetric_m3_s": -6.6e-6,
                        "streamwise_max_outward_volumetric_m3_s": 6.6e-6,
                        "patch_mean_absolute_volumetric_m3_s": 6.6e-6,
                        "analytic_relative_error": 1e-4,
                        "cell_integrated_relative_error": 1e-4,
                        "cyclic_pair_antisymmetry_relative": 0.0,
                    },
                }
            )
        convergence = {
            norm: [
                {"from": "coarse", "to": "medium", "order": 2.0},
                {"from": "medium", "to": "fine", "order": 2.0},
            ]
            for norm in ("l2", "linf")
        }
        return [
            {
                "schema_version": "1.0",
                "benchmark_id": self.contract["benchmark_id"],
                "repeat_id": repeat_id,
                "report_status": "passed",
                "failures": [],
                "meshes": copy.deepcopy(mesh_reports),
                "convergence": copy.deepcopy(convergence),
                "gates": copy.deepcopy(self.contract["gates"]),
            }
            for repeat_id in ("repeat-1", "repeat-2")
        ]

    def synthetic_image_metadata(self):
        return {
            "image_id": "sha256:a1db60cbf61b",
            "repo_digests": [self.contract["container"]["image"]],
            "architecture": "amd64",
            "os": "linux",
        }

    def test_contract_is_synthetic_digest_pinned_and_closes_engine_gates(self):
        self.generator.validate_contract(self.contract, CONTRACT_PATH.parent)

        self.assertEqual(self.contract["milestone"], "F25")
        self.assertEqual(
            self.contract["scope"]["kind"], "synthetic_tool_solver_verification"
        )
        self.assertEqual(self.contract["scope"]["source_data"], "synthetic_only")
        self.assertIsNone(self.contract["scope"]["porsche_asset"])
        self.assertIsNone(self.contract["scope"]["engine_variant"])
        self.assertEqual(
            self.contract["container"]["image"], self.generator.EXPECTED_IMAGE
        )
        self.assertEqual(self.contract["container"]["network"], "none")
        self.assertTrue(
            self.contract["container"]["confinement"]["read_only_root_filesystem"]
        )
        self.assertEqual(
            self.contract["container"]["confinement"]["case_mount_scope"],
            "single_case_read_write",
        )
        self.assertEqual(
            self.contract["acceptance"]["ux_linear_solver_final_residual_max"], 1e-8
        )
        self.assertTrue(all(value is False for value in self.contract["gates"].values()))

    def test_contract_rejects_digest_drift_and_any_open_gate(self):
        changed = copy.deepcopy(self.contract)
        changed["container"]["image"] = "ghcr.io/example/image@sha256:bad"
        with self.assertRaisesRegex(self.generator.ContractError, "digest"):
            self.generator.validate_contract(changed, CONTRACT_PATH.parent)

        changed = copy.deepcopy(self.contract)
        changed["gates"]["fabrication_authorized"] = True
        with self.assertRaisesRegex(self.generator.ContractError, "gate_must_remain_closed"):
            self.generator.validate_contract(changed, CONTRACT_PATH.parent)

        changed = copy.deepcopy(self.contract)
        changed["container"]["confinement"]["no_new_privileges"] = False
        with self.assertRaisesRegex(self.generator.ContractError, "confinement"):
            self.generator.validate_contract(changed, CONTRACT_PATH.parent)

    def test_contract_rejects_non_finite_or_unlocked_acceptance(self):
        for value in (float("nan"), float("inf"), float("-inf"), True):
            with self.subTest(value=value):
                changed = copy.deepcopy(self.contract)
                changed["acceptance"]["ux_linear_solver_final_residual_max"] = value
                with self.assertRaisesRegex(
                    self.generator.ContractError, "acceptance_value_must_remain_locked"
                ):
                    self.generator.validate_contract(changed, CONTRACT_PATH.parent)

        changed = copy.deepcopy(self.contract)
        changed["physics"]["kinematic_viscosity_m2_s"] = float("nan")
        with self.assertRaisesRegex(self.generator.ContractError, "positive_physics_value"):
            self.generator.validate_contract(changed, CONTRACT_PATH.parent)

        with tempfile.TemporaryDirectory() as temp_dir:
            invalid = Path(temp_dir) / "contract.json"
            invalid.write_text('{"acceptance": {"x": NaN}}', encoding="utf-8")
            with self.assertRaisesRegex(
                self.generator.ContractError, "non_finite_json_constant:NaN"
            ):
                self.generator.load_contract(invalid)

    def test_contract_rejects_scope_and_deck_path_drift(self):
        changed = copy.deepcopy(self.contract)
        changed["scope"]["excluded_workflows"].append("unexpected-workflow")
        with self.assertRaisesRegex(self.generator.ContractError, "excluded_workflows"):
            self.generator.validate_contract(changed, CONTRACT_PATH.parent)

        for root in ("/tmp/decks", "../decks"):
            with self.subTest(root=root):
                changed = copy.deepcopy(self.contract)
                changed["decks"]["root"] = root
                with self.assertRaisesRegex(self.generator.ContractError, "deck_root"):
                    self.generator.validate_contract(changed, CONTRACT_PATH.parent)

        changed = copy.deepcopy(self.contract)
        changed["decks"]["files"][0] = "../0/U"
        with self.assertRaisesRegex(
            self.generator.ContractError, "deck_files_must_remain_locked"
        ):
            self.generator.validate_contract(changed, CONTRACT_PATH.parent)

    def test_contract_rejects_symlinked_deck_root_or_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            contract_dir = temp / "benchmark"
            contract_dir.mkdir()
            external_decks = temp / "external-decks"
            shutil.copytree(BENCHMARK / "decks", external_decks)
            (contract_dir / "decks").symlink_to(external_decks, target_is_directory=True)

            with self.assertRaisesRegex(
                self.generator.ContractError,
                "deck_root_symlink_forbidden|resolved_deck_root_outside_contract",
            ):
                self.generator.validate_contract(
                    copy.deepcopy(self.contract), contract_dir
                )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            contract_dir = temp / "benchmark"
            contract_dir.mkdir()
            shutil.copytree(BENCHMARK / "decks", contract_dir / "decks")
            deck = contract_dir / "decks/0/U"
            external = temp / "external-U"
            external.write_text(deck.read_text(encoding="utf-8"), encoding="utf-8")
            deck.unlink()
            deck.symlink_to(external)

            with self.assertRaisesRegex(
                self.generator.ContractError,
                "deck_symlink_forbidden|resolved_deck_outside_root",
            ):
                self.generator.validate_contract(
                    copy.deepcopy(self.contract), contract_dir
                )

    def test_generator_creates_only_three_input_cases(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "cases"
            generated = self.generator.generate_cases(CONTRACT_PATH, output)

            self.assertEqual([path.name for path in generated], ["coarse", "medium", "fine"])
            for mesh_id, cells_y in self.generator.EXPECTED_MESHES:
                case = output / mesh_id
                self.assertTrue((case / "0/U").is_file())
                self.assertTrue((case / "0/p").is_file())
                block_mesh = (case / "system/blockMeshDict").read_text(encoding="utf-8")
                self.assertIn(f"(1 {cells_y} 1)", block_mesh)
                self.assertNotRegex(block_mesh, self.generator.PLACEHOLDER_RE)
                numeric_directories = [
                    path.name
                    for path in case.iterdir()
                    if path.is_dir() and path.name.replace(".", "", 1).isdigit()
                ]
                self.assertEqual(numeric_directories, ["0"])
                self.assertFalse((case / "constant/polyMesh").exists())
                self.assertFalse((case / "postProcessing").exists())

    def test_generator_never_overwrites_evidence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "cases"
            output.mkdir()
            marker = output / "keep.txt"
            marker.write_text("keep", encoding="utf-8")

            with self.assertRaises(FileExistsError):
                self.generator.generate_cases(CONTRACT_PATH, output)
            self.assertEqual(marker.read_text(encoding="utf-8"), "keep")

    def test_analytic_solution_and_second_order_calculation(self):
        velocity = self.analyzer.analytic_velocity(
            y_m=0.0,
            height_m=0.02,
            acceleration_m_s2=0.01,
            nu_m2_s=1e-5,
        )
        flow = self.analyzer.analytic_volumetric_flow(
            height_m=0.02,
            depth_m=0.01,
            acceleration_m_s2=0.01,
            nu_m2_s=1e-5,
        )
        self.assertAlmostEqual(velocity, 0.05, places=14)
        self.assertAlmostEqual(flow, 6.666666666666667e-6, places=18)

        metrics = []
        for mesh_id, spacing, error in (
            ("coarse", 0.0025, 4e-4),
            ("medium", 0.00125, 1e-4),
            ("fine", 0.000625, 2.5e-5),
        ):
            metrics.append(
                {
                    "mesh_id": mesh_id,
                    "mesh_spacing_y_m": spacing,
                    "velocity_error": {"l2_absolute_m_s": error},
                }
            )
        orders = self.analyzer.observed_orders(metrics, "l2_absolute_m_s")
        self.assertEqual([item["order"] for item in orders], [2.0, 2.0])

    def test_aggregate_keeps_engine_and_fabrication_claims_false(self):
        aggregate = self.analyzer.aggregate_reports(
            self.contract,
            self.synthetic_repeat_reports(),
            self.synthetic_image_metadata(),
        )

        self.assertEqual(aggregate["report_status"], "passed")
        self.assertTrue(aggregate["claims"]["openfoam_tool_solver_benchmark_verified"])
        self.assertFalse(aggregate["claims"]["porsche_917_engine_simulation_verified"])
        self.assertFalse(aggregate["claims"]["physicsnemo_dataset_sample_produced"])
        self.assertFalse(aggregate["claims"]["engine_design_verified"])
        self.assertFalse(aggregate["claims"]["fabrication_authorized"])
        self.assertTrue(aggregate["repeatability"]["canonical_metrics_identical"])
        self.assertEqual(
            aggregate["repeatability"]["maximum_absolute_difference"], 0.0
        )

    def test_aggregate_recomputes_and_rejects_tampered_residual(self):
        reports = self.synthetic_repeat_reports()
        reports[0]["meshes"][2]["solver"]["last_linear_residuals"]["Ux"][
            "final"
        ] = 1.0
        reports[0]["report_status"] = "passed"

        aggregate = self.analyzer.aggregate_reports(
            self.contract, reports, self.synthetic_image_metadata()
        )

        self.assertEqual(aggregate["report_status"], "failed")
        self.assertFalse(
            aggregate["claims"]["openfoam_tool_solver_benchmark_verified"]
        )
        self.assertIn(
            "repeat_validation:repeat-1:linear_solver_residual_exceeded:fine:Ux",
            aggregate["failures"],
        )

    def test_aggregate_rejects_missing_residual_even_if_declared_passed(self):
        reports = self.synthetic_repeat_reports()
        reports[1]["meshes"][0]["solver"]["last_linear_residuals"].pop("Ux")
        reports[1]["report_status"] = "passed"

        aggregate = self.analyzer.aggregate_reports(
            self.contract, reports, self.synthetic_image_metadata()
        )

        self.assertEqual(aggregate["report_status"], "failed")
        self.assertTrue(
            any("linear_solver_residual_exceeded:coarse:Ux" in item for item in aggregate["failures"])
        )

    def test_aggregate_rejects_non_finite_residual_tampering(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                reports = self.synthetic_repeat_reports()
                reports[0]["meshes"][1]["solver"]["last_linear_residuals"]["Ux"][
                    "final"
                ] = value
                reports[0]["report_status"] = "passed"

                aggregate = self.analyzer.aggregate_reports(
                    self.contract, reports, self.synthetic_image_metadata()
                )

                self.assertEqual(aggregate["report_status"], "failed")
                self.assertFalse(
                    aggregate["claims"]["openfoam_tool_solver_benchmark_verified"]
                )

    def test_aggregate_rejects_bad_or_missing_pressure_residual(self):
        for value in (1.01e-12, -1e-15, float("nan"), None):
            with self.subTest(value=value):
                reports = self.synthetic_repeat_reports()
                residuals = reports[0]["meshes"][2]["solver"][
                    "last_linear_residuals"
                ]
                if value is None:
                    residuals.pop("p")
                else:
                    residuals["p"]["final"] = value
                reports[0]["report_status"] = "passed"

                aggregate = self.analyzer.aggregate_reports(
                    self.contract, reports, self.synthetic_image_metadata()
                )

                self.assertEqual(aggregate["report_status"], "failed")
                self.assertFalse(
                    aggregate["claims"]["openfoam_tool_solver_benchmark_verified"]
                )
                self.assertTrue(
                    any(
                        "linear_solver_residual_exceeded:fine:p" in item
                        for item in aggregate["failures"]
                    )
                )

    def test_repeatability_hash_includes_solver_iterations(self):
        reports = self.synthetic_repeat_reports()
        reports[1]["meshes"][2]["solver"]["last_linear_residuals"]["Ux"][
            "iterations"
        ] = 3

        aggregate = self.analyzer.aggregate_reports(
            self.contract, reports, self.synthetic_image_metadata()
        )

        self.assertEqual(aggregate["report_status"], "failed")
        self.assertFalse(aggregate["repeatability"]["canonical_metrics_identical"])
        self.assertIn(
            "repeatability_canonical_metrics_differ", aggregate["failures"]
        )

    def test_repeat_rejects_excessive_or_missing_ux_residual(self):
        def accepted_metrics():
            output = []
            for mesh_id in ("coarse", "medium", "fine"):
                output.append(
                    {
                        "mesh_id": mesh_id,
                        "mesh_check": {
                            "passed": True,
                            "cell_count_matches": True,
                        },
                        "solver": {
                            "completed": True,
                            "openfoam_13_observed": True,
                            "simplefoam_delegation_observed": True,
                            "last_linear_residuals": {
                                "Ux": {"final": 1e-9},
                                "p": {"final": 1e-13},
                            },
                            "continuity": {"local_sum": 1e-15},
                        },
                        "mass_flow": {
                            "cyclic_pair_antisymmetry_relative": 0.0,
                            "analytic_relative_error": 1e-4,
                        },
                        "velocity_error": {
                            "max_transverse_absolute_m_s": 0.0,
                            "l2_relative": 1e-4,
                            "linf_relative": 1e-4,
                        },
                    }
                )
            return output

        excessive = accepted_metrics()
        excessive[1]["solver"]["last_linear_residuals"]["Ux"]["final"] = 1.01e-8
        failures = self.analyzer.evaluate_repeat(self.contract, excessive)
        self.assertIn("linear_solver_residual_exceeded:medium:Ux", failures)

        missing = accepted_metrics()
        missing[2]["solver"]["last_linear_residuals"].pop("Ux")
        failures = self.analyzer.evaluate_repeat(self.contract, missing)
        self.assertIn("linear_solver_residual_exceeded:fine:Ux", failures)

        bad_pressure = accepted_metrics()
        bad_pressure[0]["solver"]["last_linear_residuals"]["p"]["final"] = 1.01e-12
        failures = self.analyzer.evaluate_repeat(self.contract, bad_pressure)
        self.assertIn("linear_solver_residual_exceeded:coarse:p", failures)

        missing_pressure = accepted_metrics()
        missing_pressure[1]["solver"]["last_linear_residuals"].pop("p")
        failures = self.analyzer.evaluate_repeat(self.contract, missing_pressure)
        self.assertIn("linear_solver_residual_exceeded:medium:p", failures)

    def test_runner_is_local_digest_pinned_offline_and_non_destructive(self):
        runner = RUNNER_PATH.read_text(encoding="utf-8")

        self.assertIn(self.generator.EXPECTED_IMAGE, runner)
        self.assertIn("--platform linux/amd64", runner)
        self.assertIn("--network none", runner)
        self.assertIn("--read-only", runner)
        self.assertIn("--tmpfs /tmp:rw,noexec,nosuid,nodev,size=64m", runner)
        self.assertIn('--user "${HOST_UID}:${HOST_GID}"', runner)
        self.assertIn("--pids-limit 128", runner)
        self.assertIn("--cap-drop ALL", runner)
        self.assertIn("--security-opt no-new-privileges", runner)
        self.assertIn('--mount "type=bind,source=${CASE_DIR},target=/case"', runner)
        self.assertIn("--env HOME=/tmp", runner)
        self.assertNotIn("source=${CASES_DIR},target=", runner)
        self.assertIn("output_already_exists", GENERATOR_PATH.read_text(encoding="utf-8"))
        self.assertNotIn("rm -", runner)
        self.assertNotIn("physicsnemo", runner.lower())
        self.assertNotIn("classical-solver-cases-f13", runner)

    def test_benchmark_tree_has_no_generated_or_physicsnemo_artifact(self):
        forbidden_names = {"__pycache__", "polyMesh", "postProcessing"}
        forbidden_suffixes = {
            ".pyc",
            ".npz",
            ".pt",
            ".pth",
            ".h5",
            ".hdf5",
            ".foam",
            ".vtk",
            ".vtu",
        }
        violations = []
        for path in BENCHMARK.rglob("*"):
            relative = path.relative_to(BENCHMARK)
            if path.name in forbidden_names or path.suffix.lower() in forbidden_suffixes:
                violations.append(relative.as_posix())
            if any(part.isdigit() and part != "0" for part in relative.parts):
                violations.append(relative.as_posix())
        self.assertEqual(violations, [])

        tracked = subprocess.run(
            ["git", "ls-files", "--", str(BENCHMARK.relative_to(ROOT))],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        ).stdout.splitlines()
        self.assertFalse(
            any(
                ".DS_Store" in Path(item).parts or "__pycache__" in Path(item).parts
                for item in tracked
            )
        )

        ignore_rules = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(".DS_Store", ignore_rules)
        self.assertIn("__pycache__/", ignore_rules)


if __name__ == "__main__":
    unittest.main()
