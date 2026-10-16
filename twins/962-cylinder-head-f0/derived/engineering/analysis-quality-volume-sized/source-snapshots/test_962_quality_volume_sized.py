"""Sized head dispatch keeps the frozen audits and refuses changed cube evidence."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock

SOURCE = Path(__file__).resolve().parents[1] / "twins/962-cylinder-head-f0/source"
sys.path.insert(0, str(SOURCE))
import mesh_quality_head as ordinary
spec=importlib.util.spec_from_file_location("sized_head", SOURCE/"mesh_quality_head_sized.py")
sized=importlib.util.module_from_spec(spec); spec.loader.exec_module(sized)


class SizedEntrypoint(unittest.TestCase):
    def test_isolated_entrypoints_bind_seven_sources_and_only_add_declared_sizing(self):
        original={name:getattr(ordinary,name) for name in ["__file__","OPTIONS","OUTPUT","save","source_files"]}
        expected_options={**ordinary.OPTIONS,"Mesh.Optimize":0,**sized.SIZING}
        fixture_scope=dict(insertion_control_demonstrated=True, capped_cube_minimum_SICN=.027175498119979526,
            capped_cube_passes_head_SICN_gate=False, head_resolution_or_quality_established=False)
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(sized,"require_fixture",return_value=fixture_scope):
            root=Path(temporary).resolve(); admission=root/"admission.json"; admission.write_text("mock admission")
            output=root/"mocked-head-output"; created=[]; configure=sized.configure_core
            def controller():
                core=configure();created.append(core)
                self.assertIsNot(core,ordinary)
                self.assertEqual(core.OUTPUT,core.ROOT/"work/962-engineering/quality-volume-hxt-sized-001")
                self.assertEqual(core.DEADLINE,300);self.assertEqual(core.RSS_STOP,8*1024**3)
                core.OUTPUT=output;core.require_admission=mock.Mock()
                return core
            args=["--admission",str(admission),"--admission-sha256",ordinary.sha(admission),"--output",str(output)]
            process=mock.Mock(pid=12345,returncode=2);process.poll.return_value=2
            with mock.patch.object(sized,"configure_core",side_effect=controller), \
                    mock.patch.object(subprocess,"Popen",return_value=process) as launch, \
                    mock.patch.object(threading,"Timer"),mock.patch("sys.stdout",new_callable=io.StringIO):
                self.assertEqual(sized.main(args),2);launch.assert_called_once()
            receipt=json.loads((output/"receipt.json").read_text());sources=created[0].source_files()
            self.assertEqual(len(sources),7)
            self.assertEqual(receipt["command"][1],str(sized.WRAPPER_PATH));self.assertIn("--worker",receipt["command"])
            self.assertEqual(receipt["options"],expected_options)
            self.assertEqual(receipt["source_sha256s"],{str(p.relative_to(ordinary.ROOT)):ordinary.sha(p) for p in sources})
            for path in sources:self.assertEqual(ordinary.sha(output/"source-snapshots"/path.name),ordinary.sha(path))
            self.assertFalse(receipt["seed_companion"]["standard_optimization_enabled"])
            self.assertEqual(receipt["sized_companion"]["actual_minimum_SICN_gate_unchanged"],.1)
            self.assertFalse(receipt["sized_companion"]["fixture"]["capped_cube_passes_head_SICN_gate"])
            self.assertFalse((output/"head-volume.msh").exists())
            def worker():
                core=configure();created.append(core)
                def check(parsed):
                    self.assertTrue(parsed.worker);self.assertIsNot(core,created[0]);self.assertIsNot(core,ordinary)
                    self.assertEqual(core.__file__,str(sized.WRAPPER_PATH));self.assertEqual(core.OPTIONS,expected_options)
                    self.assertEqual(core.source_files(),sources)
                    return 2
                core.worker=mock.Mock(side_effect=check)
                return core
            with mock.patch.object(sized,"configure_core",side_effect=worker),mock.patch.object(subprocess,"Popen") as launch:
                self.assertEqual(sized.main([*args,"--worker"]),2);launch.assert_not_called()
        for name,value in original.items():self.assertIs(getattr(ordinary,name),value)

    def test_fixture_drift_blocks_both_entrypoints_before_output_or_native_launch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); evidence=root/"fixture.json"; evidence.write_text(json.dumps(dict(software_fixture_passed=True,head_accepted=False)))
            pins={"fixture.json":hashlib.sha256(evidence.read_bytes()).hexdigest()};output=root/"never-created"
            args=["--admission",str(root/"unused.json"),"--admission-sha256","a"*64,"--output",str(output)]
            with mock.patch.object(sized,"ROOT",root),mock.patch.object(sized,"FIXTURE_RESULT","fixture.json"), \
                    mock.patch.object(sized,"FIXTURE_HASHES",pins),mock.patch.object(sized,"configure_core") as configure, \
                    mock.patch.object(subprocess,"Popen") as launch:
                self.assertTrue(sized.require_fixture()["insertion_control_demonstrated"])
                evidence.write_text("changed evidence")
                for suffix in [[],["--worker"]]:
                    with self.subTest(worker=bool(suffix)),self.assertRaisesRegex(ValueError,"evidence changed"):
                        sized.main([*args,*suffix])
                configure.assert_not_called();launch.assert_not_called();self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
