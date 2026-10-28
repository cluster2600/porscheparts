"""Small stdlib copy/hash/rebase boundary checks; no restore or drawing."""
import ast
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('_dependent_fields_replay',HERE/'replay_v3.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class Boundaries(unittest.TestCase):
    def test_unpinned_late_import_refused(self):
        from types import SimpleNamespace
        key='numpy._synthetic_unpinned';self.assertNotIn(key,sys.modules)
        sys.modules[key]=SimpleNamespace(__file__=str(HERE/'selfcheck_v3.py'))
        try:
            with self.assertRaisesRegex(ValueError,'Late scientific import'):m.check_imported_runtime({})
        finally:del sys.modules[key]
    def test_known_supplemental_import_allowed(self):
        from types import SimpleNamespace
        key='PIL._synthetic_observed';self.assertNotIn(key,sys.modules);path=str((HERE/'selfcheck_v3.py').resolve())
        sys.modules[key]=SimpleNamespace(__file__=path)
        try:self.assertIn(path,m.check_imported_runtime({path:m.sha(path)}))
        finally:del sys.modules[key]
    def test_valid_exact_copy(self):
        with tempfile.TemporaryDirectory()as d:
            source=Path(d).resolve()/'source';target=Path(d).resolve()/'target';source.mkdir();target.mkdir();(source/'a').write_bytes(b'byteexact\x00\n')
            m.copy_one(source,target,'a',m.sha(source/'a'));self.assertEqual((target/'a').read_bytes(),(source/'a').read_bytes())
    def test_hash_refused_before_copy(self):
        with tempfile.TemporaryDirectory()as d:
            source=Path(d).resolve()/'source';target=Path(d).resolve()/'target';source.mkdir();target.mkdir();(source/'a').write_bytes(b'actual')
            with self.assertRaisesRegex(ValueError,'source/hash'):m.copy_one(source,target,'a','0'*64)
            self.assertFalse((target/'a').exists())
    def test_overwrite_refused(self):
        with tempfile.TemporaryDirectory()as d:
            source=Path(d).resolve()/'source';target=Path(d).resolve()/'target';source.mkdir();target.mkdir();(source/'a').write_bytes(b'actual');(target/'a').write_bytes(b'keep')
            with self.assertRaisesRegex(ValueError,'collision'):m.copy_one(source,target,'a',m.sha(source/'a'))
            self.assertEqual((target/'a').read_bytes(),b'keep')
    def test_dangling_target_refused(self):
        with tempfile.TemporaryDirectory()as d:
            source=Path(d).resolve()/'source';target=Path(d).resolve()/'target';source.mkdir();target.mkdir();(source/'a').write_bytes(b'actual');(target/'a').symlink_to(target/'absent')
            with self.assertRaises(ValueError):m.copy_one(source,target,'a',m.sha(source/'a'))
    def test_symlink_parent_refused(self):
        with tempfile.TemporaryDirectory()as d:
            source=Path(d).resolve()/'source';target=Path(d).resolve()/'target';source.mkdir();target.mkdir();(source/'folder').mkdir();(source/'folder/a').write_bytes(b'actual');(target/'folder').symlink_to(source/'folder',target_is_directory=True)
            with self.assertRaises(ValueError):m.copy_one(source,target,'folder/a',m.sha(source/'folder/a'))
    def test_path_escape_refused(self):
        for path in ['/absolute','../up','a/../b','a//b','a/./b','']:
            with self.assertRaises(ValueError):m.relative(path)
    def test_rebase_only_source_root(self):
        old={'source_root':'/old','cases':[{'field':'same.npz','numeric':1.25}],'files_sha256':{'x':'a'*64},'runtime_sha256':{'/absolute':'b'*64}}
        new=m.rebase(old,'/new');self.assertEqual(old['source_root'],'/old');self.assertEqual(new['cases'],old['cases']);self.assertEqual(new['runtime_sha256'],old['runtime_sha256']);new['source_root']='/old';self.assertEqual(new,old)
    def test_pending_before_restore(self):
        with tempfile.TemporaryDirectory()as d:
            p=Path(d)/'p.json';p.write_text(json.dumps(dict(launch_ready=False,root_GO_sha256=None)))
            with self.assertRaisesRegex(ValueError,'NON-ARMED'):m.run(p,m.sha(p))
    def test_no_scientific_import(self):
        self.assertFalse(any(n in sys.modules for n in ['numpy','matplotlib','OCP','gmsh']))
    def test_one_restore_one_frozen_main_no_solver(self):
        t=ast.parse((HERE/'replay_v3.py').read_text());calls=[n for n in ast.walk(t)if isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)]
        self.assertEqual(sum(n.func.attr=='run_path'for n in calls),1);self.assertEqual(sum(n.func.attr=='restore'for n in calls),1)
        self.assertFalse({n.func.attr for n in calls}&{'Popen','solve','generate','mesh','refine','loadtxt'})

if __name__=='__main__':unittest.main(verbosity=2)
