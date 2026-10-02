"""A source collision must never turn catalogue membership into invented fitment."""
import importlib.util
import json
from pathlib import Path
import tempfile
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('porsche_corpus', ROOT/'training/qwen-porsche-corpus/corpus.py')
corpus = importlib.util.module_from_spec(spec)
spec.loader.exec_module(corpus)


class CorpusTest(unittest.TestCase):
    def test_reference_source_page_and_missing_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); data = root/'site/data'; (data/'993-manual').mkdir(parents=True)
            def row(ref, source, group, desc):
                return dict(oemReference=ref,petSourceId=source,petIllustration=group,
                            petPage=17,generationId='993',description=desc)
            listed = [row('993 115 021 53','A','109-00','carrier'),
                      row('900 000 000 01','A','109-00','screw'),
                      row('900 000 000 02','B','109-00','unrelated screw')]
            (data/'oem-listed.json').write_text(json.dumps({'listings':listed}))
            (data/'oem-parts.json').write_text('{"oemParts":[]}')
            for kind in ('technical-data','torque-specs','procedures'):
                (data/'993-manual'/f'{kind}.json').write_text('{"entries":[]}')
            text=root/'pages.txt';text.write_text('first page\f\fthird page\f')
            out=root/'out';report=corpus.build(root/'site',out,[('manual',text)])
            self.assertEqual(report['document_pages'],{'manual':3})
            self.assertEqual(report['empty_document_pages'],['manual-page-2'])
            db=out/'knowledge.sqlite'
            self.assertEqual(corpus.query(db,'99311502153')[0]['page'],17)
            assembly=corpus.query(db,'993 115 021 53',assembly=True)
            self.assertEqual({r['source'] for r in assembly},{'A'})
            self.assertEqual(len(assembly),2)
            self.assertEqual(corpus.query(db,'unrelated screw')[0]['source'],'B')
            self.assertEqual(corpus.query(db,'not in source'),[])
            with self.assertRaises(ValueError):corpus.build(root/'site',out,[])
            self.assertEqual(corpus.partition('part:99311502153'),corpus.partition('part:99311502153'))
            sys.path.insert(0,str(ROOT/'training/qwen-porsche-corpus'))
            try:
                import train
                record={'id':'test','kind':'pet','source':'A','page':17,'status':'unverified',
                        'split_key':'part:99311502153','data':{'description':'carrier'}}
                case=train.example(record,'description')
                self.assertTrue(train.score([case],[json.dumps(case['expected'],sort_keys=True)])[0]['passed'])
                wrong={**case['expected'],'status':'verified'}
                self.assertFalse(train.score([case],[json.dumps(wrong)])[0]['passed'])
                missing=train.example(record,'material')
                self.assertIsNone(missing['expected']['value'])
                self.assertEqual(missing['expected']['status'],'not_in_record')
                fail=[{'id':'test','kind':'pet','passed':False}]
                good=[{**fail[0],'passed':True}]
                self.assertFalse(train.gate(good,fail)['eligible'])
                self.assertTrue(train.gate(fail,good)['eligible'])
            finally:sys.path.pop(0)


if __name__ == '__main__':unittest.main()
