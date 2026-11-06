"""Refinement state survives interruption without weakening the source or geometry gates."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from collections import Counter

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    'selection_checkpoint', ROOT / 'scripts/calculix_refinement_checkpoint.py')
CHECKPOINT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKPOINT)


class SelectionCheckpointTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.vectors = {'gravity': np.array([10., 0., 0., 1.]),
                        'combined': np.array([0., 10., 1., 0.])}
        self.totals = {k: float(a.sum()) for k, a in self.vectors.items()}

    def test_least_covered_case_cursor_continues_after_restart(self):
        covered = {name: 0. for name in self.vectors}
        blocked = np.zeros(4, dtype=bool)
        cursor = CHECKPOINT.Balanced(self.vectors, self.totals, covered,
                                    blocked, set(), np.ones(4, dtype=bool))
        first = next(cursor)
        self.assertEqual(first, 1)
        blocked[first] = True
        for name, values in self.vectors.items():
            covered[name] += values[first]
        resumed = CHECKPOINT.Balanced(self.vectors, self.totals, covered,
                                     blocked, set(), np.ones(4, dtype=bool))
        resumed.restore_cursor(dict(cursor.positions), cursor.seen.copy(),
                               dict(cursor.order_hashes))
        self.assertEqual(next(resumed), 0)
        with self.assertRaises(AssertionError):
            resumed.restore_cursor(dict(cursor.positions), cursor.seen.copy(),
                                   {'gravity': 'foreign', 'combined': 'foreign'})

    def fixture(self):
        # Four cells surround an interior edge. The second disjoint star remains unselected.
        children = np.array([[0, 12, 2, 3], [12, 1, 2, 3],
                             [0, 12, 3, 4], [12, 1, 3, 4],
                             [0, 12, 4, 5], [12, 1, 4, 5],
                             [0, 12, 5, 2], [12, 1, 5, 2]], dtype='<i8')
        vectors = {'gravity': np.arange(1., 9.), 'combined': np.arange(8., 0., -1.)}
        totals = {name: float(values.sum()) for name, values in vectors.items()}
        state = dict(selected=[dict(edge=[0, 1], source_cell_indices=[0, 1, 2, 3],
                                    maximum_child_edge_matrix_condition=4.)],
                     midpoints=[np.array([-0., 0., 0.])],
                     solver_midpoints=[np.array([-0., 0., 0.])],
                     children=[children], removed=[0, 1, 2, 3],
                     blocked=np.array([True] * 4 + [False] * 4), attempted={1},
                     covered=.1 + .2, case_covered={'gravity': 10., 'combined': 26.},
                     refused=Counter({'boundary': 2}), last_note=0)
        cursor = CHECKPOINT.Balanced(vectors, totals, state['case_covered'],
                                    state['blocked'], set(), np.ones(8, dtype=bool))
        cursor.positions['gravity'] = 1
        cursor.seen[0] = True
        return state, cursor

    def test_complete_state_roundtrip_preserves_every_array_bit(self):
        state, cursor = self.fixture()
        context = {'source_sha256': 'admitted-fixture', 'target': .5}
        first = CHECKPOINT.save(self.root / 'first', context, cursor, state)
        restored, position = CHECKPOINT.load(self.root / 'first', context)
        self.assertEqual(restored['selected'], state['selected'])
        self.assertEqual(restored['covered'].hex(), state['covered'].hex())
        self.assertEqual(restored['case_covered'], state['case_covered'])
        self.assertEqual(restored['refused'], state['refused'])
        self.assertEqual(restored['attempted'], state['attempted'])
        self.assertEqual(position['positions'], cursor.positions)
        for name in ('midpoints', 'solver_midpoints', 'children'):
            self.assertEqual(np.vstack(state[name]).tobytes(),
                             np.vstack(restored[name]).tobytes())
        np.testing.assert_array_equal(restored['blocked'], state['blocked'])
        second = CHECKPOINT.save(self.root / 'second', context, cursor, restored)
        self.assertEqual(first['archive_sha256'], second['archive_sha256'])
        meta = json.loads(Path(first['metadata']).read_text())
        self.assertFalse(meta['proposal_or_geometry_admitted'])

    def test_changed_source_context_is_refused(self):
        state, cursor = self.fixture()
        CHECKPOINT.save(self.root, {'source': 'A'}, cursor, state)
        with self.assertRaises(AssertionError):
            CHECKPOINT.load(self.root, {'source': 'B'})

    def test_corrupt_committed_archive_is_refused(self):
        state, cursor = self.fixture()
        receipt = CHECKPOINT.save(self.root, {'source': 'A'}, cursor, state)
        meta = json.loads(Path(receipt['metadata']).read_text())
        archive = self.root / meta['npz']
        data = bytearray(archive.read_bytes())
        data[len(data) // 2] ^= 1
        archive.write_bytes(data)
        with self.assertRaises(AssertionError):
            CHECKPOINT.load(self.root, {'source': 'A'})

    def test_uncommitted_archive_does_not_replace_latest_good_state(self):
        state, cursor = self.fixture()
        CHECKPOINT.save(self.root, {'source': 'A'}, cursor, state)
        (self.root / 'selection-999999.npz').write_bytes(b'interrupted write')
        restored, _ = CHECKPOINT.load(self.root, {'source': 'A'})
        self.assertEqual(restored['selected'], state['selected'])
        self.assertEqual(np.vstack(restored['children']).tobytes(),
                         np.vstack(state['children']).tobytes())

    def test_duplicate_parent_cells_cannot_be_checkpointed_as_disjoint(self):
        state, cursor = self.fixture()
        state['removed'] = [0, 1, 2, 2]
        state['selected'][0]['source_cell_indices'] = [0, 1, 2, 2]
        state['blocked'][3] = False
        with self.assertRaises(AssertionError):
            CHECKPOINT.save(self.root, {'source': 'A'}, cursor, state)


if __name__ == '__main__':
    unittest.main()
