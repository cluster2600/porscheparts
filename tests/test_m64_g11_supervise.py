"""Durable collection without paid APIs, real SSH or a launched compute job."""
import base64
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/fourvalve'))
import g11_supervise as supervisor
import test_m64_g11_collect as fixtures


class SupervisorChecks(unittest.TestCase):
    def fixture(self, root):
        root = root.resolve()
        now = int(time.time())
        manifest = dict(profile='picogk-m64-v1', attempt_label='3dprinting993-picogk-m64-'+'a'*20,
                        image_ref='ghcr.io/cluster2600/3dprinting993-picogk-m64@sha256:'+'b'*64,
                        job_id='picogk-g11-fixture', created_epoch=now-10, deadline_epoch=now+7200, budget_usd=3,
                        image_download_gb=10, max_input_gb=2, max_output_gb=2)
        path = root/'manifest.json'; path.write_text(json.dumps(manifest))
        config = root/'ssh.conf'
        config.write_text('Host g11\nHostName example.invalid\nPort 2222\nUser root\n'
                          'IdentityFile /fake/key\nIdentitiesOnly yes\nBatchMode yes\nForwardAgent no\n'
                          'StrictHostKeyChecking yes\nHostKeyAlias f41-42\nUserKnownHostsFile /fake/known-hosts\n')
        args = SimpleNamespace(manifest=path, ssh_config=config, instance_id=42, producer_group=123, output=root/'local',
                               log=root/'local/controller.jsonl', producer_deadline=now+3600,
                               collect_deadline=now+6000, reserve_seconds=1800)
        instance = dict(id=42, label=manifest['attempt_label'], image=manifest['image_ref'])
        source, case = fixtures.CollectionChecks().fixture(root)
        data = b'{"complete":true}\n'; (case/'result.json').write_bytes(data)
        case.rename(case.with_name('centre_w10-2-attempt1'))
        archive = root/'fixture.tar.xz'
        receipt = supervisor.collect.pack(source, archive, xz_preset=1)
        receipt['producer'] = dict(process_group=123, instance_id=42, job_id=manifest['job_id'],
                                   manifest_sha256=supervisor.fingerprint(path.read_bytes()),
                                   producer_deadline=args.producer_deadline, exit_code=0)
        name = 'results/centre_w10-2-attempt1/result.json'
        item = dict(path=name, sha256=hashlib.sha256(data).hexdigest(), data=base64.b64encode(data).decode())
        return args, instance, item, receipt, archive.read_bytes()

    def test_cold_collection_and_restart_use_existing_snapshot_and_archive(self):
        with tempfile.TemporaryDirectory() as folder:
            args, instance, item, receipt, archive = self.fixture(Path(folder)); downloaded = []
            def transport(config, command, timeout, limit, sink=None):
                if sink is not None:
                    downloaded.append(True); sink.write(archive); return b''
                mode, _, known = command.rsplit(' ', 3)[1:]
                known = json.loads(base64.b64decode(known))['known']
                value = receipt if mode == 'pack' else dict(terminal=receipt['producer'],
                            files=[] if item['path'] in known else [item], more=False)
                return json.dumps(value).encode()
            with patch.object(supervisor.guard, 'wrapper_call', return_value=instance) as wrapper, patch.object(supervisor, 'ssh', side_effect=transport):
                self.assertEqual(supervisor.run(args), 0)
                self.assertEqual(supervisor.run(args), 0)
                self.assertTrue(all(c.args == ('show', '42') for c in wrapper.call_args_list))
            self.assertEqual(len(downloaded), 1)
            self.assertTrue(json.loads((args.output/'verified.json').read_text())['collection_verified'])
            self.assertEqual((args.output/'snapshots'/item['path']).read_bytes(), base64.b64decode(item['data']))
            charges = sum(json.loads(line).get('metadata_charge_delta',0) for line in args.log.read_text().splitlines())
            self.assertGreater(charges, 0); self.assertLess(charges, supervisor.META_LIMIT)

    def test_network_corruption_foreign_identity_and_exhausted_budget_fail_closed(self):
        for failure in ('network', 'corrupt', 'foreign', 'budget', 'archive_budget', 'deadline', 'unclean'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as folder:
                args, instance, item, receipt, archive = self.fixture(Path(folder))
                if failure == 'foreign':
                    instance['id'] = 99; instance['label'] = 'another-project'
                if failure == 'budget':
                    args.output.mkdir()
                    args.log.write_text((json.dumps({'metadata_charge_delta':supervisor.RESPONSE_LIMIT})+'\n')*30)
                if failure == 'archive_budget':
                    args.output.mkdir()
                    args.log.write_text(json.dumps({'archive_charge_delta':supervisor.collect.LIMIT})+'\n')
                if failure == 'deadline':
                    args.collect_deadline = int(time.time())+10
                    args.producer_deadline = int(time.time())-10000
                def transport(config, command, timeout, limit, sink=None):
                    if sink is not None:
                        sink.write(b'X'+archive[1:]); return b''
                    mode = command.rsplit(' ', 3)[1]
                    if mode == 'pack' and failure == 'network':
                        raise TimeoutError('fixture network outage')
                    return json.dumps(receipt if mode == 'pack' else dict(terminal=dict(receipt['producer'],exit_code=1 if failure=='unclean' else 0), files=[item], more=False)).encode()
                with patch.object(supervisor.guard, 'wrapper_call', return_value=instance), patch.object(supervisor, 'ssh', side_effect=transport) as network:
                    self.assertEqual(supervisor.run(args), 1)
                    if failure in ('foreign','budget'):
                        network.assert_not_called()
                    else:
                        self.assertTrue((args.output/'snapshots'/item['path']).exists())
                self.assertFalse((args.output/'verified.json').exists())
                self.assertFalse((args.output/'collection.tar.xz').exists())

    def test_transport_byte_limit_and_timeout_kill_local_ssh_process(self):
        original = supervisor.subprocess.Popen
        for program, limit, timeout, error in [('import sys;sys.stdout.buffer.write(b"x"*10000)', 100, 2, ValueError),
                                                ('import time;time.sleep(5)', 100, .05, TimeoutError)]:
            with patch.object(supervisor.subprocess, 'Popen', side_effect=lambda command, **kwargs: original([sys.executable, '-c', program], **kwargs)):
                with self.assertRaises(error):
                    supervisor.ssh(Path('/unused'), 'not-executed', timeout, limit)
        # A real local detached producer exercises the remote marker parser, not a fake SSH response.
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            source = root/'twins/m64-cylinder-head/source/fourvalve/g11_collect.py'
            source.parent.mkdir(parents=True)
            source.write_bytes(Path(supervisor.collect.__file__).read_bytes())
            marker = root/'producer-exit.json'
            context = dict(instance_id=42, job_id='local-smoke', manifest_sha256='a'*64, producer_deadline=int(time.time())+60)
            program = ('import json,os,pathlib,sys;data=json.loads(sys.argv[2]);'
                       'data.update(process_group=os.getpgrp(),exit_code=0);'
                       'pathlib.Path(sys.argv[1]).write_text(json.dumps(data)+"\\n")')
            child = original([sys.executable, '-c', program, str(marker), json.dumps(context)], start_new_session=True)
            self.assertEqual(child.wait(timeout=5), 0)
            context['process_group'] = child.pid
            remote = supervisor.REMOTE.replace("root=pathlib.Path('/workspace/m64-g11')", 'root=pathlib.Path('+repr(str(root))+')')
            def inspect(expected, mode='snapshot'):
                payload = base64.b64encode(json.dumps({'expected_terminal':expected,'known':{}}).encode()).decode()
                return supervisor.subprocess.run([sys.executable, '-c', remote, mode, supervisor.fingerprint(source.read_bytes()), payload], capture_output=True, timeout=5)
            completed = inspect(context)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(json.loads(completed.stdout)['terminal']['process_group'], child.pid)
            self.assertNotEqual(inspect(dict(context, manifest_sha256='b'*64)).returncode, 0)
            (root/'supervised-collection.json').write_text(json.dumps({'producer':dict(context,job_id='old-job',exit_code=0)})+'\n')
            self.assertNotEqual(inspect(context, 'pack').returncode, 0)


if __name__ == '__main__':
    unittest.main()
