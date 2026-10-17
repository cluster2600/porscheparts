"""Actual-function tiny tests only; the full head diagnostic is not invoked."""
import ast
from collections import Counter,defaultdict
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import struct
import unittest

ROOT=Path(__file__).resolve().parents[3]
SOURCE=Path(__file__).with_name('reader.py')
HELPER=ROOT/'work/962-engineering/atomic-cavity-plane-clip-cap-aware-mapped-side-diagnostic-prep-001/reader_002.py'
HELPER_SHA='cbc03767f71b225c65fd7a702eae63f25fdd7b871eb92db2eeb419b2f5bb6344'
NAMES={'digest','load_helpers','build_stars','rank_group','map_cycles','classify'}
tree=ast.parse(SOURCE.read_text());nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in NAMES]
env={'F':F,'Path':Path,'math':math,'struct':struct,'ast':ast,'hashlib':hashlib,'Counter':Counter,'defaultdict':defaultdict,'HELPERS':{'need','sub','cross','dot','measure','selected_rows','rational'}}
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(SOURCE),'exec'),env)
h=env['load_helpers'](HELPER,HELPER_SHA)

class ExactKeeperTests(unittest.TestCase):
    def test_frozen_pair_and_triple(self):
        base=ROOT/'work/962-engineering/cap-aware-repair-fixtures-prep-001'
        expected=json.loads((base/'expectations.json').read_text())['cases']
        for name in ('pair','triple'):
            spec=expected[name];path=base/spec['input_file']
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),spec['input_sha256'])
            nv=len(spec['input_points']);nf=len(spec['input_oriented_faces']);rows,points,_=h['selected_rows'](path,list(range(nf)),nv,nf)
            side={i:r for i,r in rows.items() if not all(points[v][2]==0 for v in r)};group=spec['group_members'];stars,_=env['build_stars'](side,{min(group):group})
            result=env['rank_group'](points,stars[min(group)],group,h['measure'])
            self.assertEqual(result['selected_keeper'],spec['expected_keeper']);self.assertIn(result['selected_keeper'],(17,18))
            chosen=next(c for c in result['candidates'] if c['keeper']==result['selected_keeper'])
            self.assertTrue(chosen['eligible']);self.assertFalse(chosen['nonpositive_normal_face_ids'])

    def test_exact_tie_uses_lowest_source_ID(self):
        e=F(1,8);p={0:(-e,F(0),F(0)),1:(e,F(0),F(0)),2:(F(0),F(1),F(0)),3:(F(0),F(0),F(1))}
        result=env['rank_group'](p,{0:(0,2,3),1:(1,3,2)},[0,1],h['measure'])
        self.assertTrue(all(c['eligible'] for c in result['candidates']))
        self.assertEqual(result['candidates'][0]['minimum_exact_q2'],result['candidates'][1]['minimum_exact_q2'])
        self.assertEqual(result['selected_keeper'],0)

    def test_empty_surviving_star_refuses(self):
        p={0:(F(0),F(0),F(0)),1:(F(1),F(0),F(0)),2:(F(0),F(1),F(0))}
        result=env['rank_group'](p,{4:(0,1,2)},[0,1],h['measure'])
        self.assertIsNone(result['selected_keeper']);self.assertTrue(all(not c['eligible'] for c in result['candidates']))
        self.assertTrue(all(c['minimum_exact_q2'] is None and c['dropped_face_ids']==[4] for c in result['candidates']))

    def test_cycle_mapping_keeps_untouched_outer_sequence(self):
        cycles=[[0,1,2,3],[8,9,10,11]];mapped=env['map_cycles'](cycles,{0:1,1:1})
        self.assertEqual(mapped,[[1,2,3],[8,9,10,11]]);self.assertEqual(mapped[1],cycles[1])

if __name__=='__main__':unittest.main()
