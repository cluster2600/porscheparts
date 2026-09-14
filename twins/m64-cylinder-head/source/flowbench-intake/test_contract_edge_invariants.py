# SPDX-License-Identifier: GPL-3.0-or-later
"""Pure, synthetic incidence/link tests. These do NOT execute the C++ utility."""
from fractions import Fraction as F
from itertools import combinations
from pathlib import Path
import unittest


def cycle(f):
    return min(f[i:]+f[:i] for i in range(len(f)))


def join(records, deleted, a=0, b=1):
    """Records are (ordered triangle, owner, neighbour or None, patch or None)."""
    live, patches, boundary = {}, [], []
    signatures = set()
    for f, own, nei, patch in records:
        mapped = tuple(b if p == a else p for p in f)
        if len(set(mapped)) != 3:
            raise ValueError('degenerate face belongs in removal path')
        signatures.add(tuple(sorted(mapped)))
        for cell, oriented in ((own, mapped), (nei, mapped[::-1])):
            if cell is not None and cell not in deleted:
                if cell in live:
                    raise ValueError('repeated live cell')
                live[cell] = oriented
        if nei is None:
            patches.append(patch); boundary.append(mapped)
    if len(signatures) != 1 or len(records) > 2 or len(live) not in (1, 2):
        raise ValueError('nonmanifold face grouping')
    cells = sorted(live)
    if len(cells) == 2:
        if patches or cycle(live[cells[0]]) != cycle(live[cells[1]][::-1]):
            raise ValueError('orientation or boundary conflict')
        return live[cells[0]], cells[0], cells[1], None
    if len(patches) != 1 or cycle(live[cells[0]]) != cycle(boundary[0]):
        raise ValueError('ambiguous boundary provenance')
    return live[cells[0]], cells[0], None, patches[0]


def link(simplices, vertices):
    result = set()
    for simplex in simplices:
        if not set(vertices) <= set(simplex):
            continue
        rest = sorted(set(simplex)-set(vertices))
        for size in range(1,len(rest)+1):
            result.update(combinations(rest,size))
    return result


def det(a,b,c,d):
    u,v,w = [tuple(F(p[i])-F(a[i]) for i in range(3)) for p in (b,c,d)]
    return sum(u[i]*(v[(i+1)%3]*w[(i+2)%3]-v[(i+2)%3]*w[(i+1)%3]) for i in range(3))


class ContractionTests(unittest.TestCase):
    def test_internal_pair_reconnects_two_remaining_neighbours(self):
        rows=[((0,2,3),10,20,None),((1,3,2),11,20,None)]
        self.assertEqual(join(rows,{20}),((1,2,3),10,11,None))

    def test_boundary_pair_transfers_original_patch(self):
        rows=[((0,2,3),10,20,None),((1,2,3),20,None,'walls')]
        self.assertEqual(join(rows,{20}),((1,2,3),10,None,'walls'))

    def test_reject_same_direction_internal_faces(self):
        with self.assertRaises(ValueError):
            join([((0,2,3),10,20,None),((1,2,3),11,20,None)],{20})

    def test_reject_ambiguous_patch_or_no_live_cell(self):
        with self.assertRaises(ValueError):
            join([((0,2,3),10,None,'walls'),((1,3,2),11,None,'inlet')],set())
        with self.assertRaises(ValueError):
            join([((0,2,3),10,20,None),((1,3,2),11,20,None)],{10,11,20})

    def test_reject_duplicate_owner_and_nonmanifold_group(self):
        with self.assertRaises(ValueError):
            join([((0,2,3),10,20,None),((1,3,2),10,20,None)],{20})
        with self.assertRaises(ValueError):
            join([((0,2,3),10,20,None),((1,3,2),11,20,None),((1,2,3),12,20,None)],{20})

    def test_link_condition_valid_three_tet_fixture(self):
        tets=[(0,1,2,3),(0,2,3,4),(1,2,3,5)]
        self.assertEqual(link(tets,[0]) & link(tets,[1]),link(tets,[0,1]))

    def test_link_condition_rejects_duplicate_surviving_tets(self):
        tets=[(0,1,2,3),(0,2,3,4),(1,2,3,4)]
        self.assertNotEqual(link(tets,[0]) & link(tets,[1]),link(tets,[0,1]))

    def test_exact_positive_endpoints_imply_positive_straight_path(self):
        a=(F(-1,10),0,0); b=(F(1,10),0,0)
        c=(0,1,0); d=(0,0,1); x=(-1,0,0)
        initial=det(x,a,c,d); final=det(x,b,c,d)
        self.assertGreater(initial,0); self.assertGreater(final,0)
        for t in (F(0),F(1,7),F(1,2),F(1)):
            p=tuple(a[i]+t*(b[i]-a[i]) for i in range(3))
            self.assertEqual(det(x,p,c,d),(1-t)*initial+t*final)
            self.assertGreater(det(x,p,c,d),0)

    def test_native_source_defers_actions_and_has_no_solver_or_quality_bypass(self):
        source=(Path(__file__).parent/'contract_edge/contractTetEdge.C').read_text()
        self.assertLess(source.index('checkLink(la,lb,lab)'),source.index('polyTopoChange changes'))
        self.assertLess(source.index('Candidate exterior is not an oriented closed edge-manifold'),source.index('polyTopoChange changes'))
        self.assertIn('changes.removePoint(A,B)',source)
        self.assertNotIn('allowCellCollapse',source[source.index('int main'):])
        self.assertNotIn('system(',source)


if __name__=='__main__':
    unittest.main()
