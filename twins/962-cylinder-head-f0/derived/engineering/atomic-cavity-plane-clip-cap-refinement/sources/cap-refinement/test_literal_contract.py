"""Tiny literal/format checks only. Does not import or run the native adapter."""
import json
from pathlib import Path
import struct
import unittest

HERE=Path(__file__).resolve().parent

class LiteralContract(unittest.TestCase):
    def setUp(self):
        self.cases=json.loads((HERE/'fixture-expectations.json').read_text())['cases']

    def test_complete_literal_codec_and_identity_rows(self):
        for name,case in self.cases.items():
            raw=(HERE/'fixtures'/f'{name}.bin').read_bytes()
            self.assertEqual(raw[:8],b'962SURF1')
            nv,nf=struct.unpack_from('<QQ',raw,8)
            self.assertEqual(len(raw),24+24*(nv+nf))
            self.assertEqual(list(struct.iter_unpack('<ddd',raw[24:24+24*nv])),[tuple(x)for x in case['literal_points_mm']])
            self.assertEqual(list(struct.iter_unpack('<QQQ',raw[24+24*nv:])),[tuple(x)for x in case['literal_oriented_faces']])
            pairs=list(struct.iter_unpack('<QQ',(HERE/'fixtures'/f'{name}.map.u64').read_bytes()))
            self.assertEqual(pairs,[tuple(x)for x in case['map_rows']])
            self.assertEqual([a for a,b in pairs],sorted({a for a,b in pairs}))
            self.assertEqual(sum(a==b for a,b in pairs),1)
            mapping=list(range(nv))
            for a,b in pairs:mapping[a]=b
            self.assertTrue(all(mapping[mapping[a]]==mapping[a]for a in range(nv)))

    def test_identity_is_a_function_row_not_an_edge(self):
        pairs=self.cases['ordinary']['map_rows']
        self.assertEqual(pairs,[[0,0]])
        self.assertEqual(self.cases['ordinary']['map_nonidentity_rows'],0)
        self.assertFalse(self.cases['ordinary']['expected']['Steiner_insertion_required'])

    def test_loop_refusal_has_two_vertex_image(self):
        mapping={a:b for a,b in self.cases['mapped-loop-refusal']['map_rows']}
        outer=[0,3,2,1]
        self.assertEqual(len({mapping.get(a,a)for a in outer}),2)
        self.assertEqual(self.cases['mapped-loop-refusal']['expected']['intended_returncode'],3)

    def test_invalid_fixed_association_and_honest_insertion_expectation(self):
        case=self.cases['invalid-fixed-association']
        self.assertEqual(case['fixed_face_ids'],[case['input']['faces']])
        self.assertTrue(case['expected']['no_exports'])
        attempt=self.cases['interior-attempt']['expected']
        self.assertIsNone(attempt['actual_Steiner_insertion_count'])
        self.assertIsNone(attempt['intended_returncode'])
        self.assertEqual(attempt['allowed_declared_geometric_outcomes'],[0,3])

if __name__=='__main__':unittest.main()
