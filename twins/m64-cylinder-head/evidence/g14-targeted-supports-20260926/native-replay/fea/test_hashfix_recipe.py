"""Focused tests only: no build, mesh, real CCX or CG."""
import argparse
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch

import caps_hashfix_retry as retry
r,m,c=retry.r,retry.m,retry.c


class HashfixRecipe(unittest.TestCase):
    def test_direction_transform_exact_g8_deck_and_nodal_loads(self):
        points={n:(n/7.,n/9.,12.) for n in range(1,11)}
        elements=[(1,list(range(1,11)))];support=[1,2]
        weights={'intake':{3:.25,4:.75},'exhaust':{9:1.}}
        forces={'intake':1234.56789012345,'exhaust':987.65432109876}
        with tempfile.TemporaryDirectory() as d:
            case=Path(d)
            for name,direction in c.g11.DIRECTIONS:m.write_deck(case,points,elements,support,weights,forces,direction,name)
            x=(case/'x.inp').read_text();z=retry.minus_z(x)
            self.assertEqual(z,(case/'minus_z.inp').read_text())
            self.assertEqual(x.split('*CLOAD\n')[0],z.split('*CLOAD\n')[0])
            px,fx,sx=c.g9.deck(x);pz,fz,sz=c.g9.deck(z)
            self.assertEqual(set(px),set(pz));self.assertTrue(all(c.np.array_equal(px[n],pz[n]) for n in px));self.assertEqual(sx,sz)
            self.assertEqual(fz,{(n,3):-value for (n,d),value in fx.items()})

    def test_actual_failed_deck_transform_never_remeshes(self):
        text=(retry.OLD/'native-mac-g14-caps-1.5/x.inp').read_text()
        self.assertEqual(c.g8.sha256(retry.OLD/'native-mac-g14-caps-1.5/x.inp'),retry.X_SHA)
        z=retry.minus_z(text)
        self.assertEqual(text.split('*CLOAD\n')[0],z.split('*CLOAD\n')[0])
        px,fx,sx=c.g9.deck(text);pz,fz,sz=c.g9.deck(z)
        self.assertEqual(len(px),380799);self.assertEqual(set(px),set(pz))
        self.assertTrue(all(c.np.array_equal(px[n],pz[n]) for n in px));self.assertEqual(sx,sz)
        self.assertEqual(fz,{(n,3):-value for (n,d),value in fx.items()})
        with self.assertRaises(ValueError):retry.minus_z(z)

    def test_native_signal_returncode_retained(self):
        with tempfile.TemporaryDirectory() as d:
            case=Path(d);process=Mock(pid=12345,returncode=-11)
            with patch.object(r.subprocess,'Popen',return_value=process),patch.object(r.os,'killpg') as kill:
                with self.assertRaisesRegex(ValueError,'native CCX failed'):r.ccx(case,'x','fixture',1)
            value=json.loads((case/'x-execution.json').read_text())
            self.assertEqual(value['native_returncode'],-11);self.assertTrue(value['native_process_reaped'])
            self.assertIsNone(value['error']);kill.assert_called_once_with(12345,r.signal.SIGKILL)

    def test_owned_worker_child_does_not_kill_parent_group(self):
        with tempfile.TemporaryDirectory() as d:
            case=Path(d);process=Mock(pid=12345,returncode=-11);process.poll.return_value=-11
            with patch.object(r.subprocess,'Popen',return_value=process),patch.object(r.os,'killpg') as kill:
                with self.assertRaises(ValueError):r.ccx(case,'x','fixture',1,new_session=False)
                kill.assert_not_called();process.kill.assert_not_called();process.wait.assert_called()

    def test_missing_runtime_pin_refuses_before_any_process(self):
        with patch.object(r.c.g8,'sha256',return_value='wrong'),patch.object(r.subprocess,'Popen') as spawn:
            with self.assertRaisesRegex(ValueError,'inventory or builder'):r.runtime('expected')
            spawn.assert_not_called()

    def test_group_memory_guard_kills_only_owned_group(self):
        with tempfile.TemporaryDirectory() as d:
            args=argparse.Namespace(output=Path(d)/'new',reference=Path(d)/'reference.json',reference_sha256='fixture')
            process=Mock(pid=123456,returncode=-15);process.poll.return_value=None
            with patch.object(retry,'inputs',return_value=({}, {}, {}, {},Path(d))),\
                    patch.object(retry.shutil,'disk_usage',return_value=SimpleNamespace(free=40*1024**3)),\
                    patch.object(retry.subprocess,'Popen',return_value=process),\
                    patch.object(retry.subprocess,'check_output',return_value=f'123456 123456 {29*1024**2}\n'),\
                    patch.object(retry.os,'killpg') as kill:
                self.assertEqual(retry.control(args),2)
                report=json.loads((args.output/'summary.json').read_text())
                self.assertEqual(report['error'],'28GiB_RSS_limit');self.assertFalse(report['complete'])
                self.assertEqual([call.args[0] for call in kill.call_args_list],[123456,123456])
                self.assertEqual(process.wait.call_count,2)


if __name__=='__main__':unittest.main()
