"""Focused private medium recipe tests; no real CCX, CG or mesh."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch

import caps_medium_candidate as m


class MediumRecipe(unittest.TestCase):
    def test_both_decks_byte_identical_to_frozen_g8(self):
        points={n:(n*.123456789012345,n/7,12.) for n in range(1,11)}
        elements=[(1,list(range(1,11)))];support=[1,2]
        weights={'intake':{3:.25,4:.75},'exhaust':{9:1.}}
        forces={'intake':1234.56789012345,'exhaust':987.65432109876}
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);original=root/'original';new=root/'new';original.mkdir();new.mkdir()
            for name,direction in m.c.g11.DIRECTIONS:
                with patch.object(m.c.g8.subprocess,'run',side_effect=RuntimeError('stop before any solve')):
                    with self.assertRaisesRegex(RuntimeError,'stop before any solve'):
                        m.c.g8.solve(original,points,elements,support,weights,forces,direction,name)
                m.write_deck(new,points,elements,support,weights,forces,direction,name)
                self.assertEqual((new/(name+'.inp')).read_bytes(),(original/(name+'.inp')).read_bytes())
                with self.assertRaises(FileExistsError):m.write_deck(new,points,elements,support,weights,forces,direction,name)

    def test_actual_pinned_coarse_and_medium_preflight(self):
        _,variant,proof=m.inputs()
        self.assertEqual(variant['id'],m.c.IDENT);self.assertEqual(proof['preflight_nodes'],380408)
        self.assertLessEqual(proof['coarse']['coarse_maximum_journal_motion_mm'],.04)
        with patch.object(m,'PILOT_SHA','0'*64):
            with self.assertRaisesRegex(ValueError,'preflight changed'):m.inputs()

    def test_low_disk_fails_before_output_or_process(self):
        with tempfile.TemporaryDirectory() as d,patch.object(m,'inputs',return_value=({}, {}, {})),\
                patch.object(m.shutil,'disk_usage',return_value=SimpleNamespace(free=m.FREE_DISK_MIN-1)),\
                patch.object(m.subprocess,'Popen') as spawn:
            output=Path(d)/'never-created'
            with self.assertRaisesRegex(ValueError,'free disk'):m.control(output)
            self.assertFalse(output.exists());spawn.assert_not_called()

    def test_memory_guard_only_kills_owned_group_and_waits(self):
        with tempfile.TemporaryDirectory() as d:
            output=Path(d)/'medium';process=Mock(pid=123456,returncode=-15)
            process.poll.return_value=None
            with patch.object(m,'inputs',return_value=({}, {}, {})),\
                    patch.object(m.shutil,'disk_usage',return_value=SimpleNamespace(free=40*1024**3)),\
                    patch.object(m.subprocess,'Popen',return_value=process),\
                    patch.object(m.subprocess,'check_output',return_value=f'123456 123456 {29*1024**2}\n'),\
                    patch.object(m.os,'killpg') as kill:
                self.assertEqual(m.control(output),2)
                report=json.loads((output/'summary.json').read_text())
                self.assertEqual(report['error'],'28GiB_RSS_limit');self.assertFalse(report['numerically_qualified'])
                self.assertTrue(report['worker_reaped']);self.assertEqual(process.wait.call_count,2)
                self.assertEqual([call.args[0] for call in kill.call_args_list],[123456,123456])


if __name__=='__main__':unittest.main()
