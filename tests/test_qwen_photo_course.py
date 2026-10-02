"""One check of photo corrections, supplied units, deck isolation and source coverage."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
HERE=ROOT/'training/qwen-engineering-refinement'


class PhotoCourseTests(unittest.TestCase):
    def test_photo_curriculum_and_independent_checks(self):
        sys.path.insert(0,str(HERE))
        try:
            import photo_run
            import photo_course
            import refine
            import retain
            import select_variant
        finally:sys.path.pop(0)
        smoke=refine.module('photo_smoke_test',ROOT/'scripts/cad_recode/ccx_smoke.py')
        class USD:SYSTEM='supplied mesh buffers'
        rows=photo_course.cases(refine,USD,smoke)
        self.assertEqual(len(rows),len({r['id'] for r in rows}))
        self.assertEqual({s:sum(r['split']==s for r in rows) for s in ('train','valid','test')},{'train':1416,'valid':140,'test':140})
        targets=[r['expected'] for r in rows if r['domain']=='engineering']
        self.assertTrue(any(r.get('geometry_allowed') for r in targets))
        self.assertTrue(any(r.get('can_compare_cooling') for r in targets))
        self.assertTrue(any(r.get('request_source_clarification') for r in targets))
        self.assertTrue(any(r.get('displacement_consistent') for r in targets))
        self.assertFalse(any(r.get('delta_temperature_alone_proves_heat_rate') for r in targets))
        self.assertAlmostEqual(3.141592653589793*50*50*70/4/1000,137.4446786)
        replay=retain.weighted(rows)
        self.assertTrue(all(r['split']=='train' for r in replay))
        self.assertEqual(sum(r['domain']=='calculix' for r in replay),96)
        self.assertEqual(sum(r['domain']=='engineering' for r in replay),960)
        example={'split':'train','domain':'openusd','messages':[{}, {'content':'Select large.'}, {'content':'variants.SetVariantSelection("small")\n'}], 'expected':{'selection':'large'}}
        revised=select_variant.explicit_selection(example)
        self.assertTrue(revised['messages'][-1]['content'].endswith('variants.SetVariantSelection("large")\n'))
        self.assertEqual(revised['expected'],example['expected'])
        self.assertEqual(example['messages'][-1]['content'],'variants.SetVariantSelection("small")\n')
        small={**example,'messages':[{}, {'content':'Select small.'}, {'content':'variants.SetVariantSelection("large")\n'}]}
        self.assertTrue(select_variant.explicit_selection(small)['messages'][-1]['content'].endswith('variants.SetVariantSelection("small")\n'))
        for split in ('valid','test'):
            held_out={**example,'split':split}
            self.assertIs(select_variant.explicit_selection(held_out),held_out)
        self.assertEqual(len(select_variant.weighted([example,{**example,'split':'valid'}])),6)
        self.assertTrue(all(not r.get('manufacturing_authorized',False) for r in targets if 'geometry_allowed' in r))
        self.assertTrue(any(r.get('manufacturing_authorized') for r in targets))
        for r in rows:
            if r['domain']=='calculix':
                self.assertEqual(photo_run.deck_signature(r['expected']['deck']),photo_run.deck_signature(r['expected']['deck'].replace('0.3','3e-1')))
                self.assertNotEqual(photo_run.deck_signature(r['expected']['deck']),photo_run.deck_signature(r['expected']['deck']+'\n*INCLUDE,INPUT=foreign.inp\n'))
        before=[{'id':str(i),'domain':'calculix','passed':i==0} for i in range(20)]
        after=[{**r,'passed':True} for r in before]; after[-1]['passed']=False
        self.assertTrue(photo_run.qualification(before,after)['eligible'])
        after[0]['passed']=False; self.assertFalse(photo_run.qualification(before,after)['eligible'])
        research=json.loads((HERE/'research.json').read_text())
        self.assertEqual(len(research['sources']),len({r['id'] for r in research['sources']}))
        self.assertTrue(all(r['url'].startswith('https://') and r['rights'] for r in research['sources']))


if __name__=='__main__':unittest.main()
