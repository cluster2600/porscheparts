"""Prepared stdlib source/authority and mocked-owned-process checks; no MOOSE execution."""

import hashlib
import importlib.util
import json
from pathlib import Path
import signal
import tempfile
from types import SimpleNamespace
from unittest import TestCase, main, mock

SOURCE = Path(__file__).with_name("run_mac.py")
SOURCE_SHA256 = "fde48211a11066c8406076621b5cd1c2898e0353956a4e6ec879754e7452c9d3"
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_SHA256
spec = importlib.util.spec_from_file_location("mac_thermal_candidate", SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)  # stdlib-only top level; no controller main or native import


class FakeProcess:
    pid = 700001

    def __init__(self):
        self.returncode = None
        self.waited = 0

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        self.waited += 1
        self.returncode = 0 if self.returncode is None else self.returncode
        return self.returncode


class Guards(TestCase):
    def test_fixed_commands_and_registry_authority(self):
        jobs = module.commands("readiness")
        self.assertEqual([argv[-1] for _, argv in jobs], ["--help", "--version", "--registry"])
        self.assertTrue(all("-i" not in argv and "-skip_petscrc" in argv and "--n-threads=1" in argv
                            for _, argv in jobs))
        self.assertEqual(len(module.commands("coupon")), 1)
        self.assertEqual(module.commands("coupon")[0][1][-3:], ["-i", "thermal-birth.i", "time-level.i"])
        text = "Label\tType\tName\tClass\tFile\n" + "".join(
            f"test\tobject\t{name}\t{name}\tpublic_source.C\n" for name in module.FEATURES)
        self.assertEqual(module.registry_features(text), {name: True for name in module.FEATURES})
        with self.assertRaises(ValueError): module.registry_features(" ".join(module.FEATURES))
        with self.assertRaises(ValueError): module.commands("anything_else")

    def test_held_or_cross_stage_refusal_before_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp).resolve() / "actual.json"
            for update in ({"native_launch_authorized": False}, {"coupon_solve_authorized": True}):
                c = dict(schema="962-macos-cp1-thermal-birth-stage-actual/v1", stage="readiness",
                         root_and_peer_review_complete=True, native_launch_authorized=True,
                         coupon_solve_authorized=False, head_authorized=False, manufacturing_authorized=False)
                c.update(update)
                path.write_text(json.dumps(c))
                with mock.patch.object(module, "runtime_unchanged", side_effect=AssertionError("Runtime reached")):
                    with self.assertRaises(ValueError): module.checked_contract("readiness", path, module.sha(path))

    def fake_coupon(self, stop):
        root = tempfile.TemporaryDirectory(dir=module.ENGINEERING)
        self.addCleanup(root.cleanup)
        base = Path(root.name).resolve()
        output = base / "output"
        contract = base / "actual.json"
        contract.write_text("{}\n")
        case = base / "case"
        case.mkdir()
        for name in module.CASE_FILES: (case / name).write_text("synthetic only\n")
        card = case / "card.json"
        card.write_text("{}\n")
        physics = case / "case-contract.json"
        physics.write_text('{"synthetic_physics_reference":true}\n')
        c = dict(input_sha256={}, runtime_sha256s={"bin/combined-opt": "0"*64}, runtime_symlinks={},
                 resources=dict(wall_seconds=10, sampled_RSS_stop_bytes=1024 if stop else 1024**3,
                                sampled_output_stop_bytes=16 * 1024**2))
        process = FakeProcess()
        timer = SimpleNamespace(start=lambda: None, cancel=lambda: None, daemon=False)
        def kill(pid, how):
            self.assertEqual((pid, how), (process.pid, signal.SIGKILL))
            process.returncode = -9
        with mock.patch.object(module, "CASE", case), mock.patch.object(module, "CARD", card), \
             mock.patch.object(module, "PHYSICS", physics), \
             mock.patch.object(module, "checked_contract", return_value=(c, output)), \
             mock.patch.object(module, "check_pins"), mock.patch.object(module, "runtime_unchanged", return_value=True), \
             mock.patch.object(module.threading, "Timer", return_value=timer), \
             mock.patch.object(module.subprocess, "Popen", return_value=process) as popen, \
             mock.patch.object(module.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout="2\n")), \
             mock.patch.object(module.os, "killpg", side_effect=kill), \
             mock.patch.object(module.signal, "signal") as handler:
            if stop:
                with self.assertRaises(ValueError): module.run("coupon", contract, module.sha(contract))
            else:
                module.run("coupon", contract, module.sha(contract))
            self.assertEqual(popen.call_count, 1)
            self.assertEqual(popen.call_args.kwargs["env"], module.ENVIRONMENT)
            self.assertNotIn("HOME", popen.call_args.kwargs["env"])
            self.assertNotIn("CODEX_HOME", popen.call_args.kwargs["env"])
            self.assertTrue(popen.call_args.kwargs["start_new_session"])
            self.assertGreater(process.waited, 0)
            self.assertEqual(handler.call_args.args[0], signal.SIGTERM)
        return json.loads((output / "native-execution.json").read_text())

    def test_owned_success_receipt_preserves_assessor_keys(self):
        r = self.fake_coupon(False)
        for key in ("contract_sha256", "native_execution_completed", "returncode", "process_reaped",
                    "controller_error", "inputs_unchanged", "binary_and_runtime_unchanged"):
            self.assertIn(key, r)
        self.assertTrue(r["native_execution_completed"] and r["process_reaped"])
        self.assertEqual(r["level"], 2)
        self.assertEqual(r["binary_sha256"], "0"*64)
        self.assertTrue(r["binary_unchanged"])
        self.assertNotEqual(r["physics_contract_sha256"], r["actual_contract_sha256"])
        self.assertEqual(r["actual_contract_sha256"], r["contract_sha256"])
        self.assertTrue(all(Path(k).name == k for k in r["artifact_sha256"]))
        self.assertTrue(any(k.startswith("source-snapshots/") for k in r["complete_artifact_sha256"]))
        self.assertEqual(r["artifact_sha256"], {k:v for k,v in r["complete_artifact_sha256"].items() if Path(k).name==k})
        self.assertFalse(r["passed"] or r["independent_assessment_performed"] or r["hard_OS_CPU_or_memory_quota"])

    def test_sampled_stop_kills_waits_and_retains_refusal(self):
        r = self.fake_coupon(True)
        self.assertEqual((r["returncode"], r["stop_reason"]), (-9, "sampled_RSS_stop"))
        self.assertTrue(r["process_reaped"])
        self.assertFalse(r["native_execution_completed"])


    def test_exact_seven_variable_tcp_environment_and_no_inheritance(self):
        import ast
        expected = {"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C", "OMP_NUM_THREADS": "1",
                    "OPENBLAS_NUM_THREADS": "1", "VECLIB_MAXIMUM_THREADS": "1", "FI_PROVIDER": "tcp"}
        self.assertEqual(module.ENVIRONMENT, expected)
        self.assertEqual(len(module.ENVIRONMENT), 7)
        tree = ast.parse(SOURCE.read_text())
        popen = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name)
                 and n.func.value.id == "subprocess" and n.func.attr == "Popen"]
        self.assertEqual(len(popen), 1)
        environment = next(k.value for k in popen[0].keywords if k.arg == "env")
        self.assertIsInstance(environment, ast.Name)
        self.assertEqual(environment.id, "ENVIRONMENT")
        self.assertFalse(any(isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
                             and n.value.id == "os" and n.attr == "environ" for n in ast.walk(tree)))


    def test_current19_old18_registry_join_and_wrong_runtime_refusal(self):
        bindings = json.loads((module.ENGINEERING / "cp1-assumed-thermal-birth-runtime-bindings-001/bindings.json").read_text())
        ready_path = module.ENGINEERING / "moose-local-macos-readiness-003/readiness.json"
        registry_path = module.ENGINEERING / "moose-local-macos-readiness-003/registry.log"
        with tempfile.TemporaryDirectory(dir=module.ENGINEERING) as tmp:
            base = Path(tmp).resolve()
            held = base / "held.json"
            resources = dict(wall_seconds=100, sampled_RSS_stop_bytes=2*1024**3, sampled_output_stop_bytes=32*1024**2)
            held.write_text(json.dumps(dict(input_sha256={}, runtime_sha256s=bindings['runtime_sha256s'], runtime_symlinks=bindings['runtime_symlinks'], coupon_resources=resources)))
            installation = base / 'installation.json'
            installation.write_text('{}\n')
            pins = {str(p.relative_to(module.ROOT)):module.sha(p) for p in [held,installation,ready_path,registry_path]}
            c = dict(schema='962-macos-cp1-thermal-birth-stage-actual/v1', stage='coupon', root_and_peer_review_complete=True,
                     native_launch_authorized=True, coupon_solve_authorized=True, head_authorized=False, manufacturing_authorized=False,
                     engineering_accepted=False, physics_qualified=False, material_qualified=False, process_calibrated=False,
                     automatic_retry=False, input_sha256=pins, runtime_sha256s=bindings['runtime_sha256s'], runtime_symlinks=bindings['runtime_symlinks'],
                     installation_result_peer=str(installation.relative_to(module.ROOT)), installation_receipt=str(installation.relative_to(module.ROOT)),
                     resources=resources, readiness_receipt=str(ready_path.relative_to(module.ROOT)), readiness_result_peer=str(installation.relative_to(module.ROOT)),
                     readiness_registry=str(registry_path.relative_to(module.ROOT)), output=str(base/'output'))
            path=base/'actual.json'
            with mock.patch.object(module,'HELD',held), mock.patch.object(module,'ENGINEERING',base), \
                 mock.patch.object(module,'runtime_unchanged',return_value=True), mock.patch.object(module.os,'access',return_value=True):
                path.write_text(json.dumps(c))
                observed,output=module.checked_contract('coupon',path,module.sha(path))
                self.assertEqual(output,base/'output')
                self.assertFalse(output.exists())
                for mode in ['missing_heat','changed_heat','missing_link','resource_change']:
                    bad=json.loads(json.dumps(c))
                    if mode=='missing_heat':bad['runtime_sha256s'].pop('lib/combined/libheat_transfer-opt.0.dylib')
                    if mode=='changed_heat':bad['runtime_sha256s']['lib/combined/libheat_transfer-opt.0.dylib']='f'*64
                    if mode=='missing_link':bad['runtime_symlinks'].pop('bin/moose-opt')
                    if mode=='resource_change':bad['resources']['wall_seconds']=101
                    path.write_text(json.dumps(bad))
                    with self.assertRaises(ValueError):module.checked_contract('coupon',path,module.sha(path))


if __name__ == "__main__":
    main()
