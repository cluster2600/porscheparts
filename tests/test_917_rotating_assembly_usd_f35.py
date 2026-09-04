import ast
import hashlib
import json
import math
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "twins/reference-917-engine/source/author_rotating_assembly_usd_f35.py"
MATH_SOURCE = ROOT / "twins/reference-917-engine/source/rotating_assembly_f35_math.py"
CONTRACT = ROOT / "twins/reference-917-engine/rotating-assembly-cad-f35.json"

EXPECTED_VARIANTS = ("type_912_4_5_na", "917_30_turbo_5374")
EXPECTED_COUNTS = {
    "crankshaft": 1,
    "main_bearing": 8,
    "connecting_rod": 12,
    "piston": 12,
    "piston_pin": 12,
    "piston_ring": 36,
}
EXPECTED_DATUM_COUNTS = {
    "crankshaft_axis": 1,
    "main_journal_centres_01_to_08": 8,
    "crankpin_centres_01_to_06": 6,
    "rod_big_end_axis": 12,
    "rod_small_end_axis": 12,
    "piston_pin_axis": 12,
    "piston_crown_datum": 12,
    "piston_ring_groove_datums": 36,
}
SOURCE_FAMILIES = {
    "crankshaft": "crankshaft",
    "main_bearing": "main_bearing_pair",
    "connecting_rod": "connecting_rod",
    "piston": "piston",
    "piston_pin": "piston_pin",
    "piston_ring": "piston_ring",
}
FALSE_METADATA = (
    "historicalCylinderMappingResolved",
    "simulationValidated",
    "manufacturingReleased",
    "powerValidated",
)

try:
    from pxr import Gf, Sdf, Usd, UsdGeom

    HAVE_OPENUSD = True
except ImportError:
    HAVE_OPENUSD = False


