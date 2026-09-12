"""Tests purs et processus Python factices; aucun Docker/SSH/solveur."""
import copy
import io
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'twins/m64-cylinder-head/source/f58-quadrature'))
import run_quadrature as r
from quadrature_worker import Guard
sys.path.pop(0)


class Tests(unittest.TestCase):
    def test_paths(self):
        for path in ('relative', '/var/tmp/x/../a', '/var/tmp/x,readonly', '/var/tmp/x\nx', '/var/tmp/x x'):
            with self.assertRaises(ValueError): r.safe(Path(path))
        with tempfile.TemporaryDirectory() as d:
            p = Path(d).resolve(); (p/'link').symlink_to(p)
            with self.assertRaises(ValueError): r.safe(p/'link'/'x')
    def test_ownership(self):
        row = {'Id': 'a'*64, 'Name': '/test', 'Image': r.IMAGE, 'Config': {'Labels': {r.LABEL: 'token'}}}
        self.assertTrue(r.owned(row, 'test', 'token', 'a'*64))
        for key, value in [('Id', 'a'*12), ('Name', '/other'), ('Image', 'wrong')]:
            changed = copy.deepcopy(row); changed[key] = value
            self.assertFalse(r.owned(changed, 'test', 'token', 'a'*64))
        self.assertFalse(r.owned(row, 'test', 'other', 'a'*64))
    def test_budget(self):
        with patch.object(r.time, 'monotonic', return_value=575):
            with self.assertRaises(ValueError): r.left(0, 5)
            self.assertEqual(r.left(0, 30, True), 25)
    def test_bounded_writer_and_timeout(self):
        out = io.BytesIO()
        with self.assertRaisesRegex(ValueError, 'log_limit'):
            r.pump([sys.executable, '-c', 'print("x"*100)'], out, time.monotonic()+2, 20)
        self.assertEqual(len(out.getvalue()), 20)
        with self.assertRaisesRegex(ValueError, 'wall_deadline'):
            r.pump([sys.executable, '-c', 'import time; time.sleep(2)'], io.BytesIO(), time.monotonic()+.05, 20)
    def test_grid_and_thermal(self):
        g = Guard(); g.line('Mesh OK.')
        for i in range(1, 1601):
            t = i*2.5e-8; g.line(f'Time = {t:.14g}'); g.line(f'F58_BALANCE {t:.14g} 2.5e-8 300 0 0 0 0 0 0 0')
        self.assertEqual((g.steps, g.balances), (1600, 1600))
        for text in ('Time = 0.000040025', 'Solving for p_rgh,', 'FOAM FATAL ERROR', 'F58_BALANCE nan'):
            with self.assertRaises(ValueError): g.line(text)
    def test_command(self):
        cmd = r.command(Path('/var/tmp/m64-f58-quad.abcdef'), 'safe', 'token')
        for flag, value in [('--cpus', '2'), ('--memory', '4g'), ('--memory-swap', '4g'), ('--network', 'none')]:
            self.assertEqual(cmd[cmd.index(flag)+1], value)
        self.assertEqual(sum('/input/q' in s and ',readonly' in s for s in cmd), 2)
        self.assertNotIn('blockMesh', ' '.join(cmd)); self.assertNotIn('--rm', cmd)
    def test_resources_and_mounts(self):
        packet = Path('/var/tmp/m64-f58-quad.abcdef')
        h = {'NanoCpus': 2000000000, 'Memory': 4*1024**3, 'MemorySwap': 4*1024**3, 'NetworkMode': 'none',
             'ReadonlyRootfs': True, 'CapDrop': ['ALL'], 'PidsLimit': 128, 'SecurityOpt': ['no-new-privileges:true'],
             'LogConfig': {'Type': 'none'}, 'Tmpfs': {'/work': 'rw,noexec,nosuid,nodev,size=1g,mode=1777',
             '/tmp': 'rw,noexec,nosuid,nodev,size=64m,mode=1777'}}
        row = {'HostConfig': h, 'Config': {'User': f'{os.getuid()}:{os.getgid()}'}, 'Mounts':
               [{'Type': 'bind', 'Source': s, 'Destination': d, 'RW': rw} for s, (d, rw) in r.mounts(packet).items()]}
        self.assertTrue(r.resources(row, packet))
        for key, value in [('MemorySwap', -1), ('NanoCpus', 4000000000), ('NetworkMode', 'bridge'), ('ReadonlyRootfs', False)]:
            bad = copy.deepcopy(row); bad['HostConfig'][key] = value
            self.assertFalse(r.resources(bad, packet))
        bad = copy.deepcopy(row); bad['Mounts'][0]['RW'] = True
        self.assertFalse(r.resources(bad, packet))
    def test_hash_and_receipt_limit(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d).resolve()/'receipt.json'; r.save(p, {'a': 1})
            before = r.sha(p); self.assertEqual(len(before), 64)
            with p.open('ab') as out: out.write(b' ')
            self.assertNotEqual(r.sha(p), before)
            with self.assertRaisesRegex(ValueError, 'receipt_exceeds'):
                r.save(p.with_name('big.json'), {'data': 'x'*r.MIB})
    def test_source_links(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve(); (root/'lnInclude').mkdir(); source = root/'Foo.H'
            with source.open('x') as f: f.write('source')
            link = root/'lnInclude/Foo.H'; link.symlink_to('../Foo.H')
            expected = {'lnInclude/Foo.H': {'target': '../Foo.H', 'resolved': 'Foo.H', 'sha256': r.sha(source)}}
            self.assertEqual(r.inventory(root, True, expected), {'Foo.H': r.sha(source)})
            with self.assertRaisesRegex(ValueError, 'source_links_pin'): r.inventory(root, True, {})
            for target in (str(source), '../../outside.H', '../lnInclude/Foo.H'):
                link.unlink(); link.symlink_to(target)
                with self.assertRaises(ValueError): r.inventory(root, True, expected)


if __name__ == '__main__': unittest.main()
