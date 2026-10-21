"""Assert the software oracle and fail closed before any native fixture launch."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

SOURCE = Path(__file__).resolve().parents[1] / "twins/962-cylinder-head-f0/source"
sys.path.insert(0, str(SOURCE))
spec = importlib.util.spec_from_file_location("hxt_size_fixture", SOURCE / "check_hxt_size_cap_002.py")
fixture = importlib.util.module_from_spec(spec); spec.loader.exec_module(fixture)


class SoftwareOracle(unittest.TestCase):
    def test_strictly_more_actual_interior_nodes_requires_two_completed_cases(self):
        cases={name:dict(software_mesh_passed=True, worker_report=dict(referenced_interior_nodes=n))
               for name,n in zip(fixture.CASES, [0,1])}
        self.assertTrue(fixture.interior_refinement_passed(cases))
        for count in [0, False, None]:
            cases["capped-1p75"]["worker_report"]["referenced_interior_nodes"]=count
            self.assertFalse(fixture.interior_refinement_passed(cases))
        self.assertFalse(fixture.interior_refinement_passed({"uncapped":cases["uncapped"]}))

    def test_complete_outward_cube_and_only_cap_differs_without_head_or_native_access(self):
        with mock.patch.object(fixture.quality.audit_quality_head, "read") as head_read, \
                mock.patch.object(fixture.subprocess, "Popen") as launch:
            points, faces = fixture.cube(); contract = fixture.specification()
            self.assertEqual(points.shape, (8,3)); self.assertEqual(faces.shape, (12,3))
            self.assertEqual(points.min(axis=0).tolist(), [0,0,0])
            self.assertEqual(points.max(axis=0).tolist(), [7,7,7])
            self.assertEqual(contract["geometry"]["analytic_volume_mm3"], 343)
            first, second = contract["cases"].values()
            self.assertEqual({key for key in first if first[key] != second[key]}, {"Mesh.MeshSizeMax"})
            self.assertEqual(first["Mesh.MeshSizeMax"], 1e22)
            self.assertEqual(second["Mesh.MeshSizeMax"], 1.75)
            self.assertEqual(second["Mesh.Optimize"], 0)
            self.assertEqual(second["Mesh.MeshSizeExtendFromBoundary"], 0)
            self.assertFalse(contract["quality_scope"]["SICN_threshold_is_fixture_pass_condition"])
            self.assertEqual(contract["quality_scope"]["head_minimum_SICN_gate_unchanged"], .1)
            self.assertFalse(contract["quality_scope"]["head_accepted"])
            self.assertFalse(contract["native_execution_authorized_by_contract"])
            self.assertEqual(len(fixture.source_files()), 6)
            launch.assert_not_called(); head_read.assert_not_called()

    def test_changed_cube_cap_or_qualification_rejects_before_output_or_process(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); path=root/"contract.json"; output=root/"never-created"
            contract=fixture.specification()
            contract["source_sha256s"]={str(p.relative_to(fixture.ROOT)):fixture.mesh.sha(p) for p in fixture.source_files()}
            contract["test_sha256"]=fixture.mesh.sha(Path(__file__).resolve())
            variants=[]
            for change in ["cube", "cap", "qualification", "source"]:
                row=json.loads(json.dumps(contract))
                if change == "cube": row["geometry"]["outward_triangles"][0]=[0,1,2]
                elif change == "cap": row["cases"]["capped-1p75"]["Mesh.MeshSizeMax"]=2
                elif change == "qualification": row["quality_scope"]["head_accepted"]=True
                else: row["source_sha256s"][next(iter(row["source_sha256s"]))]="0"*64
                variants.append((change,row))
            with mock.patch.object(fixture.subprocess, "Popen") as launch, \
                    mock.patch.object(fixture, "worker") as worker:
                for change,row in variants:
                    path.write_text(json.dumps(row))
                    with self.subTest(change=change), self.assertRaisesRegex(ValueError, "specification changed|source bindings changed"):
                        fixture.main(["--contract",str(path),"--contract-sha256",fixture.mesh.sha(path),"--output",str(output)])
                launch.assert_not_called(); worker.assert_not_called(); self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
