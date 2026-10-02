import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location("station_credentials", Path(__file__).resolve().parents[1] / "deploy/openbao/station_credentials.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class StationCredentialTests(unittest.TestCase):


    def test_hf_start_requires_the_exact_live_launchagent_and_guard_deadline(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            guard_path = directory / "guard.py"
            guard_path.write_text("# non-secret test guard\n")
            manifest_path = directory / "station.json"
            ready_path = directory / "station.guard-ready.json"
            pins = {"manifest_sha256": "a" * 64, "vast_wrapper_sha256": "b" * 64}
            manifest = {"guard_ready_path": str(ready_path), "attempt_label": "station-example",
                        "image_ref": "image@sha256:" + "c" * 64, "created_epoch": 900,
                        "deadline_epoch": 3000, "guard_path": str(guard_path),
                        "guard_sha256": hashlib.sha256(guard_path.read_bytes()).hexdigest(),
                        "guard_service_name": "com.3dprinting993.station-example"}
            ready = {"armed": True, "pid": 123, "manifest_sha256": pins["manifest_sha256"],
                     "wrapper_sha256": pins["vast_wrapper_sha256"], "label": manifest["attempt_label"],
                     "image_ref": manifest["image_ref"], "deadline_epoch": 3000}
            ready_path.write_text(json.dumps(ready))
            good_process = SimpleNamespace(returncode=0, stdout=f"python3 {guard_path} {manifest_path}\n")
            good_service = SimpleNamespace(returncode=0, stdout="pid = 123\n")
            with mock.patch.object(module.os, "kill") as alive, mock.patch.object(module.subprocess, "run", side_effect=[good_process, good_service]):
                module.validate_guard(manifest, manifest_path, pins, 1000)
                alive.assert_called_once_with(123, 0)
            with mock.patch.object(module.os, "kill", side_effect=ProcessLookupError):
                with self.assertRaises(ValueError):
                    module.validate_guard(manifest, manifest_path, pins, 1000)
            for replies in ([SimpleNamespace(returncode=0, stdout="python3 unrelated.py\n")],
                            [good_process, SimpleNamespace(returncode=0, stdout="pid = 124\n")]):
                with mock.patch.object(module.os, "kill"), mock.patch.object(module.subprocess, "run", side_effect=replies):
                    with self.assertRaises(ValueError):
                        module.validate_guard(manifest, manifest_path, pins, 1000)
            with self.assertRaises(ValueError):
                module.validate_guard(manifest, manifest_path, pins, 1800)
            ready_path.write_text(json.dumps({**ready, "manifest_sha256": "d" * 64}))
            with self.assertRaises(ValueError):
                module.validate_guard(manifest, manifest_path, pins, 1000)

    def test_hf_start_requires_fresh_exact_metering_receipt(self):
        receipt = {"manifest_sha256": "a" * 64, "instance_id": 123,
                   "metering_active": True, "updated_epoch": 1000}
        module.validate_network_receipt(receipt, "a" * 64, 123, 1020)
        for sha, instance, now in [("b" * 64, 123, 1020), ("a" * 64, 124, 1020),
                                   ("a" * 64, 123, 1031), ("a" * 64, 123, 999)]:
            with self.assertRaises(ValueError):
                module.validate_network_receipt(receipt, sha, instance, now)





class StationPublisherTests(unittest.TestCase):
    token = "synthetic-controller-token-never-log"
    jit = "U1lOVEhFVElDLUpJVC1DT05GSUctTkVWRVItTE9H"
    remote = {"host": "build.invalid", "user": "builder", "jump": "jump.invalid", "identity": "/test/key"}

    def replies(self):
        return [(200, {"full_name": module.REPOSITORY, "permissions": {"admin": True}}),
                (200, {"total_count": 0, "runners": []}),
                (201, {"runner": {"id": 42, "name": module.RUNNER_NAME}, "encoded_jit_config": self.jit})]

    def invoke(self, operation, request):
        return module.github_dispatch(operation, self.token,
            {"SafeError": ValueError, "github_request": request}, self.remote)

    def test_fixed_repository_admin_check_and_operations(self):
        request = mock.Mock(return_value=self.replies()[0])
        with mock.patch("sys.stdout", new_callable=io.StringIO) as output:
            self.assertEqual(self.invoke(["station-publisher-check"], request), 0)
        self.assertEqual(json.loads(output.getvalue()), {"repository": module.REPOSITORY,
            "runner_admin": True, "registry_auth": "GitHub Actions job token"})
        request.assert_called_once_with(self.token, "/repos/cluster2600/porscheparts")
        for record in ({"full_name": module.REPOSITORY, "permissions": {"push": True}},
                       {"full_name": "other/repository", "permissions": {"admin": True}}):
            request = mock.Mock(return_value=(200, record))
            with self.subTest(record=record), self.assertRaisesRegex(ValueError, "administration access"):
                self.invoke(["station-publisher-start"], request)
            self.assertEqual(request.call_count, 1)
        request = mock.Mock()
        with self.assertRaisesRegex(ValueError, "invalid fixed"):
            self.invoke(["station-publisher-start", "other-host"], request)
        request.assert_not_called()

    def test_jit_start_binds_labels_host_and_one_job_without_secret_output(self):
        request = mock.Mock(side_effect=self.replies())
        with mock.patch.object(module.subprocess, "run", return_value=SimpleNamespace(
                returncode=0, stdout='{"started":true,"pid":123}', stderr="")) as run, \
                mock.patch("sys.stdout", new_callable=io.StringIO) as output:
            self.assertEqual(self.invoke(["station-publisher-start"], request), 0)
        request.assert_called_with(self.token, "/repos/cluster2600/porscheparts/actions/runners/generate-jitconfig",
            method="POST", payload={"name": module.RUNNER_NAME, "runner_group_id": 1,
                                    "labels": [module.RUNNER_LABEL], "work_folder": "_work"})
        self.assertEqual(run.call_args.kwargs["input"], self.jit)
        command = run.call_args.args[0]
        self.assertEqual(command[command.index('-J') + 1], self.remote['jump'])
        self.assertEqual(command[command.index('-i') + 1], self.remote['identity'])
        self.assertEqual(command[-2], "builder@build.invalid")
        for required in (module.RUNNER_DIR, "ACTIONS_RUNNER_INPUT_JITCONFIG", "5400", "start_new_session=True"):
            self.assertIn(required, command[-1])
        for secret in (self.token, self.jit):
            self.assertNotIn(secret, repr(command) + output.getvalue())
        value = json.loads(output.getvalue())
        self.assertEqual((value['runner_id'], value['pid'], value['maximum_jobs'], value['maximum_lifetime_seconds']),
                         (42, 123, 1, 5400))

    def test_existing_runner_inventory_and_remote_contract_fail_before_registration(self):
        for inventory in ({"total_count": 1, "runners": [{"name": module.RUNNER_NAME}]},
                          {"total_count": 101, "runners": []}):
            request = mock.Mock(side_effect=[self.replies()[0], (200, inventory)])
            with self.subTest(inventory=inventory), self.assertRaises(ValueError):
                self.invoke(["station-publisher-start"], request)
            self.assertEqual(request.call_count, 2)
        request = mock.Mock(side_effect=self.replies())
        with self.assertRaisesRegex(ValueError, "pinned station build host"):
            module.github_dispatch(["station-publisher-start"], self.token,
                {"SafeError": ValueError, "github_request": request}, {**self.remote, "extra": "not-allowed"})
        self.assertEqual(request.call_count, 2)

    def test_cleanup_deletes_only_unique_fixed_label_idle_offline_runner(self):
        runner = {"id": 21, "name": module.RUNNER_NAME, "status": "offline", "busy": False,
                  "labels": [{"name": module.RUNNER_LABEL}]}
        unrelated = {**runner, "id": 99, "name": "unrelated"}
        request = mock.Mock(side_effect=[self.replies()[0],
            (200, {"total_count": 2, "runners": [runner, unrelated]}), (204, {})])
        with mock.patch("sys.stdout", new_callable=io.StringIO) as output:
            self.assertEqual(self.invoke(["station-publisher-cleanup"], request), 0)
        self.assertEqual(json.loads(output.getvalue()), {"removed_runner_ids": [21]})
        request.assert_called_with(self.token, "/repos/cluster2600/porscheparts/actions/runners/21", method="DELETE")
        for records in ([{**runner, "status": "online"}], [{**runner, "busy": True}],
                        [{**runner, "labels": [{"name": "wrong-label"}]}], [runner, runner]):
            request = mock.Mock(side_effect=[self.replies()[0],
                (200, {"total_count": len(records), "runners": records})])
            with self.subTest(records=records), self.assertRaisesRegex(ValueError, "unique idle offline"):
                self.invoke(["station-publisher-cleanup"], request)
            self.assertEqual(request.call_count, 2)
        request = mock.Mock(side_effect=[self.replies()[0], (200, {"total_count": 1, "runners": [unrelated]})])
        with mock.patch("sys.stdout", new_callable=io.StringIO) as output:
            self.assertEqual(self.invoke(["station-publisher-cleanup"], request), 0)
        self.assertEqual(json.loads(output.getvalue()), {"removed_runner_ids": []})
        self.assertEqual(request.call_count, 2)

    def test_invalid_jit_callback_never_reaches_ssh(self):
        valid = self.replies()[2][1]
        for changed in ({**valid, "runner": {"id": 42, "name": "other-runner"}},
                        {**valid, "runner": {"id": 42, "name": module.RUNNER_NAME, "ephemeral": False}},
                        {**valid, "runner": {"id": True, "name": module.RUNNER_NAME}},
                        {**valid, "encoded_jit_config": "bad configuration"}):
            request = mock.Mock(side_effect=self.replies()[:2] + [(201, changed)])
            with self.subTest(changed=changed), mock.patch.object(module.subprocess, "run") as run, \
                    self.assertRaisesRegex(ValueError, "fixed ephemeral"):
                self.invoke(["station-publisher-start"], request)
            run.assert_not_called()

    def test_ssh_startup_failures_withhold_authentication_bearing_output(self):
        outcomes = [SimpleNamespace(returncode=1, stdout=self.jit, stderr=self.token),
                    SimpleNamespace(returncode=0, stdout=self.jit, stderr=self.token),
                    module.subprocess.TimeoutExpired("ssh", 30, output=self.jit, stderr=self.token)]
        for outcome in outcomes:
            request = mock.Mock(side_effect=self.replies())
            kwargs = {"side_effect": outcome} if isinstance(outcome, Exception) else {"return_value": outcome}
            with self.subTest(outcome=type(outcome).__name__), \
                    mock.patch.object(module.subprocess, "run", **kwargs), \
                    mock.patch("sys.stdout", new_callable=io.StringIO) as output:
                with self.assertRaisesRegex(ValueError, "authentication logs withheld") as error:
                    self.invoke(["station-publisher-start"], request)
            for secret in (self.token, self.jit):
                self.assertNotIn(secret, str(error.exception) + output.getvalue())

    def test_status_filters_runner_workflow_and_private_fields(self):
        runner = {"id": 42, "name": module.RUNNER_NAME, "status": "online", "busy": False, "private": self.jit}
        run = {"id": 84, "name": "publication", "path": ".github/workflows/picogk-station-publish.yml",
               "status": "completed", "conclusion": "success", "head_sha": "a" * 40, "private": self.token}
        request = mock.Mock(side_effect=[self.replies()[0],
            (200, {"total_count": 2, "runners": [runner, {"name": "unrelated", "private": self.jit}]}),
            (200, {"workflow_runs": [run, {"path": "unrelated", "private": self.token}]})])
        with mock.patch("sys.stdout", new_callable=io.StringIO) as output, \
                mock.patch.object(module.subprocess, "run") as process:
            self.assertEqual(self.invoke(["station-publisher-status"], request), 0)
        value = json.loads(output.getvalue())
        self.assertEqual([r['id'] for r in value['runners']], [42])
        self.assertEqual([r['id'] for r in value['runs']], [84])
        self.assertIn('branch=codex%2Fpicogk-vast-station', request.call_args.args[1])
        for secret in (self.token, self.jit):
            self.assertNotIn(secret, output.getvalue())
        process.assert_not_called()

    def test_rendered_hook_pins_module_and_host_config_and_preserves_legacy(self):
        source = ('def invoke(operation, token):\n    if True:\n        if True:\n'
                  '            if operation == ["--auth-check"]:\n                return "legacy"\n'
                  '            return "unhandled"\n')
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            hook = root / 'hook.py'
            hook.write_text('def github_dispatch(operation, token, wrapper, remote):\n    return remote["host"]\n')
            config = root / 'remote.json'
            config.write_text(json.dumps(self.remote))
            rendered = module.render_github_hook(source, hook, config)
            namespace = {'Path': Path, 'json': json, 'SafeError': ValueError}
            exec(compile(rendered, '<unit-test-hook>', 'exec'), namespace)
            self.assertEqual(namespace['invoke'](['--auth-check'], self.token), 'legacy')
            self.assertEqual(namespace['invoke'](['station-publisher-check'], self.token), self.remote['host'])
            for path in (config, hook):
                original = path.read_bytes()
                path.write_bytes(original + b' ')
                with self.subTest(path=path.name), self.assertRaisesRegex(ValueError, 'fixed build host changed'):
                    namespace['invoke'](['station-publisher-check'], self.token)
                path.write_bytes(original)


if __name__ == "__main__":
    unittest.main()
