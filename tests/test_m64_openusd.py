"""Bounded OpenUSD authoring: real Pixar checks when the pinned runtime is installed."""
import importlib.util
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch

PATH=Path(__file__).resolve().parents[1]/'training/m64-engineer/openusd.py'
SPEC=importlib.util.spec_from_file_location('m64_openusd',PATH)
usd=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(usd)
try:
    from pxr import Usd
    NATIVE=Usd.GetVersion()==usd.VERSION
except ImportError:
    NATIVE=False


class OpenUSDTests(unittest.TestCase):
    def test_missing_runtime_cannot_be_scored(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'empty.jsonl';source.write_text('')
            output=root/'scores.jsonl'
            args=['openusd.py','score','--input',str(source),'--responses',str(source),'--output',str(output)]
            with patch.object(sys,'argv',args),patch.dict(sys.modules,{'pxr':None}):
                with self.assertRaises(ModuleNotFoundError):usd.main()
            self.assertFalse(output.exists())

    def test_corpus(self):
        rows=usd.candidates()
        self.assertEqual(rows,usd.candidates())
        self.assertEqual([sum(r['split']==s for r in rows) for s in ('train','valid','test')],[48,6,12])
        self.assertEqual(len({r['id'] for r in rows}),66)
        self.assertEqual(len({r['messages'][1]['content'] for r in rows}),66)
        self.assertTrue(all(r['validation']['status']=='pending' for r in rows))
        # Templates cross splits: this deliberately cannot masquerade as 66 independent families.
        self.assertEqual(len({r['family_id'] for r in rows}),6)
        expanded=usd.candidates(expanded=True)
        self.assertEqual(expanded,usd.candidates(expanded=True))
        self.assertEqual([sum(r['split']==s for r in expanded) for s in ('train','valid','test')],[288,24,24])
        prompts=[r['messages'][1]['content'] for r in rows+expanded]
        self.assertEqual(len(set(prompts)),len(prompts))
        self.assertTrue(all(r['messages'][1]['content'].count('Also create')<=1 for r in expanded if r['split']=='train'))
        self.assertEqual(sum(r['messages'][1]['content'].count('Also create')==2 for r in expanded if r['split']=='test'),12)
        composition=usd.candidates(composition=True)
        self.assertEqual(composition,usd.candidates(composition=True))
        self.assertEqual([sum(r['split']==s for r in composition) for s in ('train','valid','test')],[288,0,24])
        self.assertTrue(all(r['messages'][1]['content'].count('Also create')==2 for r in composition))
        for key in ('id','prompt','answer'):
            values=[r['id'] if key=='id' else r['messages'][1 if key=='prompt' else 2]['content'] for r in rows+expanded+composition]
            self.assertEqual(len(set(values)),len(values),key)

    @unittest.skipUnless(NATIVE,'requires usd-core==25.5.1')
    def test_native_contract_and_boundary(self):
        rows=usd.candidates()+usd.candidates(expanded=True)+usd.candidates(composition=True)
        with tempfile.TemporaryDirectory() as directory:
            for row in rows:
                with self.subTest(row=row['id']):
                    stage=usd.author(row['messages'][-1]['content'])
                    result=usd.validate(stage,Path(directory)/row['id'])
                    self.assertEqual(result['skipped_checks'],['ShaderPropertyTypeConformanceChecker'])
        for code in ('import os', 'open("/tmp/never", "w")',
                     'stage.GetRootLayer().Export("/tmp/never")',
                     'stage.__class__', 'x = getattr(stage, "Export")',
                     'stage.GetReferences().AddReference("remote.usda")',
                     'for x in [1]:\n    stage.DefinePrim("/X")',
                     'x = 1e309', 'x = "'+('a'*161)+'"'):
            with self.subTest(code=code),self.assertRaises((ValueError,SyntaxError)):
                usd.author(code)
        for row in (r for r in rows if r['split']=='valid'):
            code=row['messages'][-1]['content']
            expected=usd.snapshot(usd.author(code))
            self.assertEqual(expected,usd.snapshot(usd.author(code.replace('root =','world =').replace('root.GetPrim()','world.GetPrim()'))))
            self.assertNotEqual(expected,usd.snapshot(usd.author(code.replace('0.001','1.0'))))
        variants=next(r for r in rows if r['split']=='valid' and r['recipe']==4)['messages'][-1]['content']
        self.assertNotEqual(usd.snapshot(usd.author(variants)),usd.snapshot(usd.author(variants.replace('part.CreateSizeAttr(4)','part.CreateSizeAttr(5)'))))
