"""Independent hand values and rejection boundaries for a hypothetical solver witness."""
import importlib.util
import base64
import csv
import gzip
import json
import math
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1]/"twins/962-cylinder-head-f0/source/physics_witness/mechanical_birth"
PUBLIC = SOURCE.parents[2]/"derived/engineering/mechanical-birth-witness"
spec = importlib.util.spec_from_file_location("mechanical_birth_assess", SOURCE/"assess.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
runner_spec = importlib.util.spec_from_file_location("mechanical_birth_runner",SOURCE/"run_local.py")
runner = importlib.util.module_from_spec(runner_spec)
with patch.dict(sys.modules,{"assess":mod}):
    runner_spec.loader.exec_module(runner)


class MechanicalBirthTests(unittest.TestCase):
    def setUp(self):
        self.card = json.loads((SOURCE/"card.json").read_text())
        self.history = mod.references(self.card)

    def fields(self, folder):
        output=Path(folder)/"fields";shutil.copytree(PUBLIC/"data",output)
        frozen=json.loads((PUBLIC/"accepted-frozen-contract.json").read_text())
        return output,frozen

    def rewrite(self,path,change):
        with path.open(newline="") as stream:
            reader=csv.DictReader(stream);names=reader.fieldnames;data=list(reader)
        change(data)
        with path.open("w",newline="") as stream:
            writer=csv.DictWriter(stream,fieldnames=names);writer.writeheader();writer.writerows(data)

    def native_fixture(self,folder):
        """Synthetic attestation fixture from public fields; never represented as a native run."""
        out,frozen=self.fields(folder)
        for name,origin in {"card.json":PUBLIC/"source-snapshots/card.json",
                "assess.py":PUBLIC/"source-snapshots/frozen-assess.py",
                "mechanical-birth.i":PUBLIC/"source-snapshots/accepted-mechanical-birth.i",
                "frozen-contract.json":PUBLIC/"accepted-frozen-contract.json",
                "native.log":PUBLIC/"native.log"}.items():shutil.copyfile(origin,out/name)
        native=dict(returncode=0,started_unix=frozen["created_unix"]+1,deadline_seconds=100,
            binary_unchanged=True,inputs_unchanged=True,binary_sha256=self.card["native_binary_sha256"],
            network="none",rootfs="read_only",input_sha256={n:mod.sha(out/n) for n in
                ("card.json","mechanical-birth.i","frozen-contract.json")},
            artifact_sha256={p.name:mod.sha(p) for p in out.iterdir()})
        return out,frozen,native

    def capture_fixture(self,out,native):
        (out/"native-execution.json").write_text(json.dumps(native))
        payload=dict(native,artifacts_base64={p.name:base64.b64encode(p.read_bytes()).decode()
            for p in out.iterdir() if p.name not in ("ssh-execution.json","ssh-stdout.json.gz")})
        data=json.dumps(payload).encode();digest=mod.hashlib.sha256(data).hexdigest()
        (out/"ssh-stdout.json.gz").write_bytes(gzip.compress(data))
        (out/"ssh-execution.json").write_text(json.dumps(dict(stdout_sha256=digest)))
        return dict(native_receipt_sha256=mod.sha(out/"native-execution.json"),
                    original_transport_stdout_sha256=digest)

    def test_hand_computed_stress_history_and_release(self):
        self.assertEqual([r["sigma_MPa"] for r in self.history], [0.,1.,.5,.25,.65,0.,0.])
        self.assertAlmostEqual(self.history[5]["end_displacement_mm"], .037, places=14)
        self.assertEqual(self.history[5]["plastic_A"], .002)
        self.assertEqual(self.history[5]["plastic_B"], 0.)

    def test_birth_reference_is_relative_not_global_geometric_strain(self):
        state = self.history[3]
        new = mod.tensor_reference(state,"B")
        self.assertEqual(new["plastic_strain_zz"],0.)
        self.assertAlmostEqual(new["total_strain_zz"],.00025,places=14)
        self.assertAlmostEqual(state["physical_axial_strain_B"],.00275,places=14)
        self.assertAlmostEqual(mod.node_reference(state,1.,1.,10.)["disp_z"],.0225,places=14)

    def test_full_tensor_and_uniaxial_force_equilibrium(self):
        for state in self.history:
            if not state["born"]:
                continue
            a,b = mod.tensor_reference(state,"A"),mod.tensor_reference(state,"B")
            self.assertEqual(len(a),24)
            self.assertEqual(a["stress_zz"],b["stress_zz"])
            self.assertAlmostEqual(a["plastic_strain_xx"]+a["plastic_strain_yy"]+a["plastic_strain_zz"],0.)
            self.assertEqual(a["stress_xz"],0.)
            self.assertAlmostEqual(mod.node_reference(state,0,0,20)["disp_z"],state["end_displacement_mm"])

    def test_rows_reject_nonfinite_and_empty(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/"x.csv"
            for text in ["x\n", "x\nnan\n", "x\ninf\n", "x\n-inf\n"]:
                p.write_text(text)
                with self.assertRaises(ValueError):mod.rows(p)

    def test_existing_assessment_is_preserved_before_reading_inputs(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/"assessment.json";p.write_text("keep")
            done=subprocess.run([sys.executable,str(SOURCE/"assess.py"),folder,
                "--contract",str(Path(folder)/"absent.json"),"--output",str(p)],capture_output=True)
            self.assertNotEqual(done.returncode,0);self.assertEqual(p.read_text(),"keep")

    def test_card_units_recipe_and_qualification_are_explicit(self):
        self.assertEqual(self.card["units"],dict(length="mm",stress="MPa",force="N",temperature="K"))
        self.assertEqual(self.card["classification"],"HYPOTHETICAL_SOFTWARE_VERIFICATION_ONLY")
        self.assertTrue(all(v is False for v in self.card["qualification"].values()))
        self.assertLess(self.history[4]["sigma_MPa"],self.card["yield_MPa"])

    def test_public_full_fields_reproduce_without_private_work(self):
        result=mod.assess_fields(PUBLIC/"data",json.loads((PUBLIC/"accepted-frozen-contract.json").read_text()))
        self.assertTrue(result["passed"]);self.assertEqual(result["field_comparisons"],5514)

    def test_fractional_indices_rejected_before_conversion(self):
        for column in ("elem_id","qp_id"):
            with self.subTest(column=column),tempfile.TemporaryDirectory() as folder:
                out,frozen=self.fields(folder)
                self.rewrite(out/"mechanical_fields_0003.csv",lambda rows:rows[0].__setitem__(column,"0.25"))
                with self.assertRaisesRegex(ValueError,"exact nonnegative integer"):
                    mod.assess_fields(out,frozen)

    def test_distinct_qp_ids_cannot_hide_duplicate_gauss_locations(self):
        with tempfile.TemporaryDirectory() as folder:
            out,frozen=self.fields(folder)
            def duplicate(rows):
                for axis in ("x","y","z"):rows[1][axis]=rows[0][axis]
            self.rewrite(out/"mechanical_fields_0003.csv",duplicate)
            with self.assertRaisesRegex(ValueError,"unique Cartesian Gauss"):
                mod.assess_fields(out,frozen)

    def test_averages_cannot_hide_incorrect_nodal_displacement(self):
        with tempfile.TemporaryDirectory() as folder:
            out,frozen=self.fields(folder)
            def balanced(rows):
                rows[0]["disp_z"]=str(float(rows[0]["disp_z"])+1e-4)
                rows[1]["disp_z"]=str(float(rows[1]["disp_z"])-1e-4)
            self.rewrite(out/"mechanical_end_0003.csv",balanced)
            with self.assertRaises(ValueError):mod.assess_fields(out,frozen)

    def test_omitted_manifest_csv_is_rejected_even_with_valid_synthetic_capture(self):
        with tempfile.TemporaryDirectory() as folder:
            out,frozen,native=self.native_fixture(folder)
            del native["artifact_sha256"]["mechanical_fields_0003.csv"]
            binding=self.capture_fixture(out,native)
            with self.assertRaisesRegex(ValueError,"all consumed native artifacts"):
                mod.assess(out,out/"frozen-contract.json",binding)

    def test_modified_and_rehashed_csv_receipt_fails_original_binding(self):
        with tempfile.TemporaryDirectory() as folder:
            out,frozen,native=self.native_fixture(folder);binding=self.capture_fixture(out,native)
            self.assertTrue(mod.assess(out,out/"frozen-contract.json",binding)["passed"])
            self.rewrite(out/"mechanical_fields_0003.csv",lambda rows:rows[0].__setitem__("stress_zz",".2"))
            native["artifact_sha256"]["mechanical_fields_0003.csv"]=mod.sha(out/"mechanical_fields_0003.csv")
            (out/"native-execution.json").write_text(json.dumps(native))
            with self.assertRaisesRegex(ValueError,"independently retained original digest"):
                mod.assess(out,out/"frozen-contract.json",binding)

    def test_changed_frozen_tolerance_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            out,frozen=self.fields(folder);frozen["card"]["tolerances"]["stress_MPa"]=100.
            with self.assertRaises(ValueError):mod.assess_fields(out,frozen)

    def test_portable_runner_requires_unchanged_inputs_binary_and_six_solves(self):
        good=dict(returncode=0,binary_unchanged=True,inputs_unchanged=True,
                  binary_sha256=self.card["native_binary_sha256"])
        log="git commit167ee97da2\n"+"Solve Converged!\n"*6
        runner.validate_execution(good,log,self.card["native_binary_sha256"])
        for key,value in [("returncode",1),("binary_unchanged",False),("inputs_unchanged",False),
                          ("binary_sha256","0"*64)]:
            with self.subTest(key=key),self.assertRaises(RuntimeError):
                runner.validate_execution(dict(good,**{key:value}),log,self.card["native_binary_sha256"])
        for bad_log in [log.replace("167ee97da2","other"),log.replace("Solve Converged!\n","",1)]:
            with self.assertRaises(RuntimeError):
                runner.validate_execution(good,bad_log,self.card["native_binary_sha256"])

    def test_portable_runner_executes_checked_absolute_path_and_stops_on_input_drift(self):
        for mutate in [False,True]:
            with self.subTest(mutate=mutate),tempfile.TemporaryDirectory() as folder:
                rootfs=Path(folder)/"rootfs";binary=rootfs/"opt/moose/bin/moose-opt"
                binary.parent.mkdir(parents=True);binary.write_bytes(b"test-only mock runtime")
                output=Path(folder)/"new-run"
                def checksum(path):
                    return self.card["native_binary_sha256"] if Path(path).resolve()==binary.resolve() else mod.sha(path)
                def native(command,**kwargs):
                    self.assertEqual(command[-1],". /environment; exec /opt/moose/bin/moose-opt -i mechanical-birth.i")
                    kwargs["stdout"].write(b"git commit167ee97da2\n"+b"Solve Converged!\n"*6)
                    if mutate:(output/"mechanical-birth.i").write_text("changed after execution")
                    return SimpleNamespace(returncode=0)
                with patch.object(runner,"sha",side_effect=checksum), \
                     patch.object(runner.subprocess,"run",side_effect=native), \
                     patch.object(runner,"assess_fields",return_value={"passed":True}) as fields:
                    if mutate:
                        with self.assertRaises(RuntimeError):runner.reproduce(rootfs,output)
                        fields.assert_not_called()
                    else:
                        self.assertTrue(runner.reproduce(rootfs,output)["passed"])
                        fields.assert_called_once()


if __name__ == "__main__":
    unittest.main()
