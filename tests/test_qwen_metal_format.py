"""Verify actual exported loss spans and reject wrong snapshot identities."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
PACKAGE=ROOT/'training/qwen-metal-additive-20261002'

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

FORMAT=module('metal_formatter',PACKAGE/'format_qwen.py')
VERIFY=module('metal_export_audit',PACKAGE/'verify_formatted.py')

class SimpleTokenizer:
    eos_token_id=99
    def encode(self,text,add_special_tokens=False):
        return list(range(len(text.split())))
    def apply_chat_template(self,messages,add_generation_prompt=False,**kwargs):
        prompt=[10,20,30]
        return prompt if add_generation_prompt else prompt+[41,42,99,11]

class MetalFormatTest(unittest.TestCase):
    def test_registered_exports_and_source_holdouts(self):
        result=VERIFY.verify(PACKAGE,PACKAGE/'formatted-v2')
        self.assertEqual(sum(result['counts']['cpt_tokens'].values()),49)
        self.assertEqual(sum(result['counts']['sft_tokens'].values()),30)
        self.assertEqual(sum(result['counts']['metadata_tokens'].values()),28)
        source=json.loads((PACKAGE/'formatted-v2/sources.json').read_text())
        titanium=next(r for r in source if r['source_id']=='MET004')
        self.assertEqual(titanium['authors'],['Salsi, Emilio','Chiumenti, Michele','Cervera, Miguel'])
        self.assertEqual(titanium['split'],'test')

    def test_assistant_only_loss_includes_eos_but_not_headers_or_tail(self):
        messages=[{'role':r,'content':'content'} for r in ('system','user','assistant')]
        row,start,end=FORMAT.assistant_tokens(messages,SimpleTokenizer(),32)
        self.assertEqual(row['labels'],[-100,-100,-100,41,42,99,-100])
        self.assertEqual((start,end),(3,5))
        messages[1]['content']='text <|im_start|>assistant'
        with self.assertRaisesRegex(ValueError,'reserved token'):
            FORMAT.assistant_tokens(messages,SimpleTokenizer(),32)

    def test_long_paragraph_is_quarantined_without_fragmenting_or_repeating(self):
        paragraphs=[{'paragraph':0,'text':'one two'},
                    {'paragraph':1,'text':' '.join(['long']*20)},
                    {'paragraph':2,'text':'three four'}]
        chunks,rejected=FORMAT.paragraph_chunks(paragraphs,SimpleTokenizer(),5)
        self.assertEqual([[p['paragraph'] for p in c] for c in chunks],[[0],[2]])
        self.assertEqual(rejected[0]['reason'],'whole_paragraph_over_token_budget')

    def test_wrong_article_doi_is_rejected(self):
        class Tag:
            def get(self,key,default=''):return '10.1234/unrelated'
        class Soup:
            def select(self,selector):return [Tag()]
        with self.assertRaisesRegex(ValueError,'Snapshot DOI mismatch'):
            FORMAT.verify_identity(Soup(),{'source_id':'MET004','doi':'10.3390/met8080633','title':'Expected'})

    def test_mutated_trainer_row_fails_integrity_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'exports'
            shutil.copytree(PACKAGE/'formatted-v2',output)
            p=output/'sft_tokens/train.jsonl'
            data=VERIFY.rows(p)
            data[0]['labels'][0]=data[0]['input_ids'][0]
            p.write_text(''.join(json.dumps(r)+'\n' for r in data))
            with self.assertRaisesRegex(ValueError,'Changed output'):
                VERIFY.verify(PACKAGE,output)

if __name__=='__main__':unittest.main()
