import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'twins/935-horizontal-cooling-system-f0/source'


def load(name):
    spec=importlib.util.spec_from_file_location(name,SOURCE/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


class ConformingRuntimeTests(unittest.TestCase):
    def test_memory_monitor_counts_only_owned_process_group(self):
        runner=load('run_conforming_study')
        self.assertEqual(runner.group_rss(' 17 100\n18 9999999\n17 200\n',17),300)
        self.assertEqual(runner.group_rss('18 9999999\n',17),0)
        with self.assertRaises(ValueError):runner.run('/missing','/unused',49,1800)
        with self.assertRaises(ValueError):runner.run('/missing','/unused',32,3601)

    def test_upstream_patch_refuses_unexpected_text_and_preserves_pointer_return(self):
        builder=load('build_ccx_macos')
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'source.c';text='void first(){\nreturn NULL;\n\n}\nvoid *second(){\nreturn NULL;\n}\n';path.write_text(text)
            with self.assertRaises(ValueError):builder.change(path,'return NULL;','return;')
            self.assertEqual(path.read_text(),text)
            builder.change(path,'return NULL;\n\n}','return;\n\n}')
            self.assertIn('void *second(){\nreturn NULL;',path.read_text())
            self.assertEqual(path.with_name('source.c.original').read_text(),text)
            path.write_text('NULL NULL NULL')
            builder.change(path,'NULL','0',count=3);self.assertEqual(path.read_text(),'0 0 0')
