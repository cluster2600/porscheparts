"""Small stdlib-only portable closure/copy boundary checks; no extraction or draw."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
w=load(HERE/'replay.py','_portable25_checks')
c=load(HERE/'historical_closure.py','_rebased003_closure_checks')
oldtests=load(ROOT/'work/carrier-C1-junction-section-figure-003/selfcheck.py','_old003_closure_fixtures')

class Tests(unittest.TestCase):
    def fixture(self,r):
        p=oldtests.Tests().closed_fixture(r);m=oldtests.m
        sup=json.loads(Path(p['extraction_supervision']).read_text());mirror=r/'mirror';mirror.mkdir()
        for source in [Path(m.__file__),Path(sup['command'][5])]:
            target=mirror/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(source.read_bytes())
        p.update(capsule_root=str(mirror),historical_producer=m.__file__,historical_data=p['data'])
        return p

    def test_four_path_substitutions_inverse_entire_function(self):
        d=json.loads((HERE/'closure-derivation.json').read_text());old=(ROOT/d['reference']).read_text()
        n=next(n for n in ast.parse(old).body if isinstance(n,ast.FunctionDef)and n.name=='closed_extraction')
        old='\n'.join(old.splitlines()[n.lineno-1:n.end_lineno])+'\n';new=(HERE/'historical_closure.py').read_text();new=new[new.index('def closed_extraction('):]
        for r in reversed(d['replacements']):self.assertEqual(new.count(r['new']),1);new=new.replace(r['new'],r['old'],1)
        self.assertEqual(new,old);self.assertEqual(len(d['replacements']),4)

    def test_identical_original_and_copied_closure_acceptance(self):
        with tempfile.TemporaryDirectory(dir=HERE)as t:
            p=self.fixture(Path(t));oldtests.m.closed_extraction(p);c.closed_extraction(p)

    def test_foreign_successful_command_and_tampered_copies_refused(self):
        for edit in ['producer','output','plan','producer_copy','plan_copy']:
            with tempfile.TemporaryDirectory(dir=HERE)as t:
                r=Path(t);p=self.fixture(r);s=Path(p['extraction_supervision']);v=json.loads(s.read_text())
                if edit=='producer':v['command'][3]=str(HERE/'replay.py')
                elif edit=='output':v['command'][6]=str(r/'foreign')
                elif edit=='plan':v['command'][5]=str(r/'foreign-plan.json')
                else:
                    source=Path(v['command'][3 if edit=='producer_copy'else 5]);target=Path(p['capsule_root'])/source.relative_to(ROOT);target.write_text('changed')
                s.write_text(json.dumps(v));p['extraction_supervision_sha256']=w.sha(s)
                with self.assertRaises((ValueError,FileNotFoundError)):c.closed_extraction(p)

    def test_copy_hash_and_path_confinement(self):
        with tempfile.TemporaryDirectory(dir=HERE)as t:
            r=Path(t);(r/'payload').write_text('same');pins={'payload':w.sha(r/'payload')};w.copied_identities(r,pins)
            (r/'payload').write_text('changed')
            with self.assertRaisesRegex(ValueError,'payload changed'):w.copied_identities(r,pins)
            for name in ['../foreign',str(r/'payload'),'']:
                with self.assertRaises(ValueError):w.safe(r,name)

    def test_symlinked_copied_payload_refused(self):
        with tempfile.TemporaryDirectory(dir=HERE)as t:
            r=Path(t);(r/'target').write_text('same');(r/'link').symlink_to(r/'target')
            with self.assertRaisesRegex(ValueError,'Symlink'):w.copied_identities(r,{'link':w.sha(r/'target')})

    def test_pending_refuses_before_module_loading(self):
        with tempfile.TemporaryDirectory(dir=HERE)as t:
            r=Path(t);p=r/'pending.json';p.write_text(json.dumps(dict(launch_ready=False,root_GO_sha256=None)))
            with patch.object(w,'load',side_effect=AssertionError('source import before GO')):
                with self.assertRaisesRegex(ValueError,'NON-ARMED'):w.run(p,w.sha(p),r/'out')
        for name in ['OCP','numpy','matplotlib','PIL']:self.assertNotIn(name,sys.modules)

    def test_status_is_compared_as_eleventh_deterministic_record_key(self):
        tree=ast.parse((HERE/'replay.py').read_text());run=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='run')
        i=next(i for i,n in enumerate(run.body)if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='keys'for t in n.targets))
        block=ast.Module(body=run.body[i:i+2],type_ignores=[]);scope={'require':w.require,'r':{},'reference':{}}
        keys=ast.literal_eval(run.body[i].value);self.assertEqual(len(keys),11);self.assertIn('status',keys)
        scope['r']={k:True for k in keys};scope['reference']=dict(scope['r']);exec(compile(ast.fix_missing_locations(block),'actual_render_comparison','exec'),scope)
        scope['r']['status']='foreign status'
        with self.assertRaisesRegex(ValueError,'records differ'):exec(compile(ast.fix_missing_locations(block),'actual_render_comparison','exec'),scope)

if __name__=='__main__':unittest.main()
