"""Small stdlib-only callback/identity tests: never Docker or a real mesh."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('private_h2_static', HERE / 'run.py')
r = importlib.util.module_from_spec(spec); spec.loader.exec_module(r)


def fixture(root, success=True, cancelled=False):
    case = root / 'mesh'; case.mkdir(); execution = root / 'execution'; execution.mkdir()
    name = 'combined-rigid-static'; deck = b'*STEP\n*STATIC,SOLVER=SPOOLES\n*END STEP\n'
    (case / (name + '.inp')).write_bytes(deck); (execution / 'prepared-deck.inp').write_bytes(deck)
    plan = dict(case_name=name, prepared_deck_sha256=hashlib.sha256(deck).hexdigest(),
                container_name='new-owned-case', ownership_token='unique-token', files_sha256={},
                mesh_files_sha256={n:'a'*64 for n in ['mesh.inp','mesh.npz','mesh.json']}, helper_sha256='b'*64)
    calls = []
    def supervise(owned, backend, started):
        calls.append(owned)
        return dict(status='solver_executed_no_numeric_admission' if success else 'cleanup_unconfirmed_no_admission',
                    actual_container_exit_code=0, container_removed=success, input_hashes_unchanged=True,
                    within_global_budget=True, container_id='c'*64)
    helper = SimpleNamespace(supervise=supervise, HERE=None)
    backend = SimpleNamespace(cancelled=cancelled)
    return case, execution, plan, helper, backend, calls


class Checks(unittest.TestCase):
    def test_prepare_callback_preserves_deck_and_stops(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = Path(tmp)/'mesh'; case.mkdir(); execution=Path(tmp)/'execution'; execution.mkdir()
            name='combined-rigid-static';(case/(name+'.inp')).write_bytes(b'original deck\n'); record={}
            callback=r.prepare_execute(case,execution,name,record)
            with self.assertRaises(r.DeckPrepared):callback(case,name)
            self.assertFalse((case/(name+'.inp')).exists())
            self.assertEqual((execution/'prepared-deck.inp').read_bytes(),b'original deck\n')
            self.assertEqual(record['deck_sha256'],r.sha(execution/'prepared-deck.inp'))

    def test_owned_callback_exact_resources_and_private_HERE(self):
        with tempfile.TemporaryDirectory() as tmp:
            case,execution,plan,helper,backend,calls=fixture(Path(tmp))
            with patch.object(r.signal,'signal'),patch.object(r.signal,'setitimer'):
                callback=r.make_execute(helper,backend,plan,case,execution,time.monotonic())
                callback(case,plan['case_name'])
                with self.assertRaisesRegex(ValueError,'repeated'):callback(case,plan['case_name'])
            owned=calls[0]
            self.assertEqual(owned['wall_budget_seconds'],1800);self.assertEqual(owned['cleanup_reserve_seconds'],60)
            self.assertEqual(owned['image'],r.IMAGE);self.assertEqual(owned['binary_sha256'],r.BINARY)
            self.assertEqual(owned['container_command'],['--signal=TERM','--kill-after=10s','1680s','/usr/bin/ccx','-i',plan['case_name']])
            self.assertEqual(helper.HERE,execution)
            self.assertEqual(json.loads((case/'runtime.json').read_text())['container_name'],'new-owned-case')

    def test_callback_refuses_drifted_deck_before_supervise(self):
        with tempfile.TemporaryDirectory() as tmp:
            case,execution,plan,helper,backend,calls=fixture(Path(tmp));(case/(plan['case_name']+'.inp')).write_text('changed')
            callback=r.make_execute(helper,backend,plan,case,execution,time.monotonic())
            with self.assertRaisesRegex(ValueError,'deck differs'):callback(case,plan['case_name'])
            self.assertEqual(calls,[])

    def test_unconfirmed_cleanup_cannot_publish_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            case,execution,plan,helper,backend,calls=fixture(Path(tmp),success=False)
            callback=r.make_execute(helper,backend,plan,case,execution,time.monotonic())
            with self.assertRaises(ValueError):callback(case,plan['case_name'])
            self.assertTrue((execution/'native-receipt.json').exists());self.assertFalse((case/'runtime.json').exists())

    def test_cancellation_after_owned_cleanup_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            case,execution,plan,helper,backend,calls=fixture(Path(tmp),cancelled=True)
            callback=r.make_execute(helper,backend,plan,case,execution,time.monotonic())
            with self.assertRaisesRegex(ValueError,'Cancellation'):callback(case,plan['case_name'])
            self.assertFalse((case/'runtime.json').exists())

    def test_wrong_case_is_rejected_before_io(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'plan.json';plan={'launch_ready':True,'case_key':'unknown'};p.write_text(json.dumps(plan))
            with self.assertRaisesRegex(ValueError,'fixed case'):r.verified(plan,r.sha(p),p)

    def test_copies_are_exact_and_exclusive(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=Path(tmp)/'a';b=Path(tmp)/'b';a.write_bytes(b'original\x00bytes')
            r.copy_exact(a,b,r.sha(a));self.assertEqual(a.read_bytes(),b.read_bytes())
            with self.assertRaises(FileExistsError):r.copy_exact(a,b,r.sha(a))


if __name__=='__main__':unittest.main()