def assignment_value(tree: ast.AST, name: str):
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    raise AssertionError(f"assignment not found: {name}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RotatingAssemblyUsdF35StaticContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = SOURCE.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.payload, filename=str(SOURCE))

    def test_source_is_valid_python_and_has_exact_public_constants(self):
        compile(self.payload, str(SOURCE), "exec")
        self.assertEqual(assignment_value(self.tree, "EXPECTED_VARIANT_IDS"), EXPECTED_VARIANTS)
        self.assertEqual(assignment_value(self.tree, "COMPONENT_COUNTS"), EXPECTED_COUNTS)
        self.assertEqual(assignment_value(self.tree, "EXPECTED_COMPONENT_TOTAL"), 81)
        self.assertEqual(assignment_value(self.tree, "EXPECTED_CANDIDATE_INTERFACE_COUNT"), 37)
        self.assertEqual(
            assignment_value(self.tree, "EXPECTED_DATUM_FRAME_COUNTS"),
            EXPECTED_DATUM_COUNTS,
        )
        self.assertEqual(assignment_value(self.tree, "SAMPLE_STEP_DEG"), 1.0)
        self.assertEqual(assignment_value(self.tree, "CRANK_DEGREES_PER_SECOND"), 60.0)
        self.assertEqual(assignment_value(self.tree, "USD_FILENAME"), "rotating-assembly-f35.usdc")
        self.assertEqual(
            assignment_value(self.tree, "REPORT_FILENAME"),
            "rotating-assembly-f35-report.json",
        )

    def test_kinematics_are_imported_from_the_single_f35_math_authority(self):
        imported = set()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.ImportFrom) and node.module == "rotating_assembly_f35_math":
                imported.update(alias.name for alias in node.names)
        self.assertEqual(
            imported,
            {
                "BANK_AXES",
                "CRANK_AXIS",
                "DESIGN_CRANKPIN_PHASES_DEG",
                "assembly_sample",
                "cycle_angles_deg",
                "paired_rod_axial_layout_mm",
                "paired_rod_axial_offset_mm",
            },
        )
        calls = {
            node.func.id
            for node in ast.walk(self.tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertIn("assembly_sample", calls)
        self.assertIn("cycle_angles_deg", calls)
        self.assertNotIn("sin", calls)
        self.assertNotIn("cos", calls)
        self.assertNotIn("atan2", calls)

    def test_source_does_not_import_or_author_a_physics_schema(self):
        imports = set()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.add(node.module or "")
                imports.update(alias.name for alias in node.names)
        self.assertNotIn("UsdPhysics", imports)
        self.assertNotIn("PhysxSchema", imports)
        self.assertNotIn("pxr.UsdPhysics", imports)
        self.assertNotIn("pxr.PhysxSchema", imports)
        self.assertNotIn("ApplyRigidBody", self.payload)
        self.assertNotIn("DefinePhysicsScene", self.payload)

    def test_all_false_metadata_and_release_gate_guards_are_explicit(self):
        self.assertEqual(assignment_value(self.tree, "FALSE_STAGE_METADATA_KEYS"), FALSE_METADATA)
        for token in (
            "manufacturing_geometry_ready",
            "engine_start_authorized",
            "performance_1600_hp_claim_authorized",
            "all_release_gates_must_be_explicitly_false",
        ):
            self.assertIn(token, self.payload)

    def test_outputs_are_hard_limited_to_the_f35_work_tree(self):
        self.assertIn('WORK_ROOT = REPO_ROOT / "work/917-rotating-assembly-f35"', self.payload)
        self.assertIn("work_root_must_be_f35_canonical", self.payload)
        self.assertIn('output_dir = WORK_ROOT / variant_id / "usd"', self.payload)
        self.assertNotIn("raw-scans", self.payload.lower())
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(
            set(contract["output_policy"]["derived_formats"]),
            {"STEP", "STL", "JSON", "USD", "USDC"},
        )
        self.assertEqual(
            contract["output_policy"]["derived_output_layout"]["converted_usd_prototype"],
            "usd-conversion/{variant}/prototypes/{family}/{family}.usd",
        )
        self.assertEqual(
            contract["output_policy"]["derived_output_layout"]["animated_usdc_stage"],
            "{variant}/usd/rotating-assembly-f35.usdc",
        )


@unittest.skipUnless(HAVE_OPENUSD, "OpenUSD Python is provided by the SimReady container")
class RotatingAssemblyUsdF35OpenUsdTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="f35-usd-test-")
        self.repo = Path(self.temporary.name) / "repo"

    def tearDown(self):
        self.temporary.cleanup()

    def _prepare_repo(
        self,
        *,
        missing=None,
        true_gate=None,
        wrong_axis=None,
        wrong_units=None,
        stale_output_digest=None,
    ):
        source_dir = self.repo / "twins/reference-917-engine/source"
        source_dir.mkdir(parents=True)
        shutil.copy2(SOURCE, source_dir / SOURCE.name)
        shutil.copy2(MATH_SOURCE, source_dir / MATH_SOURCE.name)
        contract_dir = self.repo / "twins/reference-917-engine"
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        if true_gate is not None:
            contract["release_gates"][true_gate] = True
        (contract_dir / CONTRACT.name).write_text(
            json.dumps(contract, indent=2) + "\n",
            encoding="utf-8",
        )
        variants = {item["id"]: item for item in contract["variants"]}
        for variant_id in EXPECTED_VARIANTS:
            for source_family in SOURCE_FAMILIES.values():
                if missing == (variant_id, source_family):
                    continue
                source = (
                    self.repo
                    / "work/917-rotating-assembly-f35"
                    / variant_id
                    / "step"
                    / f"{source_family}.step"
                )
                source.parent.mkdir(parents=True, exist_ok=True)
                source.write_text(
                    f"ISO-10303-21;\n/* {variant_id}:{source_family} fixture */\nEND-ISO-10303-21;\n",
                    encoding="utf-8",
                )
                path = (
                    self.repo
                    / "work/917-rotating-assembly-f35/usd-conversion"
                    / variant_id
                    / "prototypes"
                    / source_family
                    / f"{source_family}.usd"
                )
                path.parent.mkdir(parents=True, exist_ok=True)
                stage = Usd.Stage.CreateNew(str(path))
                root = UsdGeom.Xform.Define(stage, f"/{source_family}").GetPrim()
                stage.SetDefaultPrim(root)
                UsdGeom.SetStageUpAxis(
                    stage,
                    UsdGeom.Tokens.y
                    if wrong_axis == (variant_id, source_family)
                    else UsdGeom.Tokens.z,
                )
                UsdGeom.SetStageMetersPerUnit(
                    stage,
                    1.0 if wrong_units == (variant_id, source_family) else 0.001,
                )
                root.SetCustomDataByKey("3dprinting993:testFixture", True)
                stage.GetRootLayer().Save()
                report = {
                    "schema_version": "1.0",
                    "status": "passed",
                    "source_asset": str(source.resolve()),
                    "source_sha256": sha256(source),
                    "source_stable_during_conversion": True,
                    "output_usd": str(path.resolve()),
                    "output_sha256": sha256(path),
                    "atomic_output_commit": True,
                    "requested_up_axis": "Z",
                    "returncode": 0,
                    "errors": [],
                }
                if stale_output_digest == (variant_id, source_family):
                    report["output_sha256"] = "0" * 64
                (path.parent / "conversion-report.json").write_text(
                    json.dumps(report, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
        return source_dir / SOURCE.name

    def _run(self, script):
        return subprocess.run(
            [sys.executable, str(script)],
            cwd=self.repo,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def _output_dir(self, variant_id):
        return self.repo / "work/917-rotating-assembly-f35" / variant_id / "usd"

    def test_missing_prototype_fails_before_any_output_is_created(self):
        script = self._prepare_repo(missing=(EXPECTED_VARIANTS[1], "piston_ring"))
        result = self._run(script)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn(
            "exactly_one_usd_prototype_required:917_30_turbo_5374:piston_ring",
            result.stderr,
        )
        for variant_id in EXPECTED_VARIANTS:
            self.assertFalse(self._output_dir(variant_id).exists())

    def test_true_release_gate_fails_before_prototype_or_output_authoring(self):
        script = self._prepare_repo(true_gate="performance_1600_hp_claim_authorized")
        result = self._run(script)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("all_release_gates_must_be_explicitly_false", result.stderr)
        for variant_id in EXPECTED_VARIANTS:
            self.assertFalse(self._output_dir(variant_id).exists())

    def test_y_up_prototype_is_rejected_before_output_authoring(self):
        target = (EXPECTED_VARIANTS[0], "connecting_rod")
        script = self._prepare_repo(wrong_axis=target)
        result = self._run(script)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn(
            "prototype_up_axis_must_be_Z:type_912_4_5_na:connecting_rod:Y",
            result.stderr,
        )
        for variant_id in EXPECTED_VARIANTS:
            self.assertFalse(self._output_dir(variant_id).exists())

    def test_non_millimetre_prototype_is_rejected_before_output_authoring(self):
        target = (EXPECTED_VARIANTS[0], "piston")
        script = self._prepare_repo(wrong_units=target)
        result = self._run(script)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn(
            "prototype_meters_per_unit_must_be_0_001:type_912_4_5_na:piston:1.0",
            result.stderr,
        )

    def test_stale_prototype_digest_is_rejected_before_output_authoring(self):
        target = (EXPECTED_VARIANTS[1], "piston_pin")
        script = self._prepare_repo(stale_output_digest=target)
        result = self._run(script)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn(
            "prototype_output_digest_stale:917_30_turbo_5374:piston_pin",
            result.stderr,
        )

    def test_two_stages_have_exact_counts_animation_and_no_active_physics(self):
        script = self._prepare_repo()
        result = self._run(script)
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads(result.stdout)
        self.assertEqual(summary["status"], "passed")
        self.assertEqual(
            tuple(item["variant_id"] for item in summary["variant_reports"]),
            EXPECTED_VARIANTS,
        )

        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        variants = {item["id"]: item for item in contract["variants"]}
        for variant_id in EXPECTED_VARIANTS:
            with self.subTest(variant=variant_id):
                output_dir = self._output_dir(variant_id)
                self.assertEqual(
                    {path.name for path in output_dir.iterdir()},
                    {"rotating-assembly-f35.usdc", "rotating-assembly-f35-report.json"},
                )
                stage_path = output_dir / "rotating-assembly-f35.usdc"
                stage = Usd.Stage.Open(str(stage_path))
                self.assertIsNotNone(stage)
                self.assertEqual(UsdGeom.GetStageMetersPerUnit(stage), 0.001)
                self.assertEqual(UsdGeom.GetStageUpAxis(stage), UsdGeom.Tokens.z)
                self.assertEqual(stage.GetStartTimeCode(), 0.0)
                self.assertEqual(stage.GetEndTimeCode(), 720.0)
                self.assertEqual(stage.GetTimeCodesPerSecond(), 60.0)
                self.assertEqual(stage.GetFramesPerSecond(), 60.0)
                self.assertEqual(len(stage.GetPrototypes()), 6)
                camera = stage.GetPrimAtPath("/World/ReviewCamera")
                self.assertTrue(camera.IsValid())
                self.assertEqual(camera.GetTypeName(), "Camera")
                self.assertEqual(
                    camera.GetCustomDataByKey("3dprinting993:status"),
                    "diagnostic_view_only",
                )

                world = stage.GetPrimAtPath("/World")
                self.assertTrue(world.IsValid())
                self.assertEqual(world.GetMetadata("kind"), "assembly")
                self.assertEqual(stage.GetPrimAtPath("/World/Components").GetMetadata("kind"), "group")
                for family in EXPECTED_COUNTS:
                    self.assertEqual(
                        stage.GetPrimAtPath(f"/World/Components/{family}").GetMetadata("kind"),
                        "group",
                    )
                for key in FALSE_METADATA:
                    self.assertIs(world.GetCustomDataByKey(key), False)
                    self.assertIs(world.GetCustomDataByKey(f"3dprinting993:{key}"), False)
                self.assertEqual(world.GetCustomDataByKey("3dprinting993:physicalJointCount"), 0)
                self.assertEqual(world.GetCustomDataByKey("3dprinting993:rigidBodyCount"), 0)
                self.assertEqual(world.GetCustomDataByKey("3dprinting993:colliderCount"), 0)
                self.assertIs(world.GetCustomDataByKey("3dprinting993:massOrInertiaAuthored"), False)
                self.assertIs(world.GetCustomDataByKey("3dprinting993:physicalMaterialAuthored"), False)
                paired_layout = json.loads(
                    world.GetCustomDataByKey("3dprinting993:pairedRodAxialLayoutJson")
                )
                self.assertEqual(
                    paired_layout["topology"],
                    "side_by_side_visual_design_hypothesis",
                )
                self.assertIs(paired_layout["shared_crankpin_width_validated"], False)

                occurrences = [
                    prim
                    for prim in stage.TraverseAll()
                    if prim.GetCustomDataByKey("3dprinting993:isOccurrence") is True
                ]
                self.assertEqual(len(occurrences), 81)
                counts = {}
                for prim in occurrences:
                    self.assertEqual(prim.GetMetadata("kind"), "assembly")
                    family = prim.GetCustomDataByKey("3dprinting993:family")
                    counts[family] = counts.get(family, 0) + 1
                    self.assertTrue(prim.IsInstance())
                    self.assertEqual(prim.GetTypeName(), "Xform")
                self.assertEqual(counts, EXPECTED_COUNTS)

                candidates = [
                    prim
                    for prim in Usd.PrimRange(stage.GetPrimAtPath("/World/InterfaceCandidates"))
                    if prim.GetPath() != Sdf.Path("/World/InterfaceCandidates")
                ]
                self.assertEqual(len(candidates), 37)
                self.assertTrue(
                    all(prim.GetCustomDataByKey("3dprinting993:enabled") is False for prim in candidates)
                )
                self.assertTrue(
                    all(
                        prim.GetCustomDataByKey("3dprinting993:physicsJointAuthored") is False
                        for prim in candidates
                    )
                )

                datums_scope = stage.GetPrimAtPath("/World/Datums")
                self.assertTrue(datums_scope.IsValid())
                self.assertEqual(
                    datums_scope.GetCustomDataByKey("3dprinting993:expectedDatumCount"),
                    99,
                )
                self.assertEqual(
                    datums_scope.GetCustomDataByKey("3dprinting993:measuredDatumCount"),
                    0,
                )
                datums = [
                    prim
                    for prim in Usd.PrimRange(datums_scope)
                    if prim.GetCustomDataByKey("3dprinting993:datumFamily") is not None
                ]
                self.assertEqual(len(datums), 99)
                datum_counts = {
                    family: sum(
                        prim.GetCustomDataByKey("3dprinting993:datumFamily") == family
                        for prim in datums
                    )
                    for family in EXPECTED_DATUM_COUNTS
                }
                self.assertEqual(datum_counts, EXPECTED_DATUM_COUNTS)
                self.assertTrue(
                    all(prim.GetCustomDataByKey("3dprinting993:measured") is False for prim in datums)
                )
                self.assertTrue(
                    all(
                        prim.GetCustomDataByKey("3dprinting993:physicsJointAuthored") is False
                        for prim in datums
                    )
                )
                self.assertEqual(
                    len(
                        stage.GetPrimAtPath(
                            "/World/Datums/crankpin_centres_01_to_06/crankpin_centre_station_01"
                        ).GetAttribute("xformOp:translate").GetTimeSamples()
                    ),
                    721,
                )
                self.assertEqual(
                    len(
                        stage.GetPrimAtPath(
                            "/World/Datums/piston_crown_datum/piston_crown_datum_bank_A_station_01"
                        ).GetAttribute("xformOp:translate").GetTimeSamples()
                    ),
                    721,
                )

                crank = stage.GetPrimAtPath("/World/Components/crankshaft/crankshaft")
                crank_samples = crank.GetAttribute("xformOp:rotateX").GetTimeSamples()
                self.assertEqual(len(crank_samples), 721)
                self.assertEqual((crank_samples[0], crank_samples[-1]), (0.0, 720.0))
                rod = stage.GetPrimAtPath(
                    "/World/Components/connecting_rod/connecting_rod_bank_A_station_01"
                )
                self.assertEqual(len(rod.GetAttribute("xformOp:translate").GetTimeSamples()), 721)
                self.assertEqual(len(rod.GetAttribute("xformOp:rotateX").GetTimeSamples()), 721)
                piston = stage.GetPrimAtPath(
                    "/World/Components/piston/piston_bank_B_station_06"
                )
                self.assertEqual(len(piston.GetAttribute("xformOp:translate").GetTimeSamples()), 721)
                self.assertEqual(piston.GetAttribute("xformOp:rotateX").Get(), 180.0)

                for prim in list(stage.TraverseAll()) + [
                    nested
                    for prototype in stage.GetPrototypes()
                    for nested in Usd.PrimRange(prototype)
                ]:
                    self.assertFalse(prim.GetTypeName().endswith("Joint"), prim.GetPath())
                    self.assertNotEqual(prim.GetTypeName(), "PhysicsScene")
                    for schema in prim.GetAppliedSchemas():
                        self.assertNotIn("RigidBodyAPI", schema)
                        self.assertNotIn("CollisionAPI", schema)
                        self.assertNotIn("MassAPI", schema)
                        self.assertNotIn("PhysicsMaterialAPI", schema)
                        self.assertNotIn("Physx", schema)
                    for prop in prim.GetProperties():
                        name = str(prop.GetName()).lower()
                        self.assertFalse(name.startswith("physics:"), (prim.GetPath(), name))
                        self.assertFalse(name.startswith("physx"), (prim.GetPath(), name))

                parameters = {
                    key: value["value"]
                    for key, value in variants[variant_id]["parameters"].items()
                }
                rod_length = parameters["rod_center_distance_mm"]
                for time in (0.0, 90.0, 360.0, 720.0):
                    for geometric_id in ("bank_A_station_01", "bank_B_station_06"):
                        rod_prim = stage.GetPrimAtPath(
                            f"/World/Components/connecting_rod/connecting_rod_{geometric_id}"
                        )
                        matrix = UsdGeom.XformCache(Usd.TimeCode(time)).GetLocalToWorldTransform(
                            rod_prim
                        )
                        big_end = matrix.Transform(Gf.Vec3d(0.0, 0.0, 0.0))
                        small_end = matrix.Transform(Gf.Vec3d(0.0, rod_length, 0.0))
                        big_frame = stage.GetPrimAtPath(
                            f"/World/InterfaceCandidates/crankpin_to_rod_{geometric_id}"
                        )
                        small_frame = stage.GetPrimAtPath(
                            f"/World/InterfaceCandidates/rod_to_pin_{geometric_id}"
                        )
                        expected_big = big_frame.GetAttribute("xformOp:translate").Get(time)
                        expected_small = small_frame.GetAttribute("xformOp:translate").Get(time)
                        for actual, expected in ((big_end, expected_big), (small_end, expected_small)):
                            self.assertLess(
                                math.sqrt(sum((actual[index] - expected[index]) ** 2 for index in range(3))),
                                1.0e-8,
                            )

                    for station_index in range(1, 7):
                        rod_a = stage.GetPrimAtPath(
                            "/World/Components/connecting_rod/"
                            f"connecting_rod_bank_A_station_{station_index:02d}"
                        )
                        rod_b = stage.GetPrimAtPath(
                            "/World/Components/connecting_rod/"
                            f"connecting_rod_bank_B_station_{station_index:02d}"
                        )
                        x_a = rod_a.GetAttribute("xformOp:translate").Get(time)[0]
                        x_b = rod_b.GetAttribute("xformOp:translate").Get(time)[0]
                        surface_gap = abs(x_a - x_b) - parameters["rod_width_mm"]
                        self.assertGreater(surface_gap, 0.0)
                        self.assertTrue(
                            math.isclose(
                                surface_gap,
                                paired_layout["clearance_mm"],
                                rel_tol=0.0,
                                abs_tol=1.0e-10,
                            )
                        )

                report = json.loads(
                    (output_dir / "rotating-assembly-f35-report.json").read_text(encoding="utf-8")
                )
                self.assertEqual(report["variant_id"], variant_id)
                self.assertEqual(report["component_occurrence_counts"], EXPECTED_COUNTS)
                self.assertEqual(report["component_occurrence_total"], 81)
                self.assertEqual(report["prototype_count"], 6)
                self.assertEqual(
                    report["stage_metadata"],
                    {"meters_per_unit": 0.001, "up_axis": "Z"},
                )
                self.assertIs(report["atomic_stage_commit"], True)
                self.assertEqual(report["paired_rod_axial_layout"], paired_layout)
                for prototype in report["prototypes"].values():
                    self.assertIs(prototype["atomic_output_commit"], True)
                    self.assertEqual(prototype["up_axis"], "Z")
                    self.assertEqual(prototype["meters_per_unit"], 0.001)
                self.assertEqual(report["candidate_interfaces"]["total"], 37)
                self.assertEqual(report["candidate_interfaces"]["enabled"], 0)
                self.assertEqual(report["datum_frames"]["family_counts"], EXPECTED_DATUM_COUNTS)
                self.assertEqual(report["datum_frames"]["total"], 99)
                self.assertEqual(report["datum_frames"]["measured"], 0)
                self.assertEqual(report["datum_frames"]["physical_joint_authored"], 0)
                self.assertEqual(report["animation"]["sample_count"], 721)
                self.assertEqual(report["animation"]["duration_seconds"], 12.0)
                self.assertEqual(report["authored_physics"]["audit_findings"], [])
                self.assertTrue(all(value is False for value in report["release_gates"].values()))
                for key in FALSE_METADATA:
                    self.assertIs(report[key], False)
                serialized = json.dumps(report, sort_keys=True)
                self.assertNotIn(str(self.repo), serialized)
                self.assertNotIn("/Users/", serialized)

                layer_text = stage.GetRootLayer().ExportToString()
                self.assertNotIn(str(self.repo), layer_text)
                self.assertIn(f"usd-conversion/{variant_id}/prototypes", layer_text)
                other_variant = next(item for item in EXPECTED_VARIANTS if item != variant_id)
                self.assertNotIn(f"usd-conversion/{other_variant}/prototypes", layer_text)


if __name__ == "__main__":
    unittest.main()
