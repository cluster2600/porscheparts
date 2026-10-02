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
